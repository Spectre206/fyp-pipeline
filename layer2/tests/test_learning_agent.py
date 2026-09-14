"""Offline tests for final deterministic Learning behavior."""
import ast
import json
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "layer2"))

import prometheus_client

prometheus_client.start_http_server = lambda *args, **kwargs: None


class NoopMetric:
    def __init__(self, *args, **kwargs):
        pass

    def inc(self, *args, **kwargs):
        pass

    def labels(self, *args, **kwargs):
        return self

    def observe(self, *args, **kwargs):
        pass

    def set(self, *args, **kwargs):
        pass


upsert_stub = types.ModuleType("chromadb_utils.upsert")
upsert_stub.upsert_incident = lambda *args, **kwargs: None
sys.modules["chromadb_utils.upsert"] = upsert_stub

# Learning and Policy are separate production processes.  Keep Learning's
# metric registration isolated so the shared unit-test process can import both.
with patch.object(prometheus_client, "Counter", NoopMetric), \
     patch.object(prometheus_client, "Gauge", NoopMetric), \
     patch.object(prometheus_client, "Histogram", NoopMetric):
    from agents import learning_agent


def outcome_payload():
    return {
        "event_id": "event-1",
        "outcome_type": "AUTO_EXECUTE_SUCCESS",
        "actual_actions_taken": ["RESTART_CONSUMER"],
        "full_policy_result": {
            "routing_decision": "AUTO",
            "full_reasoning_chain": {
                "strategy_result": {
                    "llm_response": {"risk_tier": "LOW", "confidence": 0.8}
                },
                "triage_result": {
                    "anomaly_type": "throughput_drop",
                    "severity": "MEDIUM",
                    "original_event": {"affected_component": "RabbitMQ consumer"},
                },
            },
        },
    }


class LearningAgentTests(unittest.TestCase):
    def test_learning_has_no_ollama_generation_dependency(self):
        tree = ast.parse((ROOT / "layer2" / "agents" / "learning_agent.py").read_text())
        imported_modules = {
            node.module for node in tree.body if isinstance(node, ast.ImportFrom)
        }
        called_names = {
            node.func.id for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertNotIn("ollama.client", imported_modules)
        self.assertNotIn("generate", called_names)

    def test_valid_feedback_uses_structured_summary_and_completes_processing(self):
        agent = object.__new__(learning_agent.LearningAgent)
        channel = MagicMock()
        with patch.object(learning_agent, "upsert_incident") as upsert, \
             patch.object(learning_agent, "update_ema") as update_ema, \
             patch.object(learning_agent, "append_log"), \
             patch.object(learning_agent, "record_evaluation") as record:
            agent.on_message(channel, SimpleNamespace(delivery_tag=1), None, json.dumps(outcome_payload()))

        summary = upsert.call_args.args[1]
        self.assertEqual(
            summary,
            "event_id=event-1; anomaly_type=throughput_drop; "
            "component=RabbitMQ consumer; actions=RESTART_CONSUMER; "
            "decision=AUTO; outcome=AUTO_EXECUTE_SUCCESS; risk=LOW; confidence=0.8",
        )
        self.assertTrue(summary)
        update_ema.assert_called_once_with("AUTO_EXECUTE_SUCCESS")
        channel.basic_ack.assert_called_once_with(1)
        learning_record = next(
            call.args[1] for call in record.call_args_list if call.args[0] == "learning"
        )
        self.assertEqual(learning_record["summary_mode"], "deterministic")
        self.assertEqual(learning_record["chromadb_upsert_id"], "event-1")


if __name__ == "__main__":
    unittest.main()
