# layer1/adm/detectors/cpu_spike.py
"""
CPU/Memory Spike Detector — Statistical Z‑Score (Model 1, v1.1)

Consumes enriched events from the detect.cpu queue.
Uses pre‑computed Z‑scores from the Feature Store (z_score_cpu_percent,
z_score_mem_percent) — same proven pattern as the error rate detector.

Detection logic:
  1. Z‑score check: if |z_score_cpu| > 2.0 OR |z_score_mem| > 2.0 → flag
  2. Raw threshold catch: if cpu > 70% OR mem > 70% → flag immediately
     (catches spikes the rolling window may initially lag on)
  3. Severity based on Z‑score magnitude or raw percentage.

Note: An Isolation Forest model was trained on NAB data (train_cpu_model.py)
and saved to models/isolation_forest_cpu.pkl. It is not used in this version
but remains available for a future hybrid confidence‑adjustment stage.

Always publishes a result to fusion.results (detected=True or False).
"""

"""
CPU/Memory Spike Detector — Z-Score (Model 1) with Prometheus Metrics
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
    format="%(asctime)s [CPU_DETECTOR] %(levelname)s %(message)s"
)
log = structlog.get_logger()

DETECTOR_NAME = "cpu_spike"
PROM_PORT = 8007
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

Z_THRESHOLD        = 2.0
CPU_RAW_THRESHOLD  = 70.0
MEM_RAW_THRESHOLD  = 70.0

INPUT_QUEUE     = "detect.cpu"
OUTPUT_EXCHANGE = "fyp.events"
ROUTING_KEY     = "fusion.result"
MODEL_NAME      = "z_score_cpu_memory"


class CPUDetector:
    def __init__(self, host: str = "stream-node", port: int = 5672):
        params = pika.ConnectionParameters(
            host=host, port=port, virtual_host="fyp",
            credentials=pika.PlainCredentials("fyp_user", "fyp_pass_2026"),
            heartbeat=60, blocked_connection_timeout=30,
        )
        self.conn = pika.BlockingConnection(params)
        self.ch = self.conn.channel()
        log.info("cpu_detector_initialised", z_threshold=Z_THRESHOLD)

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
                    "detected": False,
                    "anomaly_type": "NORMAL",
                    "severity": "N/A",
                    "confidence": 0.0,
                    "model_name": MODEL_NAME,
                    "metadata": {"reason": "no valid metrics"}
                }

            z_cpu = abs(fv.get("z_score_cpu_percent", 0.0))
            z_mem = abs(fv.get("z_score_mem_percent", 0.0))
            z_max = max(z_cpu, z_mem)
            cpu_raw = raw_mv.get("cpu_percent", 0.0)
            mem_raw = raw_mv.get("mem_percent", 0.0)

            detected = False
            severity = "N/A"
            reason = ""

            if z_max > Z_THRESHOLD:
                detected = True
                severity = self._severity_from_z(z_max)
                reason = f"Z-score |{z_max:.2f}| > {Z_THRESHOLD}"
            elif cpu_raw > CPU_RAW_THRESHOLD:
                detected = True
                severity = self._severity_from_raw(cpu_raw)
                reason = f"Raw CPU {cpu_raw:.1f}% > {CPU_RAW_THRESHOLD}%"
            elif mem_raw > MEM_RAW_THRESHOLD:
                detected = True
                severity = self._severity_from_raw(mem_raw)
                reason = f"Raw MEM {mem_raw:.1f}% > {MEM_RAW_THRESHOLD}%"

            confidence = self._confidence(z_max, cpu_raw, mem_raw) if detected else 0.0

            if detected:
                ANOMALY_COUNT.labels(
                    detector=DETECTOR_NAME, anomaly_type=anomaly_type
                ).inc()

            return {
                "event_id": event_id,
                "timestamp": event.get("timestamp"),
                "detected": detected,
                "anomaly_type": "cpu_memory_spike" if detected else "NORMAL",
                "severity": severity,
                "confidence": round(confidence, 4),
                "model_name": MODEL_NAME,
                "metadata": {
                    "z_score_cpu_percent": round(z_cpu, 4),
                    "z_score_mem_percent": round(z_mem, 4),
                    "z_max": round(z_max, 4),
                    "cpu_raw": round(cpu_raw, 2),
                    "mem_raw": round(mem_raw, 2),
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
        elif abs_z >= 3.0: return "HIGH"
        return "MEDIUM"

    def _severity_from_raw(self, value: float) -> str:
        if value >= 95.0: return "CRITICAL"
        elif value >= 85.0: return "HIGH"
        return "MEDIUM"

    def _confidence(self, z_max: float, cpu_raw: float, mem_raw: float) -> float:
        z_conf = min(0.95, z_max / 6.0)
        raw_conf = min(0.90, max(cpu_raw, mem_raw) / 100.0)
        return round(max(z_conf, raw_conf), 4)

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
            with open("/home/asim/fyp-pipeline/layer1/adm/cpu_results.jsonl", "a") as f:
                f.write(json.dumps(result) + "\n")

            if result["detected"]:
                log.info("anomaly_detected", event_id=result["event_id"],
                         severity=result["severity"], z_max=result["metadata"]["z_max"])
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
        log.info("cpu_detector_started", queue=INPUT_QUEUE)
        try:
            self.ch.start_consuming()
        except KeyboardInterrupt:
            log.info("cpu_detector_stopping")
            self.ch.stop_consuming()
        finally:
            if self.conn and not self.conn.is_closed:
                self.conn.close()


if __name__ == "__main__":
    CPUDetector().run()