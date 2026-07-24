# layer1/adm/detectors/error_detector.py
"""
Error Rate Surge Detector — Statistical Z-Score (Model 2)

Consumes enriched events from the detect.error queue.
Uses the feature_vector.z_score_error_rate_percent computed by the Feature Store.
Flags an anomaly when |Z| > 3.0 OR error_rate_percent > 10% (step-change catch).

Publishes EVERY result to fusion.results (detected=True or False),
so the Fusion Engine always knows this model processed the event.
"""

import json
import logging
import sys
from pathlib import Path

import pika
import structlog

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ERROR_DETECTOR] %(levelname)s %(message)s"
)
log = structlog.get_logger()

# ── Constants ─────────────────────────────────────────────────────────
Z_SCORE_THRESHOLD = 2.0        # |Z| > 2.0 → anomaly (3-sigma rule)
ERROR_RATE_THRESHOLD = 10.0    # raw error_rate_percent > 10% → immediate flag

INPUT_QUEUE      = "detect.error"
OUTPUT_EXCHANGE  = "fyp.events"
ROUTING_KEY      = "fusion.result"
MODEL_NAME       = "z_score_error_rate"


class ErrorRateDetector:
    """
    Stateless Z-Score detector for error rate surges.
    All state (rolling window, mean, std) is maintained by the Feature Store.
    This detector only reads the pre-computed z_score_error_rate_percent.
    """

    def __init__(self, host: str = "stream-node", port: int = 5672):
        self.host = host
        self.port = port

        params = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host="fyp",
            credentials=pika.PlainCredentials("fyp_user", "fyp_pass_2026"),
            heartbeat=60,
            blocked_connection_timeout=30,
        )
        self.conn = pika.BlockingConnection(params)
        self.ch = self.conn.channel()

        log.info("error_detector_initialised",
                 input_queue=INPUT_QUEUE,
                 output_exchange=OUTPUT_EXCHANGE,
                 routing_key=ROUTING_KEY,
                 z_threshold=Z_SCORE_THRESHOLD,
                 error_rate_threshold=ERROR_RATE_THRESHOLD)

    def detect(self, event: dict) -> dict:
        """
        Core detection logic.

        Args:
            event: enriched event dict with feature_vector

        Returns:
            result dict with detection decision, confidence, and metadata.
        """
        event_id = event.get("event_id", "UNKNOWN")
        fv = event.get("feature_vector", {})

        # Extract the pre-computed Z-score for error_rate_percent
        z_score = fv.get("z_score_error_rate_percent", 0.0)

        # Also check the raw error rate for step-change detection
        error_rate = event.get("metric_values", {}).get("error_rate_percent", 0.0)

        # ── Detection logic ──────────────────────────────────────────
        detected = False
        severity = "N/A"
        reason = ""

        # Primary: Z-score > threshold
        if abs(z_score) > Z_SCORE_THRESHOLD:
            detected = True
            severity = self._severity_from_z(abs(z_score))
            reason = f"Z-score |{z_score:.2f}| > {Z_SCORE_THRESHOLD}"

        # Secondary: raw error rate step-change catch
        elif error_rate > ERROR_RATE_THRESHOLD:
            detected = True
            severity = self._severity_from_rate(error_rate)
            reason = f"error_rate_percent {error_rate:.2f}% > {ERROR_RATE_THRESHOLD}% (step-change)"

        # Compute confidence
        confidence = self._confidence(abs(z_score), error_rate)

        return {
            "event_id": event_id,
            "detected": detected,
            "anomaly_type": "error_rate_surge" if detected else "NORMAL",
            "severity": severity,
            "confidence": confidence,
            "model_name": MODEL_NAME,
            "metadata": {
                "z_score_error_rate_percent": round(z_score, 4),
                "error_rate_percent": round(error_rate, 4),
                "reason": reason,
                "threshold_z": Z_SCORE_THRESHOLD,
                "threshold_rate": ERROR_RATE_THRESHOLD,
            }
        }

    def _severity_from_z(self, abs_z: float) -> str:
        """Map Z-score magnitude to severity."""
        if abs_z >= 5.0:
            return "CRITICAL"
        elif abs_z >= 4.0:
            return "HIGH"
        else:
            return "MEDIUM"

    def _severity_from_rate(self, rate: float) -> str:
        """Map raw error rate to severity."""
        if rate >= 30.0:
            return "CRITICAL"
        elif rate >= 18.0:
            return "HIGH"
        else:
            return "MEDIUM"

    def _confidence(self, abs_z: float, error_rate: float) -> float:
        """
        Compute a confidence score (0.0–1.0).
        Higher Z-score or higher error rate → higher confidence.
        """
        # Z-score based confidence: saturates around 0.95 at Z=6+
        z_conf = min(0.95, abs_z / 6.0)

        # Rate-based confidence: saturates at 0.90 at 30%+
        rate_conf = min(0.90, error_rate / 30.0)

        return round(max(z_conf, rate_conf), 4)

    def on_message(self, ch, method, props, body):
        """RabbitMQ callback for each event."""
        try:
            event = json.loads(body)
        except json.JSONDecodeError as exc:
            log.error("json_parse_error", error=str(exc))
            ch.basic_nack(method.delivery_tag, requeue=False)
            return

        # Run detection
        result = self.detect(event)

        # Always publish to fusion.results
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
                log.info("anomaly_detected",
                         event_id=result["event_id"],
                         severity=result["severity"],
                         confidence=result["confidence"],
                         z_score=result["metadata"]["z_score_error_rate_percent"])
            else:
                log.debug("event_clean",
                          event_id=result["event_id"],
                          z_score=result["metadata"]["z_score_error_rate_percent"])

        except Exception as exc:
            log.error("publish_error", event_id=result["event_id"], error=str(exc))
            ch.basic_nack(method.delivery_tag, requeue=True)
            return

        ch.basic_ack(method.delivery_tag)

    def run(self):
        """Start consuming from detect.error queue."""
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
                log.info("error_detector_connection_closed")


# ── Entry point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    detector = ErrorRateDetector()
    detector.run()