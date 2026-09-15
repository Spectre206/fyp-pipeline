"""Replay exact captured bytes and schedule; never change event IDs or body timestamps."""
import argparse
import base64
import json
import math
import os
import time
from pathlib import Path
from evaluation.baselines.common.capture_incidents import load_capture
from evaluation.baselines.common.journal import new_run, utcnow


def replay(records, publish, output, run_id, speed=1.0, clock=time.monotonic, sleep=time.sleep):
    if not math.isfinite(speed) or speed <= 0:
        raise ValueError('speed must be finite and positive')
    started, first = clock(), records[0]['offset_seconds']
    for record in records:
        due = (record['offset_seconds'] - first) / speed
        sleep(max(0, started + due - clock()))
        sent = utcnow()
        publish(record['routing_key'], base64.b64decode(record['body_base64'], validate=True),
                {'run_id': run_id, 'replay_published_at': sent, 'capture_sequence': record['sequence']})
        output.write(json.dumps({'run_id': run_id, 'event_id': record['event_id'], 'sequence': record['sequence'],
                                 'published_at': sent, 'confirmed_at': utcnow(), 'scheduled_offset_seconds': due}) + '\n')
        output.flush()
        os.fsync(output.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', type=Path, required=True, help='New replay evidence directory, separate from controller output')
    parser.add_argument('--speed', type=float, default=1.0)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    if not args.live:
        parser.error('Explicit --live is required; use controller --dry-run for broker-free execution')
    if not math.isfinite(args.speed) or args.speed <= 0:
        parser.error('speed must be finite and positive')
    records, manifest = load_capture(args.capture, args.manifest)
    directory = new_run(args.output, args.run_id, mode='replay', capture_sha256=manifest['sha256'], speed=args.speed)
    from evaluation.baselines.common.rabbitmq import connect, publish
    connection = connect()
    try:
        channel = connection.channel()
        state = channel.queue_declare(queue='anomaly.detected', passive=True).method
        if state.consumer_count != 1 or state.message_count:
            raise RuntimeError('Require one selected input consumer and an empty ready queue')
        channel.confirm_delivery()
        with (directory / 'replay.jsonl').open('x') as output:
            replay(records, lambda route, body, headers: publish(channel, route, body, headers), output, args.run_id, args.speed)
        (directory / 'completed.json').write_text(json.dumps({'count': len(records), 'completed_at': utcnow()}) + '\n')
    finally:
        connection.close()


if __name__ == '__main__':
    main()
