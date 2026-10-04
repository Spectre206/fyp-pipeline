"""Run from repository root with python -m evaluation.baselines.single_agent.controller."""
import argparse
import hashlib
import json
import signal
import socket
import subprocess
import threading
import time
import platform
from datetime import datetime
from pathlib import Path

from evaluation.baselines.common.contracts import normalize, number, ACTION_VOCABULARY_SHA256
from evaluation.baselines.common.journal import Journal, new_run, raw_record, utcnow
from evaluation.baselines.common.layer3_adapter import envelope
from evaluation.baselines.single_agent.metrics import Metrics
from evaluation.baselines.single_agent import prompt, schema
from evaluation.baselines.single_agent.llm_client import Client, ModelError, MODEL, OPTIONS, TIMEOUT


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
    def __init__(self, journal, run_id, metrics, publisher, client):
        self.journal, self.run_id, self.metrics, self.publisher = journal, run_id, metrics, publisher
        self.client = client

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
            self.journal.append('quarantine', {'reason': 'SA_INPUT_UNIDENTIFIABLE', **raw_record(body)})
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
            decision = {**self.decide(incident), 'run_id': self.run_id, 'received_at': received,
                        'decision_ready_at': utcnow(), 'processing_seconds': time.monotonic() - started,
                        'input_sha256': digest, 'publish_confirmed_at': None,
                        'replay_published_at': headers.get('replay_published_at')}
            self.journal.prepare(decision)
            self.metrics.controller_processing.observe(decision['processing_seconds'])
            self.metrics.action_sets.labels('fallback' if decision['fallback_applied'] else 'valid').inc()
        publish_started = time.monotonic()
        try:
            self.publisher('auto.execute' if decision['routing_decision'] == 'AUTO' else 'hitl.queue',
                           json.dumps(envelope(decision), allow_nan=False).encode())
        except Exception:
            self.journal.append('failure', {'event_id': decision['event_id'], 'run_id': self.run_id, 'reason': 'SA_PUBLISH_FAILURE', 'at': utcnow()})
            raise
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

    def decide(self, incident):
        attempts, accepted, issues, reason = [], None, [], 'SA_INPUT_INVALID'
        if incident['input_status'] == 'unsupported':
            reason = 'SA_INPUT_UNSUPPORTED'
        elif incident['input_status'] == 'valid':
            for index in range(2):
                label = 'initial' if index == 0 else 'retry'
                attempt = {'event_id': incident['event_id'], 'run_id': self.run_id,
                           'attempt_number': index + 1, 'started_at': utcnow(),
                           'raw_response': None, 'extracted_json': None, 'extraction_mode': 'none',
                           'validation_issues': [], 'valid': False, 'telemetry': {}}
                self.metrics.model_calls.labels(label).inc()
                started = time.monotonic()
                outcome = 'failure'
                try:
                    result = self.client.generate(prompt.build(incident, issues), prompt.SYSTEM)
                    attempt.update(raw_response=result['raw_response'], telemetry=result.get('telemetry', {}))
                    parsed, mode, parse_issues = schema.extract(result['raw_response'])
                    issues = parse_issues or schema.validate(parsed)
                    attempt.update(extracted_json=parsed, extraction_mode=mode,
                                   validation_issues=issues, valid=not issues)
                    reason = 'SA_JSON_INVALID' if parse_issues else 'SA_SCHEMA_INVALID'
                    if not issues:
                        accepted, reason, outcome = parsed, 'SA_MODEL_DECISION', 'valid'
                        self.metrics.output_valid.labels(label).inc()
                        self.metrics.schema_valid_output.labels(label).inc()
                    else:
                        outcome = 'json' if parse_issues else 'schema'
                        self.metrics.output_invalid.labels(label, outcome).inc()
                except ModelError as exc:
                    outcome = exc.category
                    reason = 'SA_TIMEOUT' if exc.category == 'timeout' else 'SA_MODEL_FAILURE'
                    attempt.update(failure_category=exc.category, telemetry=exc.telemetry)
                    if exc.category == 'timeout': self.metrics.model_timeouts.inc()
                    else: self.metrics.model_failures.labels(exc.category).inc()
                attempt.update(completed_at=utcnow(), generation_seconds=time.monotonic() - started)
                self.metrics.model_generation.labels(label, outcome).observe(attempt['generation_seconds'])
                telemetry = attempt['telemetry']
                tps = telemetry.get('tokens_per_second')
                self.metrics.model_tokens_per_second.set(tps if number(tps) else float('nan'))
                tokens, duration = telemetry.get('eval_count'), telemetry.get('eval_duration')
                if number(tokens) and number(duration) and tokens >= 0 and duration > 0:
                    self.metrics.model_eval_tokens.inc(tokens)
                    self.metrics.model_eval_seconds.inc(duration / 1e9)
                self.journal.append('attempt', attempt)
                attempts.append(attempt)
                if accepted is not None or reason in ('SA_TIMEOUT', 'SA_MODEL_FAILURE') or index == 1:
                    break
                self.metrics.retries.labels(outcome).inc()
        fallback = accepted is None
        route = accepted['routing_decision'] if accepted else 'HITL'
        return {**incident, 'normalized_input': {k: v for k, v in incident.items() if k != 'original_event'},
                'controller': 'single_agent', 'attempts': attempts, 'accepted_model_output': accepted,
                'raw_routing_decision': next((a['extracted_json'].get('routing_decision') for a in reversed(attempts)
                    if isinstance(a['extracted_json'], dict)), None),
                'routing_decision': route, 'final_routing_decision': route, 'routing_reason': reason,
                'fallback_applied': fallback, 'validation_status': 'fallback' if fallback else 'valid',
                'recommended_actions': accepted['recommended_actions'] if accepted else [],
                'risk_tier': accepted['risk_tier'] if accepted else None,
                'confidence': accepted['confidence'] if accepted else None,
                'rationale': accepted['reasoning'] if accepted else 'Output unavailable or invalid; human review required.',
                'prompt_version': prompt.VERSION, 'schema_version': schema.VERSION}

    def callback(self, channel, method, properties, body):
        self.process(body, getattr(properties, 'headers', None))
        channel.basic_ack(method.delivery_tag)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', type=Path, required=True, help='New, nonexisting run directory')
    parser.add_argument('--dry-run', type=Path, help='Plain payload JSONL; never connects to RabbitMQ or metrics')
    parser.add_argument('--network-medium', choices=('wifi', 'ethernet'), help='Experimental provenance only; required for live runs')
    parser.add_argument('--dataset-sha256', help='Frozen input SHA-256: capture file for Mode A; SEG corpus for Mode B')
    parser.add_argument('--evaluation-mode', choices=('A', 'B'))
    parser.add_argument('--capture-manifest-sha256')
    parser.add_argument('--replay-speed', type=float, default=1.0)
    parser.add_argument('--mock-responses', type=Path, help='Dry-run only: JSONL runtime responses or error fixtures, one per model call')
    parser.add_argument('--live', action='store_true', help='Explicitly authorize connections to configured experiment queues')
    args = parser.parse_args()
    if bool(args.dry_run) == args.live:
        parser.error('Choose exactly one of --dry-run FILE or --live')
    if args.live and args.network_medium is None:
        parser.error('--network-medium is required for live runs')
    if args.dataset_sha256 is not None and (len(args.dataset_sha256) != 64 or any(c not in '0123456789abcdef' for c in args.dataset_sha256)):
        parser.error('--dataset-sha256 must be a lowercase SHA-256 digest')
    if bool(args.dry_run) != bool(args.mock_responses):
        parser.error('--dry-run requires --mock-responses; fixtures are forbidden in live mode')
    if not number(args.replay_speed) or args.replay_speed <= 0:
        parser.error('--replay-speed must be positive and finite')
    if args.capture_manifest_sha256 is not None and (len(args.capture_manifest_sha256) != 64 or any(c not in '0123456789abcdef' for c in args.capture_manifest_sha256)):
        parser.error('Invalid capture manifest SHA-256')
    root = Path(__file__).resolve().parents[3]
    git_commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    clean = not subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True).strip()
    client = Client()
    metadata = dict(controller='single_agent', mode='dry-run' if args.dry_run else 'live',
        network_medium=args.network_medium, hostname=socket.gethostname(), logical_node='ai-brain-node',
        git_commit=git_commit, working_tree_clean=clean, measured_start_at=None, ended_at=None,
        evaluation_mode=args.evaluation_mode, dataset_sha256=args.dataset_sha256,
        capture_manifest_sha256=args.capture_manifest_sha256, replay_speed=args.replay_speed,
        model_name=MODEL, model_digest=None, ollama_version=None, ollama_host=client.host,
        num_ctx=2048, num_predict=512, request_timeout_seconds=TIMEOUT, maximum_attempts=2,
        retry_policy_version='json-schema-once-v1', requested_options=OPTIONS, resolved_options=None,
        prompt_version=prompt.VERSION, prompt_sha256=prompt.SHA256, schema_version=schema.VERSION,
        schema_sha256=schema.SHA256, action_vocabulary_sha256=ACTION_VOCABULARY_SHA256,
        warmup_protocol='not-performed-mock' if args.dry_run else 'preload-and-fixed-inference-v1',
        warmup_artifact_reference=None, python_version=platform.python_version(),
        dependency_snapshot_reference=None, cpu_runtime_verification_reference=None, clock_sync_reference=None,
        unavailable_reason='Deployment references must be collected by operator; unset sampling controls use runtime defaults.')
    directory = new_run(args.output, args.run_id, **metadata)
    def update_metadata(**values):
        path = directory / 'run.json'
        data = json.loads(path.read_text())
        data.update(values)
        temporary = directory / 'run.json.tmp'
        temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
        temporary.replace(path)
    journal, metrics = Journal(directory), Metrics()
    if args.dry_run:
        messages = []
        responses = iter(json.loads(line) for line in args.mock_responses.read_text().splitlines() if line.strip())
        class MockClient:
            def generate(self, *_):
                row = next(responses)
                if row.get('error'):
                    if row['error'] not in ('timeout', 'connection', 'http', 'invalid_runtime_response', 'transport'):
                        raise ValueError('Invalid mock failure category')
                    raise ModelError(row['error'])
                return {'raw_response': row['raw_response'], 'telemetry': {}}
        controller = Controller(journal, args.run_id, metrics, lambda route, body: messages.append({'routing_key': route, 'body': json.loads(body)}), MockClient())
        update_metadata(measured_start_at=utcnow())
        try:
            for body in args.dry_run.read_bytes().splitlines():
                if body.strip():
                    controller.process(body)
            (directory / 'dry_run_envelopes.json').write_text(json.dumps(messages, indent=2) + '\n')
        finally:
            journal.export()
            journal.close()
            update_metadata(ended_at=utcnow())
        return
    from prometheus_client import start_http_server
    from evaluation.baselines.common.rabbitmq import connect, publish, require_idle
    from evaluation.baselines.single_agent.feedback import FeedbackRecorder
    stop, errors = threading.Event(), []
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    # Bind before consuming. A busy port fails without consuming any messages.
    try:
        server, _ = start_http_server(8030, addr='0.0.0.0', registry=metrics.registry)
    except Exception:
        journal.close()
        update_metadata(ended_at=utcnow())
        raise

    try:
        update_metadata(**client.identity())
        warmup = client.warmup()
        if stop.is_set():
            raise InterruptedError('Stopped during warmup')
        (directory / 'warmup.json').write_text(json.dumps(warmup, indent=2, allow_nan=False) + '\n')
        update_metadata(warmup_artifact_reference='warmup.json', measured_start_at=utcnow())
    except Exception as exc:
        journal.append('failure', {'stage': 'warmup', 'error_type': type(exc).__name__, 'at': utcnow()})
        journal.export()
        journal.close()
        server.shutdown()
        update_metadata(ended_at=utcnow())
        raise

    def worker(name, queue):
        connection = None
        try:
            connection = connect()
            channel = connection.channel()
            require_idle(channel, [queue] + (['triage.result', 'strategy.result'] if name == 'controller' else []))
            channel.basic_qos(prefetch_count=1)
            channel.confirm_delivery()
            handler = (Controller(journal, args.run_id, metrics, lambda route, body: publish(channel, route, body), client)
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
        update_metadata(ended_at=utcnow())
    if errors:
        raise SystemExit('; '.join(errors))


if __name__ == '__main__':
    main()
