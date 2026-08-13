"""Learning Agent — qwen3:0.6b summarisation + ChromaDB upsert + EMA update."""
import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog
from datetime import datetime, timezone
from pathlib import Path
from prometheus_client import Counter, Gauge, Histogram, start_http_server

from rabbitmq.connection import get_connection
from chromadb_utils.upsert import upsert_incident
from ollama.client import generate

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
    "Mean Time To Recovery (anomaly timestamp -> outcome feedback received)",
    buckets=[30, 60, 120, 180, 300, 600, 900]
)

start_http_server(8013)

SYSTEM_PROMPT = Path("prompts/learning_system_prompt.txt").read_text()
THRESHOLD_PATH = Path("config/threshold_config.json")
MODEL = "qwen3:0.6b"
LEARNING_TIMEOUT = 10

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
    THRESHOLD_PATH.write_text(json.dumps(data, indent=2))


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
        log.info("learning_agent_started", model=MODEL)

    def _build_summary_prompt(self, outcome: dict) -> str:
        pr = outcome.get("full_policy_result", {})
        chain = pr.get("full_reasoning_chain", {})
        st = chain.get("strategy_result", {})
        llm = st.get("llm_response", {})
        triage = chain.get("triage_result", {})
        ev = triage.get("original_event", {})

        anomaly_type = triage.get("anomaly_type") or ev.get("anomaly_type", "?")
        component = ev.get("affected_component") or triage.get("anomaly_type", "?")
        node = ev.get("node") or "?"

        return (
            f"Incident: {anomaly_type} on {component}\n"
            f"Severity: {triage.get('severity','?')} | Risk tier: {llm.get('risk_tier','?')}\n"
            f"Outcome: {outcome.get('outcome_type','?')}\n"
            f"Actions taken: {outcome.get('actual_actions_taken',[])}\n"
            f"Operator notes: {outcome.get('operator_notes','none')}\n"
            f"Resolution time: {outcome.get('resolution_time_ms',0)}ms\n"
            "Summarise this incident in one sentence."
        )

    def on_message(self, ch, method, props, body):
        t0 = time.monotonic()
        try:
            outcome = json.loads(body)
            event_id = outcome.get("event_id", "unknown")
            outcome_type = outcome.get("outcome_type", "UNKNOWN")

            OUTCOMES_PROCESSED.labels(outcome_type=outcome_type).inc()

            # MTTR calculation
            try:
                ev = outcome.get("full_policy_result", {}).get(
                    "full_reasoning_chain", {}
                ).get("triage_result", {}).get("original_event", {})
                ts = ev.get("timestamp")
                if ts:
                    anomaly_time = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
                    mttr = (datetime.now(timezone.utc) - anomaly_time).total_seconds()
                    MTTR_HISTOGRAM.observe(mttr)
            except Exception:
                pass

            # Summarise with qwen3:0.6b
            summary = f"Incident {event_id} - {outcome_type}"
            try:
                resp = generate(
                    MODEL,
                    self._build_summary_prompt(outcome),
                    SYSTEM_PROMPT,
                    num_predict=256,
                    timeout=LEARNING_TIMEOUT,
                )
                summary = resp.get("response", summary).strip()
            except Exception as e:
                log.warning("learning_llm_failed", error=str(e))

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