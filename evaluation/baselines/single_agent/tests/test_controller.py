import json
import tempfile
import unittest
from unittest.mock import Mock
from evaluation.baselines.common.journal import Journal
from evaluation.baselines.single_agent.controller import Controller
from evaluation.baselines.single_agent.metrics import Metrics
from evaluation.baselines.single_agent.llm_client import ModelError
from evaluation.baselines.single_agent.tests.test_contracts import fused, structural


def valid_output(**changes):
    return dict(anomaly_type='cpu_memory_spike', severity='CRITICAL', affected_component='consumer',
                recommended_actions=['MONITOR_AND_ALERT','CHECK_QUEUE_DEPTH','LOG_AND_CONTINUE'],
                confidence=.2, risk_tier='HIGH', routing_decision='AUTO', reasoning='Available evidence assessed.', **changes) if not changes else {**valid_output(), **changes}


def fake_client(value):
    return Mock(generate=Mock(return_value={'raw_response': json.dumps(value), 'telemetry': {}}))


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.journal = Journal(self.temp.name)
        self.client, self.publish = fake_client(valid_output()), Mock()
        self.controller = Controller(self.journal, 'run', Metrics(), self.publish, self.client)

    def tearDown(self):
        self.journal.close(); self.temp.cleanup()

    def process(self, raw=None):
        return self.controller.process(json.dumps(raw or fused()).encode())

    def assert_route(self, output, route, raw=None):
        self.client.generate.return_value = {'raw_response': json.dumps(output), 'telemetry': {}}
        row = self.process(raw)
        self.assertEqual(row['routing_decision'], route)
        self.assertFalse(row['fallback_applied'])
        self.assertEqual(self.publish.call_args.args[0], 'auto.execute' if route=='AUTO' else 'hitl.queue')

    def test_high_auto_remains_auto(self): self.assert_route(valid_output(), 'AUTO')
    def test_low_hitl_remains_hitl(self): self.assert_route(valid_output(risk_tier='LOW',routing_decision='HITL'), 'HITL')
    def test_low_confidence_auto_remains_auto(self): self.assert_route(valid_output(confidence=0), 'AUTO')
    def test_critical_auto_remains_auto(self): self.assert_route(valid_output(severity='CRITICAL'), 'AUTO', fused(severity='CRITICAL'))
    def test_schema_auto_remains_auto(self): self.assert_route(valid_output(anomaly_type='schema_drift'), 'AUTO', structural())
    def test_compound_auto_remains_auto(self):
        raw=fused();raw['fusion_type']='compound';raw['contributing_models'].append(fused('z_score_error_rate')['contributing_models'][0])
        self.assert_route(valid_output(anomaly_type='compound'), 'AUTO', raw)

    def test_unknown_detector_reaches_model(self):
        self.process(fused('unseen'))
        self.assertIn('unseen', self.client.generate.call_args.args[0])

    def test_invalid_input_no_call(self):
        raw=fused();raw['fused_confidence']=2
        self.assertEqual(self.process(raw)['routing_reason'],'SA_INPUT_INVALID')
        self.client.generate.assert_not_called()

    def test_unsupported_contract(self):
        self.assertEqual(self.process({'event_id':'x','severity':'LOW','node':'n','affected_component':'c'})['routing_reason'],'SA_INPUT_UNSUPPORTED')
        self.client.generate.assert_not_called()

    def test_json_retry_succeeds(self):
        self.client.generate.side_effect=[{'raw_response':'oops'}, {'raw_response':json.dumps(valid_output())}]
        row=self.process()
        self.assertEqual(len(row['attempts']),2)
        self.assertFalse(row['fallback_applied'])
        self.assertIn('INVALID_JSON',self.client.generate.call_args.args[0])

    def test_schema_retry_succeeds(self):
        self.client.generate.side_effect=[{'raw_response':'{}'}, {'raw_response':json.dumps(valid_output())}]
        self.assertFalse(self.process()['fallback_applied'])
        self.assertEqual(self.client.generate.call_count,2)

    def test_exhausted_schema_fallback(self):
        self.client.generate.return_value={'raw_response':'{}'}
        row=self.process()
        self.assertEqual(self.client.generate.call_count,2)
        self.assertEqual(row['routing_reason'],'SA_SCHEMA_INVALID')
        self.assertEqual(row['recommended_actions'],[])
        self.assertIsNone(row['risk_tier']);self.assertIsNone(row['confidence'])
        self.assertEqual(len(self.journal.records('attempt')),2)

    def test_exhausted_json_fallback(self):
        self.client.generate.return_value={'raw_response':'oops'}
        self.assertEqual(self.process()['routing_reason'],'SA_JSON_INVALID')
        self.assertEqual(self.client.generate.call_count,2)

    def test_timeout_no_retry(self):
        self.client.generate.side_effect=ModelError('timeout')
        self.assertEqual(self.process()['routing_reason'],'SA_TIMEOUT')
        self.assertEqual(self.client.generate.call_count,1)

    def test_transport_no_retry(self):
        self.client.generate.side_effect=ModelError('connection')
        self.assertEqual(self.process()['routing_reason'],'SA_MODEL_FAILURE')
        self.assertEqual(self.client.generate.call_count,1)

    def test_duplicate_no_generation(self):
        self.process();self.process()
        self.assertEqual(self.client.generate.call_count,1)
        self.assertEqual(self.publish.call_count,1)

    def test_export_and_fallback_envelope(self):
        self.client.generate.side_effect=ModelError('http')
        row=self.process();self.journal.export()
        from pathlib import Path
        self.assertEqual(json.loads((Path(self.temp.name)/'decision.jsonl').read_text()),row)
        payload=json.loads(self.publish.call_args.args[1])
        self.assertEqual(payload['routing_decision'],'HITL')
        self.assertIsNone(payload['full_reasoning_chain']['strategy_result']['llm_response']['confidence'])
        self.assertNotIn('policy_agent_latency_ms',payload)
