# layer1/adm/detectors/error_detector.py
"""
Error Rate Surge Detector — Statistical Z-Score (Model 2)

Consumes enriched events from the detect.error queue.
Uses the feature_vector.z_score_error_rate_percent computed by the Feature Store.
Flags an anomaly when |Z| > 3.0 OR error_rate_percent > 10% (step-change catch).

Publishes EVERY result to fusion.results (detected=True or False),
so the Fusion Engine always knows this model processed the event.
"""

"""
Error Rate Surge Detector — Statistical Z-Score (Model 2) with Prometheus Metrics
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
    format="%(asctime)s [ERROR_DETECTOR] %(levelname)s %(message)s"
)
log = structlog.get_logger()

DETECTOR_NAME = "error_rate"
PROM_PORT = 8004
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

Z_SCORE_THRESHOLD = 2.0
ERROR_RATE_THRESHOLD = 10.0

INPUT_QUEUE      = "detect.error"
OUTPUT_EXCHANGE  = "fyp.events"
ROUTING_KEY      = "fusion.result"
MODEL_NAME       = "z_score_error_rate"


class ErrorRateDetector:
    def __init__(self, host: str = "stream-node", port: int = 5672):
        params = pika.ConnectionParameters(
            host=host, port=port, virtual_host="fyp",
            credentials=pika.PlainCredentials("fyp_user", "fyp_pass_2026"),
            heartbeat=60, blocked_connection_timeout=30,
        )
        self.conn = pika.BlockingConnection(params)
        self.ch = self.conn.channel()
        log.info("error_detector_initialised",
                 input_queue=INPUT_QUEUE,
                 z_threshold=Z_SCORE_THRESHOLD)

    def detect(self, event: dict) -> dict:
        start = time.time()
        event_id = event.get("event_id", "UNKNOWN")
        anomaly_type = event.get("anomaly_type", "UNKNOWN")
        EVAL_COUNT.labels(detector=DETECTOR_NAME, anomaly_type=anomaly_type).inc()

        try:
            fv = event.get("feature_vector", {})
            z_score = fv.get("z_score_error_rate_percent", 0.0)
            error_rate = event.get("metric_values", {}).get("error_rate_percent", 0.0)

            detected = False
            severity = "N/A"
            reason = ""

            if abs(z_score) > Z_SCORE_THRESHOLD:
                detected = True
                severity = self._severity_from_z(abs(z_score))
                reason = f"Z-score |{z_score:.2f}| > {Z_SCORE_THRESHOLD}"
            elif error_rate > ERROR_RATE_THRESHOLD:
                detected = True
                severity = self._severity_from_rate(error_rate)
                reason = f"error_rate_percent {error_rate:.2f}% > {ERROR_RATE_THRESHOLD}%"

            confidence = self._confidence(abs(z_score), error_rate)

            if detected:
                ANOMALY_COUNT.labels(
                    detector=DETECTOR_NAME, anomaly_type=anomaly_type
                ).inc()

            return {
                "event_id": event_id,
                "timestamp": event.get("timestamp"),
                "ingestion_time": event.get("ingestion_time"),
                "detected": detected,
                "anomaly_type": "error_rate_surge" if detected else "NORMAL",
                "severity": severity,
                "confidence": confidence,
                "model_name": MODEL_NAME,
                "metadata": {
                    "z_score_error_rate_percent": round(z_score, 4),
                    "error_rate_percent": round(error_rate, 4),
                    "reason": reason,
                }
            }
        except Exception as exc:
            ERROR_COUNT.labels(detector=DETECTOR_NAME).inc()
            log.error("detector_error", error=str(exc))
            return {
                "event_id": event_id,
                "timestamp": event.get("timestamp"),
                "detected": False,
                "anomaly_type": "NORMAL",
                "severity": "N/A",
                "confidence": 0.0,
                "model_name": MODEL_NAME,
                "metadata": {"reason": "error"}
            }
        finally:
            LATENCY.labels(detector=DETECTOR_NAME).observe(time.time() - start)

    def _severity_from_z(self, abs_z: float) -> str:
        if abs_z >= 5.0: return "CRITICAL"
        elif abs_z >= 4.0: return "HIGH"
        return "MEDIUM"

    def _severity_from_rate(self, rate: float) -> str:
        if rate >= 30.0: return "CRITICAL"
        elif rate >= 18.0: return "HIGH"
        return "MEDIUM"

    def _confidence(self, abs_z: float, error_rate: float) -> float:
        z_conf = min(0.95, abs_z / 6.0)
        rate_conf = min(0.90, error_rate / 30.0)
        return round(max(z_conf, rate_conf), 4)

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
                exchange=OUTPUT_EXCHANGE,
                routing_key=ROUTING_KEY,
                body=json.dumps(result).encode("utf-8"),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json"
                )
            )
            with open("/home/asim/fyp-pipeline/layer1/adm/error_results.jsonl", "a") as f:
                f.write(json.dumps(result) + "\n")

            if result["detected"]:
                log.info("anomaly_detected", event_id=result["event_id"],
                         severity=result["severity"], confidence=result["confidence"])
            else:
                log.debug("event_clean", event_id=result["event_id"])

        except Exception as exc:
            log.error("publish_error", event_id=result["event_id"], error=str(exc))
            ch.basic_nack(method.delivery_tag, requeue=True)
            return

        ch.basic_ack(method.delivery_tag)

    def run(self):
        self.ch.basic_qos(prefetch_count=1)
        self.ch.basic_consume(
            queue=INPUT_QUEUE,
            on_message_callback=self.on_message
        )
        log.info("error_detector_started", queue=INPUT_QUEUE)
        try:
            self.ch.start_consuming()
        except KeyboardInterrupt:
            log.info("error_detector_stopping")
            self.ch.stop_consuming()
        finally:
            if self.conn and not self.conn.is_closed:
                self.conn.close()


if __name__ == "__main__":
    ErrorRateDetector().run()