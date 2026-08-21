# layer1/adm/detectors/throughput_drop.py
"""
Throughput Drop Detector — Moving Average Deviation (Model 3)

Consumes enriched events from the detect.throughput queue.
Uses pre‑computed features from the Feature Store plus raw metric values.

Detection logic (three independent checks):
  1. SILENT CRASH: if raw_mps < 2.0 AND silence_duration_s >= 30 AND the
     component handles messages → CRITICAL.
  2. THROUGHPUT DROP: if long_ma >= 5.0 (meaningful baseline) AND
     short_ma < long_ma * 0.40 → severity based on drop percentage.
  3. RAW THRESHOLD: if raw_mps < 40.0 (normal baseline is 80–200) →
     direct catch for events the rolling window may lag on.

Always publishes a result to fusion.results (detected=True or False).
"""
"""
Throughput Drop Detector — Moving Average Deviation (Model 3) with Prometheus Metrics
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
    format="%(asctime)s [THROUGHPUT_DETECTOR] %(levelname)s %(message)s"
)
log = structlog.get_logger()

DETECTOR_NAME = "throughput_drop"
PROM_PORT = 8005
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

SILENCE_TIMEOUT    = 30.0
DROP_RATIO         = 0.40
MIN_BASELINE_MPS   = 5.0
NEAR_ZERO_MPS      = 2.0
RAW_DROP_THRESHOLD = 40.0

INPUT_QUEUE      = "detect.throughput"
OUTPUT_EXCHANGE  = "fyp.events"
ROUTING_KEY      = "fusion.result"
MODEL_NAME       = "moving_average_throughput"


class ThroughputDetector:
    def __init__(self, host: str = "stream-node", port: int = 5672):
        params = pika.ConnectionParameters(
            host=host, port=port, virtual_host="fyp",
            credentials=pika.PlainCredentials("fyp_user", "fyp_pass_2026"),
            heartbeat=60, blocked_connection_timeout=30,
        )
        self.conn = pika.BlockingConnection(params)
        self.ch = self.conn.channel()
        log.info("throughput_detector_initialised",
                 silence_timeout=SILENCE_TIMEOUT,
                 drop_ratio=DROP_RATIO)

    def detect(self, event: dict) -> dict:
        start = time.time()
        event_id = event.get("event_id", "UNKNOWN")
        anomaly_type = event.get("anomaly_type", "UNKNOWN")
        EVAL_COUNT.labels(detector=DETECTOR_NAME, anomaly_type=anomaly_type).inc()

        try:
            fv = event.get("feature_vector", {})
            short_ma = fv.get("short_ma_messages_per_second", 0.0)
            long_ma  = fv.get("long_ma_messages_per_second", 0.0)
            silence  = fv.get("silence_duration_s", 0.0)
            raw_mps  = event.get("metric_values", {}).get("messages_per_second", None)

            detected = False
            severity = "N/A"
            reason = ""

            if raw_mps is not None and raw_mps < NEAR_ZERO_MPS and silence >= SILENCE_TIMEOUT:
                detected = True
                severity = "CRITICAL"
                reason = f"Silent crash — throughput {raw_mps:.1f} < {NEAR_ZERO_MPS}"
            elif long_ma >= MIN_BASELINE_MPS and short_ma < long_ma * DROP_RATIO:
                detected = True
                drop_pct = (1 - short_ma / long_ma) * 100
                severity = self._severity_from_drop(drop_pct)
                reason = f"Throughput drop — drop={drop_pct:.1f}%"
            elif raw_mps is not None and raw_mps < RAW_DROP_THRESHOLD:
                detected = True
                severity = self._severity_from_raw(raw_mps)
                reason = f"Raw throughput {raw_mps:.1f} < {RAW_DROP_THRESHOLD}"

            confidence = self._confidence(short_ma, long_ma, silence, raw_mps)

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
                "anomaly_type": "throughput_drop" if detected else "NORMAL",
                "severity": severity,
                "confidence": confidence,
                "model_name": MODEL_NAME,
                "metadata": {
                    "short_ma_messages_per_second": round(short_ma, 4),
                    "long_ma_messages_per_second": round(long_ma, 4),
                    "silence_duration_s": round(silence, 4),
                    "raw_messages_per_second": round(raw_mps, 4) if raw_mps is not None else None,
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

    def _severity_from_drop(self, drop_pct: float) -> str:
        if drop_pct >= 80: return "CRITICAL"
        elif drop_pct >= 60: return "HIGH"
        return "MEDIUM"

    def _severity_from_raw(self, mps: float) -> str:
        if mps < 2.0: return "CRITICAL"
        elif mps < 20.0: return "HIGH"
        return "MEDIUM"

    def _confidence(self, short_ma, long_ma, silence, raw_mps) -> float:
        silence_conf = min(0.95, silence / 60.0) if raw_mps is not None else 0.0
        if long_ma > 0:
            drop_pct = max(0, 1 - short_ma / long_ma)
            drop_conf = min(0.95, drop_pct / 0.80)
        else:
            drop_conf = 0.0
        raw_conf = min(0.90, 1.0 - raw_mps / RAW_DROP_THRESHOLD) if raw_mps is not None and raw_mps < RAW_DROP_THRESHOLD else 0.0
        return round(max(silence_conf, drop_conf, raw_conf), 4)

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
                properties=pika.BasicProperties(delivery_mode=2, content_type="application/json")
            )
            with open("/home/asim/fyp-pipeline/layer1/adm/throughput_results.jsonl", "a") as f:
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
        self.ch.basic_consume(queue=INPUT_QUEUE, on_message_callback=self.on_message)
        log.info("throughput_detector_started", queue=INPUT_QUEUE)
        try:
            self.ch.start_consuming()
        except KeyboardInterrupt:
            log.info("throughput_detector_stopping")
            self.ch.stop_consuming()
        finally:
            if self.conn and not self.conn.is_closed:
                self.conn.close()


if __name__ == "__main__":
    ThroughputDetector().run()