"""Offline tests for the optional Learning LLM diagnostic switch."""
import json
import os
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

# Learning and Policy normally run in separate processes.  Avoid registering
# Learning's production metric names in this shared unit-test process, so the
# existing Policy tests can import their metrics independently.
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
            "full_reasoning_chain": {
                "strategy_result": {
                    "llm_response": {"risk_tier": "LOW", "confidence": 0.8}
                },
                "triage_result": {
                    "anomaly_type": "throughput_drop",
                    "severity": "MEDIUM",
                    "original_event": {"affected_component": "RabbitMQ consumer"},
                },
            }
        },
    }


class LearningLlmSwitchTests(unittest.TestCase):
    def make_agent(self, enabled):
        agent = object.__new__(learning_agent.LearningAgent)
        agent.llm_enabled = enabled
        return agent

    def test_setting_values_and_invalid_fallback(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(learning_agent.learning_llm_enabled())
        for value in ("true", "1", "yes", "on"):
            with self.subTest(value=value), patch.dict(
                os.environ, {"LAYER2_LEARNING_LLM_ENABLED": value}, clear=True
            ):
                self.assertTrue(learning_agent.learning_llm_enabled())
        for value in ("false", "0", "no", "off"):
            with self.subTest(value=value), patch.dict(
                os.environ, {"LAYER2_LEARNING_LLM_ENABLED": value}, clear=True
            ):
                self.assertFalse(learning_agent.learning_llm_enabled())
        with patch.object(learning_agent.log, "warning") as warning, patch.dict(
            os.environ, {"LAYER2_LEARNING_LLM_ENABLED": "unexpected"}, clear=True
        ):
            self.assertTrue(learning_agent.learning_llm_enabled())
            warning.assert_called_once()

    def test_enabled_mode_calls_llm_and_preserves_processing(self):
        channel = MagicMock()
        agent = self.make_agent(True)
        with patch.object(learning_agent, "generate", return_value={"response": "LLM summary"}) as generate, \
             patch.object(learning_agent, "upsert_incident") as upsert, \
             patch.object(learning_agent, "update_ema") as update_ema, \
             patch.object(learning_agent, "append_log"), \
             patch.object(learning_agent, "record_evaluation") as record:
            agent.on_message(channel, SimpleNamespace(delivery_tag=1), None, json.dumps(outcome_payload()))

        generate.assert_called_once()
        self.assertEqual(upsert.call_args.args[1], "LLM summary")
        update_ema.assert_called_once_with("AUTO_EXECUTE_SUCCESS")
        channel.basic_ack.assert_called_once_with(1)
        learning_record = next(call.args[1] for call in record.call_args_list if call.args[0] == "learning")
        self.assertEqual(learning_record["summary_mode"], "llm")

    def test_disabled_mode_skips_llm_and_uses_deterministic_summary(self):
        channel = MagicMock()
        agent = self.make_agent(False)
        with patch.object(learning_agent, "generate") as generate, \
             patch.object(learning_agent, "upsert_incident") as upsert, \
             patch.object(learning_agent, "update_ema") as update_ema, \
             patch.object(learning_agent, "append_log"), \
             patch.object(learning_agent, "record_evaluation") as record:
            agent.on_message(channel, SimpleNamespace(delivery_tag=1), None, json.dumps(outcome_payload()))

        generate.assert_not_called()
        summary = upsert.call_args.args[1]
        self.assertEqual(
            summary,
            "anomaly_type=throughput_drop; component=RabbitMQ consumer; "
            "actions=RESTART_CONSUMER; outcome=AUTO_EXECUTE_SUCCESS; risk=LOW",
        )
        update_ema.assert_called_once_with("AUTO_EXECUTE_SUCCESS")
        channel.basic_ack.assert_called_once_with(1)
        learning_record = next(call.args[1] for call in record.call_args_list if call.args[0] == "learning")
        self.assertEqual(learning_record["summary_mode"], "deterministic")


if __name__ == "__main__":
    unittest.main()
