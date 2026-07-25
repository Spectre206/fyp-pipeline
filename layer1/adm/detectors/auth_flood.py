# layer1/adm/detectors/auth_detector.py
"""
Auth Failure Flood Detector — Rate-Gate + Random Forest (Model 4)

Consumes enriched events from the detect.auth queue.
Two-stage detection:
  1. Rate-gate: auth_failures_per_min > 20 → immediate flag
  2. Random Forest: loads trained model (auth_rf.pkl), maps event metrics
     to KDD99 features, and provides secondary confirmation for flagged events.

Always publishes a result to fusion.results (detected=True or False).
"""

import json
import logging
import os
from pathlib import Path

import numpy as np
import pika
import structlog

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AUTH_DETECTOR] %(levelname)s %(message)s"
)
log = structlog.get_logger()

RATE_THRESHOLD = 20.0
INPUT_QUEUE    = "detect.auth"
OUTPUT_EXCHANGE = "fyp.events"
ROUTING_KEY    = "fusion.result"
MODEL_NAME     = "rate_gate_auth_rf"
MODEL_PATH     = os.path.join(os.path.dirname(__file__), "../models/auth_rf.pkl")

# KDD99 feature names the RF expects (in order)
RF_FEATURES = [
    "duration", "src_bytes", "dst_bytes",
    "num_failed_logins", "logged_in", "num_compromised",
    "root_shell", "su_attempted", "num_root",
    "count", "srv_count", "serror_rate", "rerror_rate",
    "same_srv_rate", "dst_host_count", "dst_host_srv_count",
    "dst_host_serror_rate", "dst_host_rerror_rate",
]


class AuthDetector:
    """Two-stage auth failure flood detector."""

    def __init__(self, host: str = "stream-node", port: int = 5672):
        params = pika.ConnectionParameters(
            host=host, port=port, virtual_host="fyp",
            credentials=pika.PlainCredentials("fyp_user", "fyp_pass_2026"),
            heartbeat=60, blocked_connection_timeout=30,
        )
        self.conn = pika.BlockingConnection(params)
        self.ch = self.conn.channel()

        # Load Random Forest model
        self.rf_model = None
        if os.path.exists(MODEL_PATH):
            import joblib
            self.rf_model = joblib.load(MODEL_PATH)
            log.info("rf_model_loaded", path=MODEL_PATH)
        else:
            log.warning("rf_model_not_found", path=MODEL_PATH,
                        note="running rate-gate only")

        log.info("auth_detector_initialised",
                 rate_threshold=RATE_THRESHOLD,
                 rf_available=self.rf_model is not None)

    def _map_to_rf_features(self, event: dict) -> np.ndarray:
        """
        Map event metrics to the 18 KDD99 features the RF expects.
        Unavailable features default to 0.
        """
        mv = event.get("metric_values", {})
        if not isinstance(mv, dict):
            return np.zeros(len(RF_FEATURES))

        # Direct mappings where possible
        feature_map = {
            "src_bytes": mv.get("src_bytes", 0),
            "serror_rate": mv.get("error_rate_percent", 0) / 100.0,  # normalise
            "rerror_rate": 0.0,
            "num_failed_logins": mv.get("auth_failures_per_min", 0),
        }

        # Build feature array in the order RF expects
        features = []
        for name in RF_FEATURES:
            features.append(float(feature_map.get(name, 0.0)))

        return np.array(features).reshape(1, -1)

    def detect(self, event: dict) -> dict:
        event_id = event.get("event_id", "UNKNOWN")
        fv = event.get("feature_vector", {})
        auth_rate = fv.get("auth_failures_per_min", 0.0)

        detected = auth_rate > RATE_THRESHOLD
        severity = self._severity(auth_rate) if detected else "N/A"

        # Base confidence from rate-gate
        confidence = min(0.95, auth_rate / 100.0) if detected else 0.0

        # RF confirmation (if model available and event flagged)
        rf_vote = None
        if detected and self.rf_model is not None:
            try:
                features = self._map_to_rf_features(event)
                rf_pred = self.rf_model.predict(features)[0]
                rf_proba = self.rf_model.predict_proba(features)[0]
                rf_vote = int(rf_pred)

                if rf_pred == 1:
                    # RF agrees — boost confidence
                    confidence = min(0.98, confidence + rf_proba[1] * 0.3)
                else:
                    # RF disagrees — lower confidence but don't override rate-gate
                    confidence = max(0.30, confidence - 0.20)
            except Exception as exc:
                log.warning("rf_inference_error", error=str(exc))

        return {
            "event_id": event_id,
            "detected": detected,
            "anomaly_type": "auth_failure_flood" if detected else "NORMAL",
            "severity": severity,
            "confidence": round(confidence, 4),
            "model_name": MODEL_NAME,
            "metadata": {
                "auth_failures_per_min": round(auth_rate, 4),
                "rate_threshold": RATE_THRESHOLD,
                "rf_vote": rf_vote,
                "reason": (
                    f"auth_failures_per_min {auth_rate:.1f} > {RATE_THRESHOLD}"
                    if detected else ""
                ),
            }
        }

    def _severity(self, rate: float) -> str:
        if rate >= 100:
            return "CRITICAL"
        elif rate >= 40:
            return "HIGH"
        return "MEDIUM"

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
                         severity=result["severity"], rate=result["metadata"]["auth_failures_per_min"],
                         rf_vote=result["metadata"]["rf_vote"])
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