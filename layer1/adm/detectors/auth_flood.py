"""Statistical Auth Failure Flood Detector.

Consumes enriched events from ``detect.auth`` and makes a deterministic decision
from three Layer 1 signals: the current authentication-failure rate, its rolling
60-second mean, and its event-to-event rate of change.  No trained model or
external model artifact participates in the runtime path.
"""

import json
import logging
import time
import pika
import structlog
from prometheus_client import Counter, Histogram, start_http_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AUTH_DETECTOR] %(levelname)s %(message)s"
)
log = structlog.get_logger()

DETECTOR_NAME = "auth_flood"
PROM_PORT = 8006
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

RATE_THRESHOLD = 20.0
RATE_CHANGE_THRESHOLD = 15.0
INPUT_QUEUE    = "detect.auth"
OUTPUT_EXCHANGE = "fyp.events"
ROUTING_KEY    = "fusion.result"
MODEL_NAME     = "statistical_auth_rate"


class AuthDetector:
    def __init__(self, host: str = "stream-node", port: int = 5672):
        params = pika.ConnectionParameters(
            host=host, port=port, virtual_host="fyp",
            credentials=pika.PlainCredentials("fyp_user", "fyp_pass_2026"),
            heartbeat=60, blocked_connection_timeout=30,
        )
        self.conn = pika.BlockingConnection(params)
        self.ch = self.conn.channel()

        log.info(
            "auth_detector_initialised",
            rate_threshold=RATE_THRESHOLD,
            rate_change_threshold=RATE_CHANGE_THRESHOLD,
        )

    def detect(self, event: dict) -> dict:
        start = time.time()
        event_id = event.get("event_id", "UNKNOWN")
        anomaly_type = event.get("anomaly_type", "UNKNOWN")
        EVAL_COUNT.labels(detector=DETECTOR_NAME, anomaly_type=anomaly_type).inc()

        try:
            fv = event.get("feature_vector", {})
            metrics = event.get("metric_values", {})
            if not isinstance(fv, dict):
                fv = {}
            if not isinstance(metrics, dict):
                metrics = {}

            # The current raw rate catches an abrupt flood before a rolling
            # statistic can be diluted by normal observations.  The rolling
            # mean and rate-of-change retain sensitivity to sustained floods.
            current_rate = float(metrics.get("auth_failures_per_min", 0.0))
            rolling_rate = float(fv.get("auth_failures_per_min", 0.0))
            rate_change = float(fv.get("rate_of_change_auth_failures_per_min", 0.0))
            detected = (
                current_rate > RATE_THRESHOLD
                or rolling_rate > RATE_THRESHOLD
                or rate_change >= RATE_CHANGE_THRESHOLD
            )
            signal_rate = max(current_rate, rolling_rate)
            severity = self._severity(signal_rate) if detected else "N/A"
            confidence = self._confidence(current_rate, rolling_rate, rate_change)

            reasons = []
            if current_rate > RATE_THRESHOLD:
                reasons.append(f"current_rate {current_rate:.1f} > {RATE_THRESHOLD}")
            if rolling_rate > RATE_THRESHOLD:
                reasons.append(f"rolling_rate {rolling_rate:.1f} > {RATE_THRESHOLD}")
            if rate_change >= RATE_CHANGE_THRESHOLD:
                reasons.append(
                    f"rate_change {rate_change:.1f} >= {RATE_CHANGE_THRESHOLD}"
                )

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
                "anomaly_type": "auth_failure_flood" if detected else "NORMAL",
                "severity": severity,
                "confidence": round(confidence, 4),
                "model_name": MODEL_NAME,
                "metadata": {
                    "current_auth_failures_per_min": round(current_rate, 4),
                    "rolling_auth_failures_per_min": round(rolling_rate, 4),
                    "auth_failure_rate_change": round(rate_change, 4),
                    "rate_threshold": RATE_THRESHOLD,
                    "rate_change_threshold": RATE_CHANGE_THRESHOLD,
                    "reason": "; ".join(reasons),
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

    def _severity(self, rate: float) -> str:
        if rate >= 100: return "CRITICAL"
        elif rate >= 40: return "HIGH"
        return "MEDIUM"

    def _confidence(self, current_rate: float, rolling_rate: float, rate_change: float) -> float:
        if (
            current_rate <= RATE_THRESHOLD
            and rolling_rate <= RATE_THRESHOLD
            and rate_change < RATE_CHANGE_THRESHOLD
        ):
            return 0.0
        current_conf = min(0.95, current_rate / 100.0)
        rolling_conf = min(0.90, rolling_rate / 100.0)
        change_conf = min(0.85, rate_change / 50.0)
        return round(max(current_conf, rolling_conf, change_conf), 4)

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
            with open("/home/asim/fyp-pipeline/layer1/adm/auth_results.jsonl", "a") as f:
                f.write(json.dumps(result) + "\n")

            if result["detected"]:
                log.info("anomaly_detected", event_id=result["event_id"],
                         severity=result["severity"],
                         rate=result["metadata"]["current_auth_failures_per_min"])
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
        log.info("auth_detector_started", queue=INPUT_QUEUE)
        try:
            self.ch.start_consuming()
        except KeyboardInterrupt:
            log.info("auth_detector_stopping")
            self.ch.stop_consuming()
        finally:
            if self.conn and not self.conn.is_closed:
                self.conn.close()


if __name__ == "__main__":
    AuthDetector().run()
