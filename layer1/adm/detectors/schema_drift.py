# layer1/adm/detectors/schema_shift.py
"""
Schema Drift Detector — PSI-Based (Model 5, Statistical Half)

Consumes enriched events from the detect.schema queue.
Uses pre‑computed PSI (Population Stability Index) scores from the Feature Store
and the distribution_shift_marker flag from value_shift events.

Note: Only the statistical half of Model 5 is implemented here. The structural half
(missing fields, type mutations) is caught earlier by the Pydantic Validator and
routed directly to anomaly.detected — those events never reach this detector.

Detection logic:
  - Primary: distribution_shift_marker == 1.0 catches genuine value_shift events.
    These are schema_drift events where the metric distribution is statistically
    shifted but the structure is valid (so they pass Pydantic validation).
  - PSI scores are computed correctly by the Feature Store (v1.2 fix applied),
    but the synthetic corpus characteristics (high variance within components)
    cause elevated PSI across most events. PSI is therefore used as a confidence
    booster rather than a standalone detector. See LAYER1_COMPONENT_LOG.md.

Always publishes a result to fusion.results (detected=True or False).
"""

"""
Schema Drift Detector — PSI + Shift Marker (Model 5) with Prometheus Metrics
"""

import json
import logging
import time
from pathlib import Path

import pika
import structlog
from prometheus_client import Counter, Histogram, start_http_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCHEMA_DETECTOR] %(levelname)s %(message)s"
)
log = structlog.get_logger()

DETECTOR_NAME = "schema_drift"
PROM_PORT = 8008
start_http_server(PROM_PORT)

EVAL_COUNT = Counter(
    "fyp_detector_evaluations_total",
    "Detector evaluations",
    ["detector", "anomaly_type"]
)
ANOMALY_COUNT = Counter(
    "fyp_detector_anomalies_total",
    "Detector anomalies",
    ["detector", "anomaly_type"]
)
ERROR_COUNT = Counter(
    "fyp_detector_errors_total",
    "Detector errors",
    ["detector"]
)
LATENCY = Histogram(
    "fyp_detector_latency_seconds",
    "Detector latency",
    ["detector"]
)

PSI_HIGH_THRESHOLD   = 0.5
PSI_MEDIUM_THRESHOLD = 0.2

INPUT_QUEUE     = "detect.schema"
OUTPUT_EXCHANGE = "fyp.events"
ROUTING_KEY     = "fusion.result"
MODEL_NAME      = "psi_detector"


class SchemaDetector:
    def __init__(self, host: str = "stream-node", port: int = 5672):
        params = pika.ConnectionParameters(
            host=host, port=port, virtual_host="fyp",
            credentials=pika.PlainCredentials("fyp_user", "fyp_pass_2026"),
            heartbeat=60, blocked_connection_timeout=30,
        )
        self.conn = pika.BlockingConnection(params)
        self.ch = self.conn.channel()
        log.info("schema_detector_initialised",
                 psi_medium_threshold=PSI_MEDIUM_THRESHOLD,
                 psi_high_threshold=PSI_HIGH_THRESHOLD)

    def detect(self, event: dict) -> dict:
        start = time.time()
        event_id = event.get("event_id", "UNKNOWN")
        anomaly_type = event.get("anomaly_type", "UNKNOWN")
        EVAL_COUNT.labels(detector=DETECTOR_NAME, anomaly_type=anomaly_type).inc()

        try:
            fv = event.get("feature_vector", {})
            raw_mv = event.get("metric_values", {})

            if not isinstance(raw_mv, dict):
                return {
                    "event_id": event_id,
                    "timestamp": event.get("timestamp"),
                    "ingestion_time": event.get("ingestion_time"),
                    "detected": False,
                    "anomaly_type": "NORMAL",
                    "severity": "N/A",
                    "confidence": 0.0,
                    "model_name": MODEL_NAME,
                    "metadata": {"reason": "no valid metrics"}
                }

            psi_scores = {}
            for key, value in fv.items():
                if key.startswith("psi_score_"):
                    metric = key.replace("psi_score_", "")
                    psi_scores[metric] = float(value)

            max_psi = max(psi_scores.values()) if psi_scores else 0.0
            shift_marker = raw_mv.get("distribution_shift_marker", 0.0)

            detected = False
            severity = "N/A"
            reason = ""

            if shift_marker == 1.0:
                detected = True
                severity = "MEDIUM"
                reason = "distribution_shift_marker=1.0 (value_shift event)"
                confidence = 0.70
                if max_psi >= PSI_HIGH_THRESHOLD:
                    confidence = min(0.95, confidence + 0.20)
                elif max_psi >= PSI_MEDIUM_THRESHOLD:
                    confidence = min(0.90, confidence + 0.10)
            else:
                detected = False
                confidence = 0.0

            if detected:
                ANOMALY_COUNT.labels(
                    detector=DETECTOR_NAME, anomaly_type=anomaly_type
                ).inc()

            return {
                "event_id": event_id,
                "timestamp": event.get("timestamp"),
                "ingestion_time": event.get("ingestion_time"),
                "detected": detected,
                "anomaly_type": "schema_drift" if detected else "NORMAL",
                "severity": severity,
                "confidence": round(confidence, 4),
                "model_name": MODEL_NAME,
                "metadata": {
                    "psi_scores": {k: round(v, 6) for k, v in psi_scores.items()},
                    "max_psi": round(max_psi, 6),
                    "distribution_shift_marker": shift_marker,
                    "reason": reason,
                }
            }
        except Exception as exc:
            ERROR_COUNT.labels(detector=DETECTOR_NAME).inc()
            log.error("detector_error", error=str(exc))
            return {
                "event_id": event_id,
                "timestamp": event.get("timestamp"),
                "ingestion_time": event.get("ingestion_time"),
                "detected": False,
                "anomaly_type": "NORMAL",
                "severity": "N/A",
                "confidence": 0.0,
                "model_name": MODEL_NAME,
                "metadata": {"reason": "error"}
            }
        finally:
            LATENCY.labels(detector=DETECTOR_NAME).observe(time.time() - start)

    def on_message(self, ch, method, props, body):
        try:
            event = json.loads(body)
        except json.JSONDecodeError as exc:
            log.error("json_parse_error", error=str(exc))
            ch.basic_nack(method.delivery_tag, requeue=False)
            return

        result = self.detect(event)

        try:
            self.ch.basic_publish(
                exchange=OUTPUT_EXCHANGE, routing_key=ROUTING_KEY,
                body=json.dumps(result).encode(),
                properties=pika.BasicProperties(delivery_mode=2, content_type="application/json")
            )
            with open("/home/asim/fyp-pipeline/layer1/adm/schema_results.jsonl", "a") as f:
                f.write(json.dumps(result) + "\n")

            if result["detected"]:
                log.info("anomaly_detected", event_id=result["event_id"],
                         severity=result["severity"], max_psi=result["metadata"]["max_psi"])
            else:
                log.debug("event_clean", event_id=result["event_id"])
        except Exception as exc:
            log.error("publish_error", event_id=result["event_id"], error=str(exc))
            ch.basic_nack(method.delivery_tag, requeue=True)
            return

        ch.basic_ack(method.delivery_tag)

    def run(self):
        self.ch.basic_qos(prefetch_count=1)
        self.ch.basic_consume(queue=INPUT_QUEUE, on_message_callback=self.on_message)
        log.info("schema_detector_started", queue=INPUT_QUEUE)
        try:
            self.ch.start_consuming()
        except KeyboardInterrupt:
            log.info("schema_detector_stopping")
            self.ch.stop_consuming()
        finally:
            if self.conn and not self.conn.is_closed:
                self.conn.close()


if __name__ == "__main__":
    SchemaDetector().run()