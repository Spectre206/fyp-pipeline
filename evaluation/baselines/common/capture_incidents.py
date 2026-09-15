"""Capture as sole anomaly.detected consumer; no Layer 1 or topology changes."""
import argparse
import base64
import hashlib
import json
import math
import os
import time
from pathlib import Path
from evaluation.baselines.common.contracts import decode
from evaluation.baselines.common.journal import new_run, utcnow


class Capture:
    def __init__(self, directory):
        self.path = Path(directory) / 'incidents.jsonl'
        self.output = self.path.open('xb')
        self.ids = set()
        self.count = 0
        self.started = time.monotonic()

    def write(self, routing_key, body):
        data = decode(body)
        event_id = data.get('event_id') if isinstance(data, dict) else None
        if not isinstance(event_id, str) or not event_id.strip() or len(event_id) > 255:
            raise ValueError('Capture requires usable event IDs; input remains unacknowledged')
        if event_id in self.ids:
            raise ValueError('Duplicate event ID; capture is incomplete and needs reconciliation')
        if routing_key not in {'anomaly.fused', 'anomaly.schema_drift'}:
            raise ValueError('Unsupported incident routing key')
        record = {'sequence': self.count, 'event_id': event_id, 'routing_key': routing_key,
                  'captured_at': utcnow(), 'offset_seconds': time.monotonic() - self.started,
                  'body_base64': base64.b64encode(body).decode('ascii')}
        self.output.write((json.dumps(record) + '\n').encode())
        self.output.flush()
        os.fsync(self.output.fileno())
        self.ids.add(event_id)
        self.count += 1

    def finish(self):
        self.output.close()
        manifest = {'format': 'fyp-capture-v1', 'sha256': hashlib.sha256(self.path.read_bytes()).hexdigest(),
                    'count': self.count, 'unique_ids': len(self.ids), 'schedule': 'capture_offsets',
                    'capture_complete': True,
                    'note': 'Reconcile Layer 1 publication and queue drain before freezing this dataset.'}
        (self.path.parent / 'incidents.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        return manifest


def load_capture(path, manifest_path):
    path = Path(path)
    manifest = json.loads(Path(manifest_path).read_text())
    content = path.read_bytes()
    if manifest.get('format') != 'fyp-capture-v1' or manifest.get('capture_complete') is not True:
        raise ValueError('Unsupported/incomplete capture')
    if hashlib.sha256(content).hexdigest() != manifest.get('sha256'):
        raise ValueError('Capture checksum mismatch')
    records, ids, last = [], set(), -1.0
    for line in content.splitlines():
        record = json.loads(line)
        body = base64.b64decode(record['body_base64'], validate=True)
        payload = decode(body)
        event_id = payload.get('event_id') if isinstance(payload, dict) else None
        offset = record['offset_seconds']
        if (not isinstance(event_id, str) or not event_id.strip() or len(event_id) > 255
                or event_id != record['event_id'] or event_id in ids or record['sequence'] != len(records)
                or not isinstance(offset, (int, float)) or isinstance(offset, bool)
                or not math.isfinite(offset) or offset < 0 or offset < last
                or record['routing_key'] not in {'anomaly.fused', 'anomaly.schema_drift'}):
            raise ValueError('Invalid capture identity/order/schedule/route')
        ids.add(event_id)
        last = offset
        records.append(record)
    if not records or len(records) != manifest.get('count') or len(ids) != manifest.get('unique_ids'):
        raise ValueError('Capture count mismatch or empty dataset')
    return records, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--capture-id', required=True)
    parser.add_argument('--count', type=int, required=True, help='Expected reconciled capture count; no historical default')
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    if not args.live or args.count < 1:
        parser.error('Explicit --live and positive --count are required')
    from evaluation.baselines.common.rabbitmq import connect, require_idle
    directory = new_run(args.output, args.capture_id, mode='capture')
    capture = Capture(directory)
    connection = None
    try:
        connection = connect()
        channel = connection.channel()
        require_idle(channel, ['anomaly.detected'])
        channel.basic_qos(prefetch_count=1)
        def callback(ch, method, properties, body):
            capture.write(method.routing_key, body)
            ch.basic_ack(method.delivery_tag)
            if capture.count >= args.count:
                ch.stop_consuming()
        channel.basic_consume(queue='anomaly.detected', on_message_callback=callback, exclusive=True)
        channel.start_consuming()
        if capture.count != args.count:
            raise RuntimeError('Capture interrupted: no complete manifest written')
        capture.finish()
    finally:
        capture.output.close()
        if connection and connection.is_open:
            connection.close()


if __name__ == '__main__':
    main()
