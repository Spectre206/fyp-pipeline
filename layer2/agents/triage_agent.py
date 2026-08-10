"""Triage Agent — Rule-Based Classifier + ChromaDB RAG."""
import json
import time
import structlog
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from prometheus_client import Counter, Histogram, start_http_server

from rabbitmq.connection import get_connection, publish
from chromadb_utils.query import retrieve_rag_context, format_rag_context

log = structlog.get_logger()

TRIAGE_LATENCY = Histogram("fyp_triage_latency_s", "Triage Agent latency")
TRIAGE_PROCESSED = Counter(
    "fyp_triage_processed_total", "Events triaged", ["anomaly_type"]
)
TRIAGE_TIMEOUT = Counter("fyp_triage_timeout_total", "Triage timeouts")

start_http_server(8010)

# (anomaly_type, severity) → response_protocol
PROTOCOL_TABLE = {
    ("cpu_memory_spike",   "CRITICAL"): "EMERGENCY_RESTART_CONSUMER",
    ("cpu_memory_spike",   "HIGH"):     "SCALE_CONSUMER_RESOURCES",
    ("cpu_memory_spike",   "MEDIUM"):   "MONITOR_AND_ALERT",
    ("cpu_memory_spike",   "LOW"):      "LOG_AND_CONTINUE",
    ("error_rate_surge",   "CRITICAL"): "CIRCUIT_BREAKER_OPEN",
    ("error_rate_surge",   "HIGH"):     "RATE_LIMIT_ENDPOINT",
    ("error_rate_surge",   "MEDIUM"):   "INVESTIGATE_UPSTREAM",
    ("error_rate_surge",   "LOW"):      "LOG_AND_CONTINUE",
    ("throughput_drop",    "CRITICAL"): "RESTART_ALL_CONSUMERS",
    ("throughput_drop",    "HIGH"):     "RESTART_FAILED_CONSUMER",
    ("throughput_drop",    "MEDIUM"):   "CHECK_QUEUE_DEPTH",
    ("auth_failure_flood", "CRITICAL"): "ISOLATE_NODE",
    ("auth_failure_flood", "HIGH"):     "RATE_LIMIT_AUTH",
    ("auth_failure_flood", "MEDIUM"):   "ALERT_SECURITY_TEAM",
    ("schema_drift",       "HIGH"):     "HALT_INGESTION_REVIEW_SCHEMA",
    ("schema_drift",       "MEDIUM"):   "FLAG_FOR_SCHEMA_REVIEW",
    ("compound",           "CRITICAL"): "EMERGENCY_FULL_PIPELINE_REVIEW",
    ("compound",           "HIGH"):     "COORDINATED_REMEDIATION",
}

# Map Fusion Engine model names → anomaly types
MODEL_TO_TYPE = {
    "z_score_cpu_memory":        "cpu_memory_spike",
    "z_score_error_rate":        "error_rate_surge",
    "moving_average_throughput": "throughput_drop",
    "rate_gate_auth_rf":         "auth_failure_flood",
    "psi_detector":              "schema_drift",
}

TRIAGE_TIMEOUT_S = 5.0


class TriageAgent:
    def __init__(self):
        self.conn = get_connection()
        self.ch = self.conn.channel()
        log.info("triage_agent_started")

    def classify(self, event: dict) -> str:
        """Return response protocol for this event, with fallback."""
        atype = event.get("anomaly_type", "UNKNOWN")
        sev = event.get("severity", "MEDIUM")
        return PROTOCOL_TABLE.get(
            (atype, sev),
            PROTOCOL_TABLE.get((atype, "HIGH"), "GENERIC_INVESTIGATE"),
        )

    def _normalize_event(self, event: dict) -> dict:
        """
        Fused events from Fusion Engine lack anomaly_type/severity.
        Derive them from contributing_models and fused_severity so the
        classification table works correctly. Validator bypass events
        already have these fields and pass through unchanged.
        """
        # Derive anomaly_type if missing
        if not event.get("anomaly_type"):
            models = event.get("contributing_models", [])
            if len(models) > 1:
                event["anomaly_type"] = "compound"
            elif len(models) == 1:
                model_name = models[0].get("model_name", "")
                event["anomaly_type"] = MODEL_TO_TYPE.get(model_name, "unknown")
            else:
                event["anomaly_type"] = "unknown"

        # Use fused_severity if severity is missing
        if not event.get("severity"):
            event["severity"] = event.get("fused_severity", "MEDIUM")

        return event

    def on_message(self, ch, method, props, body):
        t0 = time.monotonic()
        try:
            event = json.loads(body)
            event_id = event.get("event_id", "unknown")

            # Keep original untouched for the triage.result payload
            original_event = dict(event)

            # Normalize fused events for classification
            event = self._normalize_event(event)

            # Rule-based classification
            protocol = self.classify(event)

            # ChromaDB RAG retrieval (cold start → empty)
            rag_context = []
            rag_formatted = ""
            try:
                rag_context = retrieve_rag_context(event, n_results=3)
                rag_formatted = format_rag_context(rag_context)
            except Exception as e:
                log.warning("rag_retrieval_failed", error=str(e))

            elapsed = time.monotonic() - t0
            if elapsed > TRIAGE_TIMEOUT_S:
                log.warning("triage_sla_exceeded", elapsed=elapsed)
                TRIAGE_TIMEOUT.inc()

            result = {
                "event_id":                event_id,
                "triage_timestamp":        datetime.now(timezone.utc).isoformat(),
                "anomaly_type":            event.get("anomaly_type"),
                "severity":                event.get("severity"),
                "fusion_type":             original_event.get("fusion_type"),
                "fusion_confidence":       original_event.get("fusion_confidence"),
                "contributing_models":     original_event.get("contributing_models", []),
                "response_protocol":       protocol,
                "rag_context":             rag_context,
                "rag_context_formatted":   rag_formatted,
                "triage_agent_latency_ms": round((time.monotonic() - t0) * 1000),
                "original_event":          original_event,
            }

            publish(self.ch, "triage.result", json.dumps(result))
            ch.basic_ack(method.delivery_tag)

            TRIAGE_LATENCY.observe(time.monotonic() - t0)
            TRIAGE_PROCESSED.labels(
                anomaly_type=event.get("anomaly_type", "?")
            ).inc()

            log.info(
                "triage_complete",
                event_id=event_id,
                protocol=protocol,
                rag_docs=len(rag_context),
                latency_ms=result["triage_agent_latency_ms"],
            )

        except Exception as e:
            log.error("triage_error", error=str(e))
            ch.basic_nack(method.delivery_tag, requeue=False)

    def run(self):
        self.ch.basic_qos(prefetch_count=1)
        self.ch.basic_consume("anomaly.detected", self.on_message)
        log.info("triage_consuming", queue="anomaly.detected")
        self.ch.start_consuming()


if __name__ == "__main__":
    TriageAgent().run()
