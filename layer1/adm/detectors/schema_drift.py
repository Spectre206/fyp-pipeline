"""Schema Drift Detector — structural bypass complement.

Consumes enriched events from the detect.schema queue.
Uses the explicit, structurally valid distribution-shift marker from value-shift
events. PSI is intentionally not computed in the active runtime vector.

Note: Only the statistical half of Model 5 is implemented here. The structural half
(missing fields, type mutations) is caught earlier by the Pydantic Validator and
routed directly to anomaly.detected — those events never reach this detector.

Detection logic:
  - Primary: distribution_shift_marker == 1.0 catches genuine value_shift events.
    These are schema_drift events where the metric distribution is statistically
    shifted but the structure is valid (so they pass Pydantic validation).
Always publishes a result to fusion.results (detected=True or False).
"""

import json
import logging
import time
import pika
import structlog
from prometheus_client import Counter, Histogram, start_http_server
from detector_support import detector_results_path, load_detector_config

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

_SETTINGS = load_detector_config("schema_drift", {"distribution_shift_marker": 1.0, "confidence": 0.7})

INPUT_QUEUE     = "detect.schema"
OUTPUT_EXCHANGE = "fyp.events"
ROUTING_KEY     = "fusion.result"
MODEL_NAME      = "distribution_shift_marker"


class SchemaDetector:
    def __init__(self, host: str = "stream-node", port: int = 5672):
        params = pika.ConnectionParameters(
            host=host, port=port, virtual_host="fyp",
            credentials=pika.PlainCredentials("fyp_user", "fyp_pass_2026"),
            heartbeat=60, blocked_connection_timeout=30,
        )
        self.conn = pika.BlockingConnection(params)
        self.ch = self.conn.channel()
        log.info("schema_detector_initialised", shift_marker=_SETTINGS["distribution_shift_marker"])

    def detect(self, event: dict) -> dict:
        start = time.time()
        event_id = event.get("event_id", "UNKNOWN")
        anomaly_type = event.get("anomaly_type", "UNKNOWN")
        EVAL_COUNT.labels(detector=DETECTOR_NAME, anomaly_type=anomaly_type).inc()

        try:
            raw_mv = event.get("metric_values", {})

            if not isinstance(raw_mv, dict):
                return {
                    "event_id": event_id,
                    "timestamp": event.get("timestamp"),
                    "ingestion_time": event.get("ingestion_time"),
                     "node": event.get("node"),
                    "affected_component": event.get("affected_component"),
                    "detected": False,
                    "anomaly_type": "NORMAL",
                    "severity": "N/A",
                    "confidence": 0.0,
                    "model_name": MODEL_NAME,
                    "metadata": {"reason": "no valid metrics"}
                }

            shift_marker = raw_mv.get("distribution_shift_marker", 0.0)

            detected = False
            severity = "N/A"
            reason = ""

            if shift_marker == _SETTINGS["distribution_shift_marker"]:
                detected = True
                severity = "MEDIUM"
                reason = "distribution_shift_marker=1.0 (value_shift event)"
                confidence = _SETTINGS["confidence"]
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
                "node": event.get("node"),
                "affected_component": event.get("affected_component"),
                "detected": detected,
                "anomaly_type": "schema_drift" if detected else "NORMAL",
                "severity": severity,
                "confidence": round(confidence, 4),
                "model_name": MODEL_NAME,
                "metadata": {
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
                "node": event.get("node"),
                "affected_component": event.get("affected_component"),
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
            with detector_results_path("schema_results.jsonl").open("a") as f:
                f.write(json.dumps(result) + "\n")

            if result["detected"]:
                log.info("anomaly_detected", event_id=result["event_id"],
                         severity=result["severity"], shift_marker=result["metadata"]["distribution_shift_marker"])
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
