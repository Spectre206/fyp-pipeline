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

import json
import logging
import sys
from pathlib import Path

import pika
import structlog

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [THROUGHPUT_DETECTOR] %(levelname)s %(message)s"
)
log = structlog.get_logger()

# ── Constants ─────────────────────────────────────────────────────────
SILENCE_TIMEOUT    = 30.0    # seconds — matches System Design
DROP_RATIO         = 0.40    # short_ma < long_ma * 0.40 → throughput drop
MIN_BASELINE_MPS   = 5.0     # ignore drops when normal throughput is below this
NEAR_ZERO_MPS      = 2.0     # treat throughput < 2 msgs/sec as effectively silent
RAW_DROP_THRESHOLD = 40.0    # flag if raw throughput < 40 (normal baseline 80–200)

INPUT_QUEUE      = "detect.throughput"
OUTPUT_EXCHANGE  = "fyp.events"
ROUTING_KEY      = "fusion.result"
MODEL_NAME       = "moving_average_throughput"


class ThroughputDetector:
    """
    Stateless throughput drop / silent crash detector.
    All rolling window state is maintained by the Feature Store.
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

        log.info("throughput_detector_initialised",
                 input_queue=INPUT_QUEUE,
                 output_exchange=OUTPUT_EXCHANGE,
                 silence_timeout=SILENCE_TIMEOUT,
                 drop_ratio=DROP_RATIO,
                 min_baseline_mps=MIN_BASELINE_MPS,
                 near_zero_mps=NEAR_ZERO_MPS,
                 raw_drop_threshold=RAW_DROP_THRESHOLD)

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

        # Extract the pre‑computed features
        short_ma = fv.get("short_ma_messages_per_second", 0.0)
        long_ma  = fv.get("long_ma_messages_per_second", 0.0)
        silence  = fv.get("silence_duration_s", 0.0)

        # Raw metric value — used to check if this component handles messages
        raw_mps = event.get("metric_values", {}).get("messages_per_second", None)

        # ── Detection logic ──────────────────────────────────────────
        detected = False
        severity = "N/A"
        reason = ""

        # Priority 1: Silent crash — only for components that handle messages
        # AND are currently showing near‑zero throughput.
        if (
            raw_mps is not None
            and raw_mps < NEAR_ZERO_MPS
            and silence >= SILENCE_TIMEOUT
        ):
            detected = True
            severity = "CRITICAL"
            reason = (
                f"Silent crash — throughput {raw_mps:.1f} < {NEAR_ZERO_MPS} "
                f"for {silence:.0f}s (threshold: {SILENCE_TIMEOUT}s)"
            )

        # Priority 2: Throughput drop — only when baseline is meaningful.
        elif (
            long_ma >= MIN_BASELINE_MPS
            and short_ma < long_ma * DROP_RATIO
        ):
            detected = True
            drop_pct = (1 - short_ma / long_ma) * 100
            severity = self._severity_from_drop(drop_pct)
            reason = (
                f"Throughput drop — short_ma={short_ma:.1f}, "
                f"long_ma={long_ma:.1f}, drop={drop_pct:.1f}% "
                f"(threshold: {(1-DROP_RATIO)*100:.0f}%)"
            )

        # Priority 3: Raw throughput below normal baseline —
        # catches events the rolling window may lag on.
        elif raw_mps is not None and raw_mps < RAW_DROP_THRESHOLD:
            detected = True
            severity = self._severity_from_raw(raw_mps)
            reason = (
                f"Raw throughput {raw_mps:.1f} < {RAW_DROP_THRESHOLD} "
                f"(normal baseline 80–200)"
            )

        # Compute confidence
        confidence = self._confidence(short_ma, long_ma, silence, raw_mps)

        return {
            "event_id": event_id,
            "detected": detected,
            "anomaly_type": "throughput_drop" if detected else "NORMAL",
            "severity": severity,
            "confidence": confidence,
            "model_name": MODEL_NAME,
            "metadata": {
                "short_ma_messages_per_second": round(short_ma, 4),
                "long_ma_messages_per_second": round(long_ma, 4),
                "silence_duration_s": round(silence, 4),
                "raw_messages_per_second": (
                    round(raw_mps, 4) if raw_mps is not None else None
                ),
                "reason": reason,
                "threshold_silence_s": SILENCE_TIMEOUT,
                "threshold_drop_ratio": DROP_RATIO,
                "min_baseline_mps": MIN_BASELINE_MPS,
                "near_zero_mps": NEAR_ZERO_MPS,
                "raw_drop_threshold": RAW_DROP_THRESHOLD,
            }
        }

    def _severity_from_drop(self, drop_pct: float) -> str:
        """Map throughput drop percentage to severity."""
        if drop_pct >= 80:
            return "CRITICAL"
        elif drop_pct >= 60:
            return "HIGH"
        else:
            return "MEDIUM"

    def _severity_from_raw(self, mps: float) -> str:
        """Map raw throughput value to severity."""
        if mps < NEAR_ZERO_MPS:
            return "CRITICAL"
        elif mps < 20.0:
            return "HIGH"
        else:
            return "MEDIUM"

    def _confidence(
        self,
        short_ma: float,
        long_ma: float,
        silence: float,
        raw_mps: float | None,
    ) -> float:
        """
        Compute confidence (0.0–1.0).
        Higher silence duration, larger drop, or lower raw throughput
        → higher confidence.
        """
        # Silence‑based: saturates at 0.95 at 60s+
        silence_conf = (
            min(0.95, silence / 60.0) if raw_mps is not None else 0.0
        )

        # Drop‑based: saturates at 0.95 at 80%+ drop
        if long_ma > 0:
            drop_pct = max(0, 1 - short_ma / long_ma)
            drop_conf = min(0.95, drop_pct / 0.80)
        else:
            drop_conf = 0.0

        # Raw‑based: saturates at 0.90 when throughput is near zero
        if raw_mps is not None and raw_mps < RAW_DROP_THRESHOLD:
            raw_conf = min(0.90, 1.0 - raw_mps / RAW_DROP_THRESHOLD)
        else:
            raw_conf = 0.0

        return round(max(silence_conf, drop_conf, raw_conf), 4)

    def on_message(self, ch, method, props, body):
        """RabbitMQ callback for each event."""
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

            # Save local copy for evaluation
            with open(
                "/home/asim/fyp-pipeline/layer1/adm/throughput_results.jsonl", "a"
            ) as f:
                f.write(json.dumps(result) + "\n")

            if result["detected"]:
                log.info(
                    "anomaly_detected",
                    event_id=result["event_id"],
                    severity=result["severity"],
                    confidence=result["confidence"],
                    reason=result["metadata"]["reason"],
                )
            else:
                log.debug("event_clean", event_id=result["event_id"])

        except Exception as exc:
            log.error("publish_error", event_id=result["event_id"], error=str(exc))
            ch.basic_nack(method.delivery_tag, requeue=True)
            return

        ch.basic_ack(method.delivery_tag)

    def run(self):
        """Start consuming from detect.throughput queue."""
        self.ch.basic_qos(prefetch_count=1)
        self.ch.basic_consume(
            queue=INPUT_QUEUE,
            on_message_callback=self.on_message
        )
        log.info("throughput_detector_started", queue=INPUT_QUEUE)
        try:
            self.ch.start_consuming()
        except KeyboardInterrupt:
            log.info("throughput_detector_stopping")
            self.ch.stop_consuming()
        finally:
            if self.conn and not self.conn.is_closed:
                self.conn.close()
                log.info("throughput_detector_connection_closed")


# ── Entry point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    detector = ThroughputDetector()
    detector.run()