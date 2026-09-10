"""Learning Agent — deterministic summaries + ChromaDB upsert + EMA update."""
import json
import time
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog
from datetime import datetime, timezone
from pathlib import Path
from prometheus_client import Counter, Gauge, Histogram, start_http_server

from rabbitmq.connection import get_connection
from chromadb_utils.upsert import upsert_incident
from utils.file_logger import append_log
from evaluation.artifacts import record as record_evaluation

log = structlog.get_logger()

OUTCOMES_PROCESSED = Counter(
    "fyp_learning_outcomes_total", "Outcomes processed", ["outcome_type"]
)
THRESHOLD_UPDATES = Counter(
    "fyp_learning_threshold_updates_total", "EMA threshold updates"
)
CHROMADB_UPSERTS = Counter(
    "fyp_learning_chromadb_upserts_total", "ChromaDB upserts"
)
THRESHOLD_GAUGE = Gauge(
    "fyp_learning_confidence_threshold",
    "Current EMA confidence threshold"
)
MTTR_HISTOGRAM = Histogram(
    "fyp_mttr_seconds",
    "Mean Time To Recovery (triage_timestamp → outcome feedback received)",
    buckets=[30, 60, 120, 180, 300, 600, 900]
)
TIMESTAMP_MISSING = Counter(
    "fyp_timestamp_missing_total", "Events missing original timestamp", ["agent"]
)

start_http_server(8013)

BASE_DIR = Path(__file__).resolve().parent.parent
THRESHOLD_PATH = BASE_DIR / "config" / "threshold_config.json"

OUTCOME_SIGNALS = {
    "AUTO_EXECUTE_SUCCESS": 0.80,
    "AUTO_EXECUTE_FAILURE": 0.50,
    "HITL_APPROVED": 0.75,
    "HITL_REJECTED": 0.40,
    "HITL_MODIFIED": 0.60,
}
NEGATIVE_OUTCOMES = {"AUTO_EXECUTE_FAILURE", "HITL_REJECTED"}
def load_threshold_config() -> dict:
    try:
        return json.loads(THRESHOLD_PATH.read_text())
    except Exception:
        return {"confidence_threshold": 0.65, "update_count": 0, "ema_alpha": 0.9}


current_cfg = load_threshold_config()
THRESHOLD_GAUGE.set(current_cfg.get("confidence_threshold", 0.65))


def save_threshold_config(data: dict):
    THRESHOLD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=THRESHOLD_PATH.parent, delete=False
    ) as temporary_file:
        json.dump(data, temporary_file, indent=2)
        temporary_file.flush()
        os.fsync(temporary_file.fileno())
        temporary_path = temporary_file.name
    os.replace(temporary_path, THRESHOLD_PATH)


def update_ema(outcome_type: str):
    signal = OUTCOME_SIGNALS.get(outcome_type)
    if signal is None:
        return

    cfg = load_threshold_config()
    alpha = float(cfg.get("ema_alpha", 0.9))
    current = float(cfg.get("confidence_threshold", 0.65))
    new_t = alpha * current + (1 - alpha) * signal
    new_t = max(0.60, min(0.90, new_t))

    cfg["confidence_threshold"] = round(new_t, 4)
    cfg["last_updated"] = datetime.now(timezone.utc).isoformat()
    cfg["update_count"] = cfg.get("update_count", 0) + 1
    save_threshold_config(cfg)

    THRESHOLD_GAUGE.set(new_t)
    THRESHOLD_UPDATES.inc()
    log.info(
        "ema_updated",
        old=round(current, 4),
        new=round(new_t, 4),
        signal=signal,
        outcome=outcome_type,
    )


class LearningAgent:
    def __init__(self):
        self.conn = get_connection()
        self.ch = self.conn.channel()
        log.info("learning_agent_started", summary_mode="deterministic")

    def _deterministic_summary(self, outcome: dict) -> str:
        """Build a stable Chroma document without invoking Ollama."""
        policy = outcome.get("full_policy_result", {})
        chain = policy.get("full_reasoning_chain", {})
        strategy = chain.get("strategy_result", {})
        llm = strategy.get("llm_response", {})
        triage = chain.get("triage_result", {})
        event = triage.get("original_event", {})

        parts = []
        event_id = outcome.get("event_id")
        anomaly_type = triage.get("anomaly_type") or event.get("anomaly_type")
        component = event.get("affected_component")
        actions = outcome.get("actual_actions_taken")
        decision = policy.get("routing_decision")
        outcome_type = outcome.get("outcome_type")
        risk_tier = llm.get("risk_tier")
        confidence = llm.get("confidence")
        if event_id:
            parts.append(f"event_id={event_id}")
        if anomaly_type:
            parts.append(f"anomaly_type={anomaly_type}")
        if component:
            parts.append(f"component={component}")
        if isinstance(actions, list) and actions:
            parts.append("actions=" + ", ".join(str(action) for action in actions))
        if decision:
            parts.append(f"decision={decision}")
        if outcome_type:
            parts.append(f"outcome={outcome_type}")
        if risk_tier:
            parts.append(f"risk={risk_tier}")
        if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
            parts.append(f"confidence={confidence}")
        return "; ".join(parts) or "outcome=UNKNOWN"

    def on_message(self, ch, method, props, body):
        t0 = time.monotonic()
        try:
            outcome = json.loads(body)
            event_id = outcome.get("event_id", "unknown")
            outcome_type = outcome.get("outcome_type", "UNKNOWN")
            feedback_timestamp = datetime.now(timezone.utc).isoformat()
            feedback_latency_s = None

            OUTCOMES_PROCESSED.labels(outcome_type=outcome_type).inc()

            # ---------- MTTR calculation ----------
            # Control-plane MTTR: triage_timestamp → outcome feedback received
            try:
                chain = outcome.get("full_policy_result", {}).get(
                    "full_reasoning_chain", {}
                )
                triage_result = chain.get("triage_result", {})
                ts = triage_result.get("triage_timestamp")

                if ts:
                    try:
                        start_time = datetime.fromisoformat(ts)
                        if start_time.tzinfo is None:
                            start_time = start_time.replace(tzinfo=timezone.utc)
                        else:
                            start_time = start_time.astimezone(timezone.utc)

                        mttr = (datetime.now(timezone.utc) - start_time).total_seconds()
                        feedback_latency_s = mttr
                        MTTR_HISTOGRAM.observe(mttr)
                    except Exception:
                        log.warning("mttr_timestamp_parse_failed", event_id=event_id, ts=ts)
                        TIMESTAMP_MISSING.labels(agent="learning").inc()
                else:
                    log.warning("mttr_no_timestamp", event_id=event_id)
                    TIMESTAMP_MISSING.labels(agent="learning").inc()
            except Exception:
                pass
            # ---------------------------------------

            # This records receipt before best-effort learning work begins.
            # A separate learning record below captures successful processing.
            record_evaluation("feedback", {
                "event_id": event_id,
                "outcome_type": outcome_type,
                "feedback_timestamp": feedback_timestamp,
                "feedback_latency_s": feedback_latency_s,
            })

            summary_mode = "deterministic"
            summary = self._deterministic_summary(outcome)

            # Build ChromaDB metadata
            pr = outcome.get("full_policy_result", {})
            chain = pr.get("full_reasoning_chain", {})
            st = chain.get("strategy_result", {})
            llm = st.get("llm_response", {})
            triage = chain.get("triage_result", {})
            ev = triage.get("original_event", {})

            metadata = {
                "incident_id": event_id,
                "anomaly_type": triage.get("anomaly_type")
                or ev.get("anomaly_type", "unknown"),
                "risk_tier": llm.get("risk_tier", "HIGH"),
                "outcome_type": outcome_type,
                "confidence_at_decision": float(llm.get("confidence", 0.0)),
                "fusion_type": ev.get("fusion_type", "single"),
                "severity": triage.get("severity") or ev.get("severity", "MEDIUM"),
                "node": ev.get("node")
                or triage.get("original_event", {}).get("node")
                or "unknown",
                "affected_component": ev.get("affected_component") or "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operator_approved": outcome_type
                in {"HITL_APPROVED", "HITL_MODIFIED"},
                "negative_example": outcome_type in NEGATIVE_OUTCOMES,
            }

            upsert_incident(event_id, summary, metadata)
            CHROMADB_UPSERTS.inc()

            update_ema(outcome_type)
            record_evaluation("learning", {
                "event_id": event_id,
                "outcome_type": outcome_type,
                "summary_mode": summary_mode,
                "learning_latency_s": time.monotonic() - t0,
                "chromadb_upsert_id": event_id,
                "threshold_updated": outcome_type in OUTCOME_SIGNALS,
            })

            # ---- File-based persistent log ----
            append_log("learning_agent.jsonl", {
                "event_id": event_id,
                "outcome_type": outcome_type,
                "summary": summary,
                "latency_ms": round((time.monotonic() - t0) * 1000),
            })

            ch.basic_ack(method.delivery_tag)
            log.info(
                "learning_complete",
                event_id=event_id,
                outcome=outcome_type,
                latency_ms=round((time.monotonic() - t0) * 1000),
            )

        except Exception as e:
            log.error("learning_error", error=str(e))
            ch.basic_nack(method.delivery_tag, requeue=False)

    def run(self):
        self.ch.basic_qos(prefetch_count=1)
        self.ch.basic_consume("outcome.feedback", self.on_message)
        log.info("learning_consuming", queue="outcome.feedback")
        self.ch.start_consuming()


if __name__ == "__main__":
    LearningAgent().run()
