"""Run from repository root with python -m evaluation.baselines.threshold_only.controller."""
import argparse
import hashlib
import json
import signal
import threading
import time
from datetime import datetime
from pathlib import Path

from evaluation.baselines.common.contracts import normalize
from evaluation.baselines.common.journal import Journal, new_run, raw_record, utcnow
from evaluation.baselines.common.layer3_adapter import envelope
from evaluation.baselines.threshold_only.metrics import Metrics
from evaluation.baselines.threshold_only.rules import decide, RULES_SHA256


def elapsed_since(value, now):
    if not isinstance(value, str):
        return None
    try:
        then, end = datetime.fromisoformat(value), datetime.fromisoformat(now)
        if then.tzinfo is None or end.tzinfo is None:
            return None
        duration = (end - then).total_seconds()
        return duration if duration >= 0 else None
    except ValueError:
        return None


class Controller:
    def __init__(self, journal, run_id, metrics, publisher):
        self.journal, self.run_id, self.metrics, self.publisher = journal, run_id, metrics, publisher

    def process(self, body, headers=None):
        received, started = utcnow(), time.monotonic()
        self.metrics.incident_deliveries.inc()
        digest = hashlib.sha256(body).hexdigest()
        self.journal.append('delivery', {'received_at': received, 'sha256': digest, **raw_record(body)})
        headers = headers if isinstance(headers, dict) else {}
        if headers.get('run_id') not in (None, self.run_id):
            self.journal.append('quarantine', {'reason': 'wrong_run', **raw_record(body)})
            self.metrics.malformed_input.labels('wrong_run').inc()
            return None
        incident = normalize(body)
        if incident['input_status'] == 'unidentifiable':
            self.journal.append('quarantine', {'reason': 'TH_INPUT_UNIDENTIFIABLE', **raw_record(body)})
            self.metrics.malformed_input.labels('unidentifiable').inc()
            return None
        previous = self.journal.decision(incident['event_id'])
        if previous:
            self.metrics.duplicate_incidents.inc()
            decision, confirmed = previous
            if decision['input_sha256'] != digest:
                self.journal.append('quarantine', {'event_id': incident['event_id'], 'reason': 'id_collision', **raw_record(body)})
                self.metrics.malformed_input.labels('id_collision').inc()
                return None
            if confirmed:
                return decision
        else:
            self.metrics.incidents_received.labels(incident['input_origin']).inc()
            if incident['input_status'] == 'invalid':
                self.metrics.malformed_input.labels('invalid').inc()
            decision = {**decide(incident), 'run_id': self.run_id, 'received_at': received,
                        'decision_ready_at': utcnow(), 'processing_seconds': time.monotonic() - started,
                        'input_sha256': digest, 'publish_confirmed_at': None,
                        'replay_published_at': headers.get('replay_published_at')}
            self.journal.prepare(decision)
            self.metrics.controller_processing.observe(decision['processing_seconds'])
            self.metrics.action_sets.labels('valid').inc()
        publish_started = time.monotonic()
        self.publisher('auto.execute' if decision['routing_decision'] == 'AUTO' else 'hitl.queue',
                       json.dumps(envelope(decision), allow_nan=False).encode())
        decision['publish_confirmed_at'] = utcnow()
        decision['publish_seconds'] = time.monotonic() - publish_started
        decision['input_queue_wait_seconds'] = elapsed_since(decision.get('replay_published_at'), decision['received_at'])
        decision['boundary_to_decision_seconds'] = elapsed_since(decision.get('replay_published_at'), decision['publish_confirmed_at'])
        self.journal.confirm(decision)
        self.metrics.publish.observe(decision['publish_seconds'])
        for key, metric in (('input_queue_wait_seconds', self.metrics.input_queue_wait),
                            ('boundary_to_decision_seconds', self.metrics.boundary_to_decision)):
            if decision[key] is not None:
                metric.observe(decision[key])
        self.metrics.decisions.labels(decision['routing_decision'], decision['routing_reason'], decision['risk_tier'] or 'UNCLASSIFIED').inc()
        return decision

    def callback(self, channel, method, properties, body):
        self.process(body, getattr(properties, 'headers', None))
        channel.basic_ack(method.delivery_tag)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', type=Path, required=True, help='New, nonexisting run directory')
    parser.add_argument('--dry-run', type=Path, help='Plain payload JSONL; never connects to RabbitMQ or metrics')
    parser.add_argument('--live', action='store_true', help='Explicitly authorize connections to configured experiment queues')
    args = parser.parse_args()
    if bool(args.dry_run) == args.live:
        parser.error('Choose exactly one of --dry-run FILE or --live')
    directory = new_run(args.output, args.run_id, controller='threshold_only', rules_sha256=RULES_SHA256,
                        mode='dry-run' if args.dry_run else 'live')
    journal, metrics = Journal(directory), Metrics()
    if args.dry_run:
        messages = []
        controller = Controller(journal, args.run_id, metrics, lambda route, body: messages.append({'routing_key': route, 'body': json.loads(body)}))
        try:
            for body in args.dry_run.read_bytes().splitlines():
                if body.strip():
                    controller.process(body)
            (directory / 'dry_run_envelopes.json').write_text(json.dumps(messages, indent=2) + '\n')
        finally:
            journal.export()
            journal.close()
        return
    from prometheus_client import start_http_server
    from evaluation.baselines.common.rabbitmq import connect, publish, require_idle
    from evaluation.baselines.threshold_only.feedback import FeedbackRecorder
    stop, errors = threading.Event(), []
    # Bind before consuming. A busy port fails without consuming any messages.
    try:
        server, _ = start_http_server(8020, addr='0.0.0.0', registry=metrics.registry)
    except Exception:
        journal.close()
        raise

    def worker(name, queue):
        connection = None
        try:
            connection = connect()
            channel = connection.channel()
            require_idle(channel, [queue] + (['triage.result', 'strategy.result'] if name == 'controller' else []))
            channel.basic_qos(prefetch_count=1)
            channel.confirm_delivery()
            handler = (Controller(journal, args.run_id, metrics, lambda route, body: publish(channel, route, body))
                       if name == 'controller' else FeedbackRecorder(journal, args.run_id, metrics))
            # Exclusive consumer prevents a competing consumer joining this queue during the run.
            channel.basic_consume(queue=queue, on_message_callback=handler.callback, exclusive=True)
            metrics.worker_up.labels(name).set(1)
            while not stop.is_set():
                connection.process_data_events(time_limit=1)
        except Exception as exc:
            errors.append(f'{name}: {type(exc).__name__}: {exc}')
            metrics.processing_failures.labels(name).inc()
            try:
                journal.append('failure', {'worker': name, 'error_type': type(exc).__name__, 'at': utcnow()})
            finally:
                stop.set()
        finally:
            metrics.worker_up.labels(name).set(0)
            if connection and connection.is_open:
                connection.close()

    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    threads = [threading.Thread(target=worker, args=(name, queue)) for name, queue in
               [('feedback', 'outcome.feedback'), ('controller', 'anomaly.detected')]]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        stop.set()
        server.shutdown()
        journal.export()
        journal.close()
    if errors:
        raise SystemExit('; '.join(errors))


if __name__ == '__main__':
    main()
