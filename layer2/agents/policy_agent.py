"""Policy Agent — Deterministic 5-rule routing table."""
import json
import math
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog
from datetime import datetime, timezone
from pathlib import Path
from prometheus_client import Counter, Histogram, start_http_server

from rabbitmq.connection import get_connection, publish
from utils.file_logger import append_log
from evaluation.artifacts import record as record_evaluation
from agents.schema_validator import ALLOWED_ACTIONS

log = structlog.get_logger()

POLICY_LATENCY = Histogram("fyp_policy_latency_s", "Policy Agent latency")
ROUTING_DECISION = Counter(
    "fyp_routing_decision_total", "Routing decisions", ["decision", "reason"]
)
CONTROL_PLANE_PROCESSING_LATENCY = Histogram(
    "fyp_control_plane_processing_latency_seconds",
    "Triage + Strategy + Policy processing latency, excluding queue wait",
    buckets=(0.1, 0.5, 1, 2, 5, 10, 20, 30, 45, 60),
)
END_TO_END_DECISION_LATENCY = Histogram(
    "fyp_end_to_end_decision_latency_seconds",
    "Triage timestamp to Policy decision latency, including inter-agent queue wait",
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 900, 1800),
)
TIMESTAMP_MISSING = Counter(
    "fyp_timestamp_missing_total", "Events missing original timestamp", ["agent"]
)

start_http_server(8012)

BASE_DIR = Path(__file__).resolve().parent.parent
THRESHOLD_PATH = BASE_DIR / "config" / "threshold_config.json"

def load_threshold() -> float:
    """Load confidence threshold from disk — called on every message."""
    try:
        data = json.loads(THRESHOLD_PATH.read_text())
        t = float(data.get("confidence_threshold", 0.65))
        return max(0.60, min(0.90, t))
    except Exception:
        return 0.65


class PolicyAgent:
    def __init__(self):
        self.conn = get_connection()
        self.ch = self.conn.channel()
        log.info("policy_agent_started")

    def route(self, strategy: dict, threshold: float) -> tuple:
        """Apply 5-rule routing table. Returns (decision, reason, target_queue)."""
        triage = strategy.get("triage_result", {})
        llm = strategy.get("llm_response", {})
        timed = strategy.get("timed_out", False)
        valid = strategy.get("valid_json", False)
        schema_valid = strategy.get("schema_valid", False)
        f_type = triage.get("original_event", {}).get("fusion_type", "")
        tier = llm.get("risk_tier")
        confidence = llm.get("confidence")
        actions = llm.get("recommended_actions")

        # Rule 1 — Timeout or parse error
        if timed:
            return "HITL", "TIMEOUT", "hitl.queue"
        if not valid:
            return "HITL", "PARSE_ERROR", "hitl.queue"
        if schema_valid is not True:
            return "HITL", "SCHEMA_INVALID", "hitl.queue"
        if tier not in {"LOW", "HIGH"}:
            return "HITL", "INVALID_RISK_TIER", "hitl.queue"
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            return "HITL", "INVALID_CONFIDENCE", "hitl.queue"
        conf = float(confidence)
        if not math.isfinite(conf) or not 0.0 <= conf <= 1.0:
            return "HITL", "INVALID_CONFIDENCE", "hitl.queue"
        if not isinstance(actions, list) or len(actions) != 3 or any(
            not isinstance(action, str) or action not in ALLOWED_ACTIONS for action in actions
        ):
            return "HITL", "UNSUPPORTED_ACTION", "hitl.queue"

        # Retained for compatibility with historical Fusion payloads.
        if f_type == "low_confidence":
            return "HITL", "FUSION_LOW_CONFIDENCE", "hitl.queue"

        if tier == "HIGH":
            return "HITL", "HIGH_RISK", "hitl.queue"
        if conf < threshold:
            return "HITL", "LOW_CONFIDENCE", "hitl.queue"
        return "AUTO", "LOW_RISK_HIGH_CONFIDENCE", "auto.execute"

    def on_message(self, ch, method, props, body):
        t0 = time.monotonic()
        try:
            strategy = json.loads(body)
            event_id = strategy.get("event_id", "unknown")
            threshold = load_threshold()

            decision, reason, target_queue = self.route(strategy, threshold)

            policy_time = datetime.now(timezone.utc)
            policy_timestamp = policy_time.isoformat()

            # End-to-end decision latency: Triage timestamp → Policy decision.
            try:
                triage_result = strategy.get("triage_result", {})
                ts = triage_result.get("triage_timestamp")

                if ts:
                    try:
                        start_time = datetime.fromisoformat(ts)
                        if start_time.tzinfo is None:
                            start_time = start_time.replace(tzinfo=timezone.utc)
                        else:
                            start_time = start_time.astimezone(timezone.utc)

                        end_to_end_latency_s = (policy_time - start_time).total_seconds()
                        END_TO_END_DECISION_LATENCY.observe(end_to_end_latency_s)
                    except Exception:
                        log.warning("decision_latency_timestamp_parse_failed", event_id=event_id, ts=ts)
                        TIMESTAMP_MISSING.labels(agent="policy").inc()
                else:
                    log.warning("decision_latency_no_triage_timestamp", event_id=event_id)
                    TIMESTAMP_MISSING.labels(agent="policy").inc()
            except Exception:
                pass
            # ---------------------------------------

            result = {
                "event_id": event_id,
                "policy_timestamp": policy_timestamp,
                "routing_decision": decision,
                "routing_reason": reason,
                "threshold_used": threshold,
                "policy_agent_latency_ms": round((time.monotonic() - t0) * 1000),
                "full_reasoning_chain": {
                    "triage_result": strategy.get("triage_result"),
                    "strategy_result": strategy,
                },
            }
            triage_latency_s = None
            end_to_end_decision_latency_s = None
            try:
                triage_latency_s = float(
                    strategy["triage_result"]["triage_agent_latency_ms"]
                ) / 1000.0
            except Exception:
                pass
            try:
                triage_start = datetime.fromisoformat(
                    strategy["triage_result"]["triage_timestamp"]
                )
                if triage_start.tzinfo is None:
                    triage_start = triage_start.replace(tzinfo=timezone.utc)
                else:
                    triage_start = triage_start.astimezone(timezone.utc)
                end_to_end_decision_latency_s = (policy_time - triage_start).total_seconds()
            except Exception:
                pass
            try:
                strategy_latency_s = float(strategy["strategy_agent_latency_ms"]) / 1000.0
                policy_latency_s = result["policy_agent_latency_ms"] / 1000.0
                if all(value >= 0 for value in (triage_latency_s, strategy_latency_s, policy_latency_s)):
                    CONTROL_PLANE_PROCESSING_LATENCY.observe(
                        triage_latency_s + strategy_latency_s + policy_latency_s
                    )
            except (KeyError, TypeError, ValueError):
                pass
            record_evaluation("policy", {
                "event_id": event_id,
                "routing_decision": decision,
                "routing_reason": reason,
                "destination_queue": target_queue,
                "policy_timestamp": result["policy_timestamp"],
                "policy_latency_s": result["policy_agent_latency_ms"] / 1000.0,
                "triage_latency_s": triage_latency_s,
                "end_to_end_decision_latency_s": end_to_end_decision_latency_s,
            })

            # ---- File-based persistent log ----
            append_log("policy_agent.jsonl", {
                "event_id": event_id,
                "routing_decision": decision,
                "routing_reason": reason,
                "threshold_used": threshold,
                "latency_ms": result["policy_agent_latency_ms"],
            })

            publish(self.ch, target_queue, json.dumps(result))
            ch.basic_ack(method.delivery_tag)

            POLICY_LATENCY.observe(time.monotonic() - t0)
            ROUTING_DECISION.labels(decision=decision, reason=reason).inc()

            log.info(
                "policy_routed",
                event_id=event_id,
                decision=decision,
                reason=reason,
                latency_ms=result["policy_agent_latency_ms"],
            )

        except Exception as e:
            log.error("policy_error", error=str(e))
            ch.basic_nack(method.delivery_tag, requeue=False)

    def run(self):
        self.ch.basic_qos(prefetch_count=1)
        self.ch.basic_consume("strategy.result", self.on_message)
        log.info("policy_consuming", queue="strategy.result")
        self.ch.start_consuming()


if __name__ == "__main__":
    PolicyAgent().run()
