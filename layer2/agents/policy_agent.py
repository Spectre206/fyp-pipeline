"""Policy Agent — Deterministic 5-rule routing table."""
import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog
from datetime import datetime, timezone
from pathlib import Path
from prometheus_client import Counter, Histogram, start_http_server

from rabbitmq.connection import get_connection, publish

log = structlog.get_logger()

POLICY_LATENCY = Histogram("fyp_policy_latency_s", "Policy Agent latency")
ROUTING_DECISION = Counter(
    "fyp_routing_decision_total", "Routing decisions", ["decision", "reason"]
)
MTTA_HISTOGRAM = Histogram(
    "fyp_mtta_seconds",
    "Mean Time To Acknowledge (anomaly timestamp → policy decision)",
    buckets=[10, 20, 30, 40, 50, 60, 90, 120, 180, 300]
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
        f_type = triage.get("original_event", {}).get("fusion_type", "")
        tier = llm.get("risk_tier", "HIGH")
        conf = float(llm.get("confidence", 0.0))

        # Rule 1 — Timeout or parse error
        if timed or not valid:
            reason = "TIMEOUT" if timed else "PARSE_ERROR"
            return "HITL", reason, "hitl.queue"

        # Rule 2 — Fusion Engine low confidence (v1.2)
        if f_type == "low_confidence":
            return "HITL", "FUSION_LOW_CONFIDENCE", "hitl.queue"

        # Rule 3 — High risk tier
        if tier == "HIGH":
            return "HITL", "HIGH_RISK", "hitl.queue"

        # Rule 4 — Low risk but uncertain
        if conf < threshold:
            return "HITL", "LOW_CONFIDENCE", "hitl.queue"

        # Rule 5 — Safe for automatic execution
        return "AUTO", "LOW_RISK_HIGH_CONFIDENCE", "auto.execute"

    def on_message(self, ch, method, props, body):
        t0 = time.monotonic()
        try:
            strategy = json.loads(body)
            event_id = strategy.get("event_id", "unknown")
            threshold = load_threshold()

            decision, reason, target_queue = self.route(strategy, threshold)

            # ---------- MTTA calculation ----------
            # Extract the original anomaly timestamp from the triage result
            try:
                triage_result = strategy.get("triage_result", {})
                original_event = triage_result.get("original_event", {})
                ts = original_event.get("timestamp")
                if ts:
                    try:
                        anomaly_time = datetime.fromisoformat(ts)
                        # If the timestamp is naive (no tzinfo), assume UTC
                        if anomaly_time.tzinfo is None:
                            anomaly_time = anomaly_time.replace(tzinfo=timezone.utc)
                        else:
                            anomaly_time = anomaly_time.astimezone(timezone.utc)
                        mtta = (datetime.now(timezone.utc) - anomaly_time).total_seconds()
                        MTTA_HISTOGRAM.observe(mtta)
                    except Exception:
                        log.warning("mtta_timestamp_parse_failed", event_id=event_id, ts=ts)
                        TIMESTAMP_MISSING.labels(agent="policy").inc()
                else:
                    TIMESTAMP_MISSING.labels(agent="policy").inc()
            except Exception:
                pass
            # ---------------------------------------

            result = {
                "event_id": event_id,
                "policy_timestamp": datetime.now(timezone.utc).isoformat(),
                "routing_decision": decision,
                "routing_reason": reason,
                "threshold_used": threshold,
                "policy_agent_latency_ms": round((time.monotonic() - t0) * 1000),
                "full_reasoning_chain": {
                    "triage_result": strategy.get("triage_result"),
                    "strategy_result": strategy,
                },
            }

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