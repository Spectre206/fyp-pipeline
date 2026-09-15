import json
import tempfile
import unittest
from unittest.mock import Mock
from evaluation.baselines.common.journal import Journal
from evaluation.baselines.threshold_only.controller import Controller
from evaluation.baselines.threshold_only.feedback import FeedbackRecorder
from evaluation.baselines.threshold_only.metrics import Metrics
from evaluation.baselines.threshold_only.tests.test_contracts import fused
from evaluation.baselines.threshold_only.rules import decide
from evaluation.baselines.common.contracts import normalize


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.journal, self.metrics = Journal(self.temp.name), Metrics()
        self.publisher = Mock()
        self.controller = Controller(self.journal, 'r1', self.metrics, self.publisher)
        self.controller.process(json.dumps(fused()).encode())
        self.envelope = json.loads(self.publisher.call_args.args[1])
        self.recorder = FeedbackRecorder(self.journal, 'r1', self.metrics)

    def tearDown(self):
        self.journal.close()
        self.temp.cleanup()

    def feedback(self, **changes):
        row = {'event_id':'e1','outcome_type':'AUTO_EXECUTE_SUCCESS','actual_actions_taken':['MONITOR_AND_ALERT'], 'operator_notes':'ok','resolution_time_ms':500,'full_policy_result':self.envelope}
        row.update(changes)
        return json.dumps(row).encode()

    def test_valid_feedback_durable(self):
        self.assertEqual(self.recorder.process(self.feedback())['status'], 'accepted')
        self.assertEqual(len(self.journal.records('feedback')), 1)

    def test_duplicate_retained(self):
        self.recorder.process(self.feedback())
        self.assertEqual(self.recorder.process(self.feedback())['status'], 'duplicate')
        self.assertEqual(len(self.journal.records('feedback')), 2)

    def test_conflicting_duplicate(self):
        self.recorder.process(self.feedback())
        self.assertEqual(self.recorder.process(self.feedback(operator_notes='different'))['status'], 'conflicting_duplicate')

    def test_unexpected_id(self):
        self.envelope['event_id']='other'
        self.assertEqual(self.recorder.process(self.feedback(event_id='other'))['status'], 'unexpected_id')

    def test_wrong_run(self):
        self.envelope['run_id']='old'
        self.assertEqual(self.recorder.process(self.feedback())['status'], 'wrong_run')

    def test_malformed(self):
        for body in (b'{', b'[]', b'null', self.feedback(outcome_type='other')):
            self.assertEqual(self.recorder.process(body)['status'], 'malformed')

    def test_route_mismatch(self):
        self.assertEqual(self.recorder.process(self.feedback(outcome_type='HITL_APPROVED'))['status'], 'route_mismatch')

    def test_no_rule_change(self):
        before = decide(normalize(fused()))
        self.recorder.process(self.feedback(outcome_type='AUTO_EXECUTE_FAILURE'))
        self.assertEqual(before, decide(normalize(fused())))

    def test_ack_after_durable_write_only(self):
        self.journal.append = Mock(side_effect=OSError('disk full'))
        channel = Mock()
        with self.assertRaises(OSError):
            self.recorder.callback(channel, Mock(delivery_tag=1), None, self.feedback())
        channel.basic_ack.assert_not_called()

    def test_duplicate_input_not_republished(self):
        self.controller.process(json.dumps(fused()).encode())
        self.assertEqual(self.publisher.call_count, 1)

    def test_id_collision_quarantined(self):
        changed = fused(severity='HIGH')
        self.controller.process(json.dumps(changed).encode())
        self.assertEqual(self.publisher.call_count, 1)
        self.assertEqual(self.journal.records('quarantine')[0]['reason'], 'id_collision')

    def test_broker_failure_no_ack(self):
        self.publisher.side_effect = RuntimeError('offline')
        channel = Mock()
        with self.assertRaises(RuntimeError):
            self.controller.callback(channel, Mock(delivery_tag=1), None, json.dumps(fused(event_id='e2')).encode())
        channel.basic_ack.assert_not_called()
        self.assertFalse(self.journal.decision('e2')[1])

    def test_unidentifiable_quarantine(self):
        self.controller.process(b'bad')
        self.assertEqual(self.publisher.call_count, 1)
        self.assertEqual(self.journal.records('quarantine')[0]['reason'], 'TH_INPUT_UNIDENTIFIABLE')
