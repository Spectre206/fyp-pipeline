import ast
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock
from evaluation.baselines.common.contracts import ROOT, normalize
from evaluation.baselines.common.layer3_adapter import envelope
from evaluation.baselines.threshold_only.rules import decide
from evaluation.baselines.threshold_only.tests.test_contracts import fused, structural


def decision(raw=None):
    return {**decide(normalize(raw or fused())), 'run_id': 'test', 'decision_ready_at': '2026-09-15T10:00:00+00:00', 'processing_seconds': .001}


def source_function(path, name, globals_dict, class_name=None):
    """Execute the existing function AST, excluding import-time servers/connections."""
    tree = ast.parse(path.read_text())
    nodes = next(n.body for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name) if class_name else tree.body
    node = next(n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), globals_dict)
    return globals_dict[name]


class CompatibilityTests(unittest.TestCase):
    def test_actual_auto_extraction_and_feedback(self):
        wrote, published = Mock(), Mock()
        global_vars = {'json': json, 'write_decision': wrote, 'publish': published,
                       'OUTCOME_FEEDBACK_EMITTED': Mock(), 'log': Mock()}
        handler = source_function(ROOT/'layer3/auto_executor/executor.py', 'on_message', global_vars, 'AutoExecutor')
        instance, channel, method = Mock(), Mock(), Mock(delivery_tag=1)
        instance.execute_actions.return_value = ('AUTO_EXECUTE_SUCCESS', 500)
        payload = envelope(decision())
        handler(instance, channel, method, None, json.dumps(payload))
        channel.basic_ack.assert_called_once_with(1)
        channel.basic_nack.assert_not_called()
        self.assertIsNone(wrote.call_args.args[0]['confidence_from_llm'])
        self.assertEqual(json.loads(published.call_args.args[1])['full_policy_result'], payload)

    def test_actual_human_decision_extraction(self):
        build = source_function(ROOT/'layer3/dashboard/hitl/views.py', '_build_decision', {})
        payload = envelope(decision(structural()))
        row = build(payload, 'APPROVE', 'note', ['MONITOR_AND_ALERT'])
        self.assertEqual(row['event_id'], 's1')
        self.assertIsNone(row['confidence_from_llm'])
        self.assertEqual(row['risk_tier_from_llm'], 'HIGH')

    def test_actual_logger_persists_null(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = {'sqlite3': sqlite3, 'json': json, 'datetime': datetime, 'timezone': timezone, 'DB_PATH': str(Path(directory)/'test.db')}
            path = ROOT/'layer3/sqlite_logger/logger.py'
            for name in ('_get_conn', 'init_db', 'write_decision'):
                source_function(path, name, scope)
            scope['init_db']()
            scope['write_decision']({'event_id':'e1', 'decision_type':'AUTO_EXECUTE', 'confidence_from_llm':None})
            with sqlite3.connect(scope['DB_PATH']) as db:
                self.assertIsNone(db.execute('SELECT confidence_from_llm FROM decisions').fetchone()[0])

    def test_actual_hitl_persistence_contract(self):
        manager = Mock()
        manager.objects.get_or_create.return_value = ('incident', True)
        persist = source_function(ROOT/'layer3/dashboard/hitl/management/commands/consume_hitl.py', 'persist_hitl_incident', {'HitlIncident':manager,'json':json})
        payload = envelope(decision(structural()))
        persist(payload)
        kwargs = manager.objects.get_or_create.call_args.kwargs
        self.assertEqual(kwargs['event_id'], 's1')
        self.assertEqual(json.loads(kwargs['defaults']['payload_json']), payload)

    def test_original_preserved_no_fake_agent_measurements(self):
        raw = fused()
        payload = envelope(decision(raw))
        self.assertEqual(payload['full_reasoning_chain']['triage_result']['original_event'], raw)
        self.assertNotIn('policy_agent_latency_ms', payload)
        response = payload['full_reasoning_chain']['strategy_result']['llm_response']
        self.assertIsNone(response['confidence'])
        self.assertIn('Deterministic rule', response['reasoning'])

    def test_neutral_template(self):
        from django.template import Engine, Context
        # Remove URL tags only: this checks actual displayed data without starting a Django app.
        import re
        text = re.sub(r'{% url .*?%}', '#', (ROOT/'evaluation/baselines/common/templates/hitl/detail.html').read_text())
        rendered = Engine().from_string(text).render(Context({'payload':envelope(decision()),'incident':{'event_id':'e1','id':1}}, use_l10n=False))
        self.assertIn('Controller Risk Tier', rendered)
        self.assertIn('Unavailable', rendered)
        self.assertNotIn('LLM Risk Tier', rendered)
