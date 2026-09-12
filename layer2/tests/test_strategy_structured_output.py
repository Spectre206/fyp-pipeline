"""Offline tests for Strategy's Ollama JSON-Schema output constraint."""
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

query_stub = types.ModuleType("chromadb_utils.query")
query_stub.retrieve_rag_context = lambda *args, **kwargs: []
query_stub.format_rag_context = lambda context: ""
sys.modules["chromadb_utils.query"] = query_stub

from agents import strategy_agent
from agents.schema_validator import (
    ALLOWED_ACTIONS,
    REQUIRED_FIELDS,
    STRATEGY_RESPONSE_SCHEMA,
    schema_for_triage_severity,
    validate,
)
from ollama import client as ollama_client


def valid_response():
    return {
        "anomaly_type": "throughput_drop",
        "severity": "MEDIUM",
        "affected_component": "RabbitMQ consumer",
        "recommended_actions": [
            "MONITOR_AND_ALERT",
            "LOG_AND_CONTINUE",
            "CHECK_QUEUE_DEPTH",
        ],
        "confidence": 0.8,
        "risk_tier": "LOW",
        "reasoning": "The incident is contained and low risk.",
    }


class StrategyStructuredOutputTests(unittest.TestCase):
    def test_schema_represents_the_full_contract(self):
        schema = STRATEGY_RESPONSE_SCHEMA
        self.assertIsInstance(schema, dict)
        self.assertEqual(set(schema["required"]), REQUIRED_FIELDS)
        self.assertFalse(schema["additionalProperties"])
        actions = schema["properties"]["recommended_actions"]
        self.assertEqual(actions["minItems"], 3)
        self.assertEqual(actions["maxItems"], 3)
        self.assertTrue(actions["uniqueItems"])
        self.assertEqual(set(actions["items"]["enum"]), ALLOWED_ACTIONS)
        self.assertEqual(schema["properties"]["risk_tier"]["enum"], ["HIGH", "LOW"])
        self.assertEqual(schema["properties"]["confidence"]["minimum"], 0)
        self.assertEqual(schema["properties"]["confidence"]["maximum"], 1)

    def test_ollama_client_sends_schema_as_format(self):
        response = MagicMock()
        response.json.return_value = {"response": "{}"}
        with patch.object(ollama_client.requests, "post", return_value=response) as post:
            ollama_client.generate("model", "prompt", "system", format=STRATEGY_RESPONSE_SCHEMA)

        payload = post.call_args.kwargs["json"]
        self.assertIs(payload["format"], STRATEGY_RESPONSE_SCHEMA)
        self.assertIsInstance(payload["format"], dict)

    def test_triage_severity_schema_enforces_the_risk_tier_mapping(self):
        for severity, risk_tier in {
            "LOW": "LOW",
            "MEDIUM": "LOW",
            "HIGH": "HIGH",
            "CRITICAL": "HIGH",
        }.items():
            with self.subTest(severity=severity):
                schema = schema_for_triage_severity(severity)
                self.assertEqual(schema["properties"]["severity"]["enum"], [severity])
                self.assertEqual(schema["properties"]["risk_tier"]["enum"], [risk_tier])
                payload = valid_response()
                payload["severity"] = severity
                payload["risk_tier"] = risk_tier
                self.assertTrue(validate(payload)[0])

    def test_application_validator_rejects_tier_mismatches(self):
        for severity, risk_tier, expected_issue in (
            ("MEDIUM", "HIGH", "tier_mismatch:expected=LOW,got=HIGH"),
            ("HIGH", "LOW", "tier_mismatch:expected=HIGH,got=LOW"),
        ):
            with self.subTest(severity=severity, risk_tier=risk_tier):
                payload = valid_response()
                payload["severity"] = severity
                payload["risk_tier"] = risk_tier
                valid, issues = validate(payload)
                self.assertFalse(valid)
                self.assertIn(expected_issue, issues)

    def test_application_validator_requires_three_distinct_allowed_actions(self):
        accepted = valid_response()
        self.assertTrue(validate(accepted)[0])

        for actions, expected_issue in (
            (["MONITOR_AND_ALERT", "MONITOR_AND_ALERT", "LOG_AND_CONTINUE"], "duplicate_actions"),
            (["MONITOR_AND_ALERT"] * 3, "duplicate_actions"),
            (["MONITOR_AND_ALERT", "LOG_AND_CONTINUE"], "bad_actions_count:2"),
            (["MONITOR_AND_ALERT", "LOG_AND_CONTINUE", "NOT_ALLOWED"], "bad_actions_value"),
        ):
            with self.subTest(actions=actions):
                payload = valid_response()
                payload["recommended_actions"] = actions
                valid, issues = validate(payload)
                self.assertFalse(valid)
                self.assertIn(expected_issue, issues)

    def test_system_prompt_contains_the_mandatory_risk_tier_mapping(self):
        for mapping in ("LOW -> LOW", "MEDIUM -> LOW", "HIGH -> HIGH", "CRITICAL -> HIGH"):
            self.assertIn(mapping, strategy_agent.SYSTEM_PROMPT)
        self.assertIn("copy the Triage Severity", strategy_agent.SYSTEM_PROMPT)

    def test_strategy_passes_schema_and_still_rejects_invalid_response(self):
        agent = object.__new__(strategy_agent.StrategyAgent)
        agent.ch = MagicMock()
        triage = {
            "event_id": "event-1", "anomaly_type": "throughput_drop",
            "severity": "MEDIUM", "original_event": {},
        }
        invalid = valid_response()
        invalid["recommended_actions"] = ["NOT_ALLOWED"] * 3
        with patch.object(strategy_agent, "generate", return_value={"response": json.dumps(invalid)}) as generate, \
             patch.object(strategy_agent, "publish") as publish, \
             patch.object(strategy_agent, "append_log"), \
             patch.object(strategy_agent, "record_evaluation"):
            agent.on_message(MagicMock(), SimpleNamespace(delivery_tag=1), None, json.dumps(triage))

        output_schema = generate.call_args.kwargs["format"]
        self.assertEqual(output_schema["properties"]["severity"]["enum"], ["MEDIUM"])
        self.assertEqual(output_schema["properties"]["risk_tier"]["enum"], ["LOW"])
        self.assertEqual(
            set(output_schema["properties"]["recommended_actions"]["items"]["enum"]),
            ALLOWED_ACTIONS,
        )
        self.assertTrue(output_schema["properties"]["recommended_actions"]["uniqueItems"])
        result = json.loads(publish.call_args.args[2])
        self.assertTrue(result["valid_json"])
        self.assertFalse(result["schema_valid"])
        self.assertFalse(result["timed_out"])


if __name__ == "__main__":
    unittest.main()
