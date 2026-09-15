"""Accounting only: no imports from rules and no path back into decisions."""
from evaluation.baselines.common.contracts import decode
from evaluation.baselines.common.journal import raw_record, utcnow

OUTCOMES = {'AUTO_EXECUTE_SUCCESS', 'AUTO_EXECUTE_FAILURE', 'HITL_APPROVED', 'HITL_REJECTED', 'HITL_MODIFIED'}


class FeedbackRecorder:
    def __init__(self, journal, run_id, metrics):
        self.journal, self.run_id, self.metrics = journal, run_id, metrics
        self.seen = {}

    def process(self, body):
        record = {'run_id': self.run_id, 'received_at': utcnow(), **raw_record(body), 'status': 'malformed'}
        try:
            data = decode(body)
            if not isinstance(data, dict):
                raise ValueError('not object')
            record['payload'] = data
            event_id = data.get('event_id')
            outcome = data.get('outcome_type')
            actions = data.get('actual_actions_taken')
            envelope = data.get('full_policy_result')
            if (not isinstance(event_id, str) or not event_id.strip()
                    or not isinstance(outcome, str) or outcome not in OUTCOMES
                    or not isinstance(actions, list) or not all(isinstance(x, str) for x in actions)
                    or not isinstance(data.get('operator_notes'), str)
                    or not isinstance(envelope, dict)):
                raise ValueError('invalid fields')
            record.update(event_id=event_id, outcome_type=outcome)
            if (envelope.get('run_id') != self.run_id or envelope.get('controller') != 'threshold_only'
                    or envelope.get('event_id') != event_id):
                record['status'] = 'wrong_run'
            elif not self.journal.decision(event_id):
                record['status'] = 'unexpected_id'
            else:
                expected = self.journal.decision(event_id)[0]['routing_decision']
                if (expected == 'AUTO') != outcome.startswith('AUTO_'):
                    record['status'] = 'route_mismatch'
                elif event_id in self.seen:
                    record['status'] = 'duplicate' if self.seen[event_id] == data else 'conflicting_duplicate'
                else:
                    record['status'] = 'accepted'
        except (ValueError, TypeError, UnicodeError):
            pass
        # Keep exact bytes even for malformed/nonfinite JSON; do not serialize invalid parsed values.
        if record['status'] == 'malformed':
            record.pop('payload', None)
        self.journal.append('feedback', record)
        status = record['status']
        if status == 'accepted':
            self.seen[record['event_id']] = record['payload']
            self.metrics.feedback_received.labels(record['outcome_type']).inc()
        elif status in {'duplicate', 'conflicting_duplicate'}:
            self.metrics.feedback_duplicates.inc()
            if status == 'conflicting_duplicate':
                self.metrics.feedback_errors.labels(status).inc()
        else:
            self.metrics.feedback_errors.labels(status).inc()
        return record

    def callback(self, channel, method, properties, body):
        self.process(body)  # A storage failure raises; delivery remains unacknowledged.
        channel.basic_ack(method.delivery_tag)
