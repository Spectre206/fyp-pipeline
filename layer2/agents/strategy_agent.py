"""Strategy Agent — qwen3:1.7b via Ollama, 7-field JSON output."""
import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog
from datetime import datetime, timezone
from pathlib import Path
from prometheus_client import Counter, Histogram, Gauge, start_http_server

from rabbitmq.connection import get_connection, publish
from agents.schema_validator import validate
from ollama.client import generate

log = structlog.get_logger()

STRATEGY_LATENCY = Histogram("fyp_strategy_latency_s", "Strategy Agent latency")
STRATEGY_VALID = Counter("fyp_strategy_schema_valid_total", "Schema valid responses")
STRATEGY_INVALID = Counter("fyp_strategy_schema_invalid_total", "Schema invalid responses")
STRATEGY_TIMEOUT = Counter("fyp_strategy_timeout_total", "LLM timeouts")
STRATEGY_TPS = Gauge("fyp_strategy_tokens_per_s", "Tokens per second")

start_http_server(8011)

SYSTEM_PROMPT = Path("prompts/strategy_system_prompt.txt").read_text()
LLM_TIMEOUT_S = 30
MODEL = "qwen3:1.7b"


class StrategyAgent:
    def __init__(self):
        self.conn = get_connection()
        self.ch = self.conn.channel()
        log.info("strategy_agent_started", model=MODEL)

    def _build_prompt(self, triage: dict) -> str:
        """Assemble the user prompt from the triage result."""
        ev = triage.get("original_event", {})
        rag = triage.get("rag_context_formatted", "")

        prompt = (
            f"Anomaly Type: {triage.get('anomaly_type')}\n"
            f"Severity: {triage.get('severity')}\n"
            f"Affected Component: {ev.get('affected_component', 'unknown')}\n"
            f"Node: {ev.get('node', 'unknown')}\n"
            f"Response Protocol from Triage: {triage.get('response_protocol')}\n"
            f"Fusion Type: {triage.get('fusion_type')}\n"
            f"Contributing Models: {triage.get('contributing_models', [])}\n"
            f"Context: {ev.get('context', '')}\n"
        )
        if rag:
            prompt += f"\n{rag}\n"
        prompt += "\nGenerate the incident response JSON."
        return prompt

    def on_message(self, ch, method, props, body):
        t0 = time.monotonic()
        timed_out = False
        valid_json = False
        parsed = {}
        raw_response = ""
        schema_valid = False
        issues = "not_attempted"
        eval_count = 0
        tokens_per_s = 0.0

        try:
            triage = json.loads(body)
            event_id = triage.get("event_id", "unknown")
            prompt = self._build_prompt(triage)

            try:
                resp = generate(
                    model=MODEL,
                    prompt=prompt,
                    system=SYSTEM_PROMPT,
                    num_ctx=2048,
                    num_predict=512,
                    timeout=LLM_TIMEOUT_S,
                )
                raw_response = resp.get("response", "")
                eval_count = resp.get("eval_count", 0)
                eval_dur_ns = resp.get("eval_duration", 0)
                tokens_per_s = (
                    round(eval_count / (eval_dur_ns / 1e9), 2)
                    if eval_dur_ns > 0
                    else 0.0
                )
                STRATEGY_TPS.set(tokens_per_s)

                try:
                    parsed = json.loads(raw_response.strip())
                    valid_json = True
                    schema_valid, issues = validate(parsed)
                    if schema_valid:
                        STRATEGY_VALID.inc()
                    else:
                        STRATEGY_INVALID.inc()
                except json.JSONDecodeError:
                    valid_json = False
                    issues = "json_parse_failed"
                    STRATEGY_INVALID.inc()

            except Exception as e:
                # requests.Timeout is a subclass of Exception
                timed_out = True
                issues = "llm_timeout"
                STRATEGY_TIMEOUT.inc()
                log.warning("strategy_llm_timeout", event_id=event_id, error=str(e))

            latency_ms = round((time.monotonic() - t0) * 1000)

            result = {
                "event_id": event_id,
                "strategy_timestamp": datetime.now(timezone.utc).isoformat(),
                "llm_response": parsed,
                "valid_json": valid_json,
                "schema_valid": schema_valid,
                "issues": issues,
                "raw_response": raw_response,
                "strategy_agent_latency_ms": latency_ms,
                "tokens_per_second": tokens_per_s,
                "eval_tokens": eval_count,
                "timed_out": timed_out,
                "triage_result": triage,
            }

            publish(self.ch, "strategy.result", json.dumps(result))
            ch.basic_ack(method.delivery_tag)

            STRATEGY_LATENCY.observe(time.monotonic() - t0)
            log.info(
                "strategy_complete",
                event_id=event_id,
                schema_valid=schema_valid,
                latency_ms=latency_ms,
                tokens_per_s=tokens_per_s,
                timed_out=timed_out,
            )

        except Exception as e:
            log.error("strategy_error", error=str(e))
            ch.basic_nack(method.delivery_tag, requeue=False)

    def run(self):
        self.ch.basic_qos(prefetch_count=1)
        self.ch.basic_consume("triage.result", self.on_message)
        log.info("strategy_consuming", queue="triage.result", model=MODEL)
        self.ch.start_consuming()


if __name__ == "__main__":
    StrategyAgent().run()
