# layer1/fusion_engine/fusion_engine.py
"""
Fusion Engine — Multi-Detector Signal Correlation (v1.7)

Consumes individual detector results from fusion.results,
groups them by event_id within a configurable correlation window,
and publishes a single fused decision to anomaly.detected.

Detectors:
    - error_rate
    - throughput_drop
    - auth_flood
    - cpu_spike
    - schema_drift

v1.7 CHANGELOG:
  - Keeps primary correlation window at 3 seconds.
  - Uses configurable late-arrival recovery window.
  - Recommended recovery window for evaluation: 0.75 seconds.
  - Fast Path remains enabled but does not prematurely finalize events.
  - Adds separate Fast Path trigger counter:
      `fyp_fusion_fast_path_triggered_total`
  - Existing:
      `fyp_fusion_fast_path_total`
    remains unchanged for dashboard compatibility.
  - Fast Path trigger is counted only once per event.
  - Keeps correlation timing instrumentation.
  - Keeps detector-count-at-finalization instrumentation.
  - Keeps ingestion_time propagation unchanged.
  - Keeps min_confidence_to_publish unchanged.
  - Keeps processed_event_ids duplicate protection.
  - Uses RabbitMQ basic_consume() for continuous consumption.
  - No artificial polling sleep.

v1.6 CHANGELOG:
  - Keeps the primary correlation window at 3 seconds.
  - Adds a small late-arrival recovery window after the primary
    correlation window.
  - Events with all five detector results are fused immediately.
  - Incomplete events are allowed an additional recovery period.
  - Fast Path remains enabled but does not immediately finalize events.
  - Adds correlation timing instrumentation.

v1.5 CHANGELOG:
  - FIX correlation timeout to use Fusion-side monotonic time.
  - ingestion_time is preserved as event metadata but is not compared
    directly with current wall clock for the correlation deadline.
  - Uses RabbitMQ basic_consume() for continuous consumption.
  - Fast Path remains enabled but does not immediately finalize events.
  - Duplicate detector results are ignored.

v1.2 CHANGELOG:
  - FIX duplicate processing: added processed_event_ids set to ensure
    each event is fused exactly once.
  - Late-arriving detector results after final fusion are acknowledged
    and ignored.

All-normal events are suppressed.

Compound event:
    >=2 unique detectors returned detected=True.

Fast Path:
    A CRITICAL result from a model whose configured weight meets the
    Fast Path threshold marks the event as Fast Path, but the event
    remains eligible for correlation.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pika
import structlog
from prometheus_client import Counter, Histogram, start_http_server


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [FUSION] %(levelname)s %(message)s"
)
log = structlog.get_logger()

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "fusion_config.json"


# ── Prometheus metrics (port 8003) ────────────────────────────────────

start_http_server(8003)

FUSION_SUPPRESSED = Counter(
    "fyp_fusion_suppressed_total",
    "Events where all detectors returned normal (suppressed)"
)

FUSION_PUBLISHED = Counter(
    "fyp_fusion_published_total",
    "Events published to anomaly.detected"
)

FUSION_COMPOUND = Counter(
    "fyp_fusion_compound_total",
    "Compound incidents (≥2 detectors flagged)"
)

FUSION_FASTPATH = Counter(
    "fyp_fusion_fast_path_total",
    "Events fast-pathed (CRITICAL with high-weight model)"
)

# NEW:
# Counts events where Fast Path was actually triggered by a qualifying
# CRITICAL/high-weight detector result.
#
# This metric is deliberately separate from FUSION_FASTPATH.
# FUSION_FASTPATH remains unchanged for existing dashboard compatibility.
FUSION_FASTPATH_TRIGGERED = Counter(
    "fyp_fusion_fast_path_triggered_total",
    "Events where a CRITICAL high-weight detector triggered Fast Path"
)

FUSION_LATENCY = Histogram(
    "fyp_fusion_latency_seconds",
    "Fusion decision computation latency in seconds",
    buckets=(
        0.0001,
        0.0005,
        0.001,
        0.002,
        0.005,
        0.01,
        0.02,
        0.05,
        0.1,
        0.2,
        0.5,
        1.0,
        2.0,
        3.0,
    )
)

FUSION_ERRORS = Counter(
    "fyp_fusion_errors_total",
    "Fusion processing errors"
)

# Correlation timing instrumentation.
FUSION_CORRELATION_WAIT = Histogram(
    "fyp_fusion_correlation_wait_seconds",
    "Time an event remained in correlation before finalization",
    buckets=(
        0.01,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        1.5,
        2.0,
        2.5,
        3.0,
        3.1,
        3.2,
        3.3,
        3.4,
        3.5,
        3.6,
        3.7,
        3.8,
        4.0,
    )
)

FUSION_LATE_RECOVERY = Counter(
    "fyp_fusion_late_recovery_total",
    "Events finalized during the late-arrival recovery period"
)

FUSION_DETECTORS_RECEIVED = Histogram(
    "fyp_fusion_detectors_received",
    "Number of unique detectors received at final fusion",
    buckets=(1, 2, 3, 4, 5)
)


# ── Expected detector models ──────────────────────────────────────────

EXPECTED_DETECTORS = {
    "z_score_error_rate",
    "moving_average_throughput",
    "rate_gate_auth_rf",
    "z_score_cpu_memory",
    "psi_detector",
}


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"fusion_config.json not found at {path}"
        )

    with open(path) as f:
        cfg = json.load(f)

    log.info(
        "config_loaded",
        path=str(path)
    )

    return cfg


def parse_ingestion_time(value) -> Optional[float]:
    """
    Parse ingestion_time for validation purposes.

    ingestion_time is preserved as event metadata.

    It is NOT used as the Fusion timeout clock.
    """

    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        pass

    try:
        normalized = value.replace(
            "Z",
            "+00:00"
        )

        dt = datetime.fromisoformat(
            normalized
        )

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.timestamp()

    except (ValueError, TypeError):
        return None


class FusionEngine:
    """Correlates detector results and produces fused anomaly decisions."""

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH):
        self.config = load_config(config_path)
        rmq = self.config["rabbitmq"]

        self.host = rmq["host"]
        self.port = rmq["port"]
        self.vhost = rmq["virtual_host"]
        self.username = rmq["username"]
        self.password = rmq["password"]
        self.input_queue = rmq["input_queue"]
        self.output_exchange = rmq["output_exchange"]
        self.output_routing_key = rmq["output_routing_key"]

        # ─────────────────────────────────────────────────────────────
        # Primary correlation window.
        #
        # Keep this at 3 seconds.
        # ─────────────────────────────────────────────────────────────

        self.window_s = float(
            self.config["correlation_window_s"]
        )

        # ─────────────────────────────────────────────────────────────
        # Late-arrival recovery window.
        #
        # Recommended:
        #     0.75 seconds
        #
        # Effective maximum:
        #     3.0 + 0.75 = 3.75 seconds
        #
        # The primary correlation window is still 3 seconds.
        # Recovery is only used for incomplete events.
        # ─────────────────────────────────────────────────────────────

        self.recovery_window_s = float(
            self.config.get(
                "correlation_recovery_window_s",
                0.75
            )
        )

        self.min_confidence = float(
            self.config["min_confidence_to_publish"]
        )

        self.fast_path_enabled = bool(
            self.config["fast_path_critical"]
        )

        self.fast_path_weight_threshold = float(
            self.config["fast_path_model_weight_threshold"]
        )

        self.model_weights = self.config["model_weights"]

        # ─────────────────────────────────────────────────────────────
        # Pending events:
        #
        # event_id → {
        #     "results": [],
        #     "methods": [],
        #     "detectors_seen": set(),
        #     "first_seen_monotonic": float,
        #     "first_ingestion_time": str,
        #     "fast_path_triggered": bool,
        #     "recovery_active": bool
        # }
        # ─────────────────────────────────────────────────────────────

        self.pending: Dict[str, dict] = {}

        # ─────────────────────────────────────────────────────────────
        # Duplicate protection.
        #
        # An event is added here only after final fusion.
        # ─────────────────────────────────────────────────────────────

        self.processed_event_ids = set()

        # RabbitMQ connection
        params = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.vhost,
            credentials=pika.PlainCredentials(
                self.username,
                self.password
            ),
            heartbeat=60,
            blocked_connection_timeout=30,
        )

        self.conn = pika.BlockingConnection(params)
        self.ch = self.conn.channel()

        # High-throughput RabbitMQ consumer.
        self.ch.basic_qos(
            prefetch_count=100
        )

        log.info(
            "fusion_engine_initialised",
            input_queue=self.input_queue,
            correlation_window_s=self.window_s,
            recovery_window_s=self.recovery_window_s,
            min_confidence=self.min_confidence,
            fast_path=self.fast_path_enabled,
            expected_detectors=len(EXPECTED_DETECTORS)
        )

    def run(self):
        """Main loop: consume from fusion.results, correlate, publish."""

        log.info(
            "fusion_engine_started",
            correlation_window_s=self.window_s,
            recovery_window_s=self.recovery_window_s
        )

        self.ch.basic_consume(
            queue=self.input_queue,
            on_message_callback=self.on_message,
            auto_ack=False
        )

        try:

            while True:

                # Process RabbitMQ messages continuously.
                self.ch.connection.process_data_events(
                    time_limit=0.05
                )

                # Check correlation/recovery deadlines.
                self._check_expired_events()

        except KeyboardInterrupt:

            log.info(
                "fusion_engine_stopping"
            )

            try:
                self.ch.stop_consuming()
            except Exception:
                pass

        finally:

            if self.conn and not self.conn.is_closed:

                self.conn.close()

                log.info(
                    "fusion_engine_connection_closed"
                )

    def on_message(
        self,
        ch,
        method,
        props,
        body
    ):
        """RabbitMQ callback for detector results."""

        try:

            result = json.loads(
                body
            )

        except json.JSONDecodeError as exc:

            FUSION_ERRORS.inc()

            log.error(
                "json_parse_error",
                error=str(exc)
            )

            ch.basic_nack(
                method.delivery_tag,
                requeue=False
            )

            return

        try:

            self._handle_message(
                method,
                result
            )

        except Exception as exc:

            FUSION_ERRORS.inc()

            log.error(
                "fusion_message_error",
                event_id=result.get(
                    "event_id"
                ),
                error=str(exc)
            )

            ch.basic_nack(
                method.delivery_tag,
                requeue=False
            )

    def _handle_message(
        self,
        method,
        result: dict
    ):
        """Process a single detector result."""

        event_id = result.get(
            "event_id"
        )

        if not event_id:

            log.error(
                "missing_event_id"
            )

            self.ch.basic_ack(
                method.delivery_tag
            )

            return

        # ─────────────────────────────────────────────────────────────
        # If event has already been finalized, ignore the late result.
        # ─────────────────────────────────────────────────────────────

        if event_id in self.processed_event_ids:

            log.debug(
                "late_result_ignored",
                event_id=event_id
            )

            self.ch.basic_ack(
                method.delivery_tag
            )

            return

        model_name = result.get(
            "model_name"
        )

        # ─────────────────────────────────────────────────────────────
        # Validate detector identity.
        # ─────────────────────────────────────────────────────────────

        if model_name not in EXPECTED_DETECTORS:

            log.warning(
                "unknown_detector_model",
                event_id=event_id,
                model_name=model_name
            )

        # ─────────────────────────────────────────────────────────────
        # Create pending event.
        # ─────────────────────────────────────────────────────────────

        if event_id not in self.pending:

            self.pending[event_id] = {
                "results": [],
                "methods": [],
                "detectors_seen": set(),

                # Fusion-side monotonic timer.
                "first_seen_monotonic": time.monotonic(),

                # Preserve original event-time information.
                "first_ingestion_time": result.get(
                    "ingestion_time"
                ),

                "fast_path_triggered": False,
                "recovery_active": False,
            }

        entry = self.pending[event_id]

        # ─────────────────────────────────────────────────────────────
        # Prevent same detector from being counted twice.
        # ─────────────────────────────────────────────────────────────

        if model_name in entry["detectors_seen"]:

            log.debug(
                "duplicate_detector_result",
                event_id=event_id,
                detector=model_name
            )

            self.ch.basic_ack(
                method.delivery_tag
            )

            return

        # Validate ingestion_time.
        if result.get("ingestion_time"):

            parsed_ingestion = parse_ingestion_time(
                result.get(
                    "ingestion_time"
                )
            )

            if parsed_ingestion is None:

                log.warning(
                    "invalid_ingestion_time",
                    event_id=event_id,
                    ingestion_time=result.get(
                        "ingestion_time"
                    )
                )

        # ─────────────────────────────────────────────────────────────
        # Store detector result.
        # ─────────────────────────────────────────────────────────────

        entry["results"].append(
            result
        )

        entry["methods"].append(
            method
        )

        entry["detectors_seen"].add(
            model_name
        )

        # ─────────────────────────────────────────────────────────────
        # FAST PATH
        #
        # Fast Path is recorded but does not finalize the event.
        #
        # NEW:
        # FUSION_FASTPATH_TRIGGERED counts the event at the moment the
        # Fast Path condition is first detected.
        # ─────────────────────────────────────────────────────────────

        if self._is_fast_path(
            result
        ):

            # IMPORTANT:
            # Count only the False → True transition.
            #
            # This guarantees one trigger increment per event.
            if not entry["fast_path_triggered"]:

                entry["fast_path_triggered"] = True

                # NEW:
                # Count that Fast Path was actually triggered, regardless
                # of whether the event is ultimately published or suppressed.
                FUSION_FASTPATH_TRIGGERED.inc()

                log.info(
                    "fast_path_triggered",
                    event_id=event_id,
                    detector=model_name,
                    detectors_received=len(
                        entry["detectors_seen"]
                    )
                )

        # ─────────────────────────────────────────────────────────────
        # All five detectors received.
        #
        # Finalize immediately.
        # ─────────────────────────────────────────────────────────────

        if EXPECTED_DETECTORS.issubset(
            entry["detectors_seen"]
        ):

            self._fuse_and_cleanup(
                event_id,
                fast_path=entry["fast_path_triggered"],
                recovery=False
            )

        # ACK after safely storing the result in pending.
        try:

            self.ch.basic_ack(
                method.delivery_tag
            )

        except Exception as exc:

            log.error(
                "ack_error",
                event_id=event_id,
                error=str(exc)
            )

    def _check_expired_events(self):
        """
        Check normal correlation deadline and late recovery deadline.

        Timeline:

            0.0s ---------------- 3.0s ---------------- 3.75s
                  normal window        recovery window
        """

        if not self.pending:
            return

        now = time.monotonic()

        for event_id, entry in list(
            self.pending.items()
        ):

            elapsed = (
                now
                - entry["first_seen_monotonic"]
            )

            # ─────────────────────────────────────────────────────────
            # Phase 1: primary 3-second correlation window.
            # ─────────────────────────────────────────────────────────

            if (
                elapsed >= self.window_s
                and not entry["recovery_active"]
            ):

                # If all detectors arrived by the boundary,
                # finalize immediately.
                if EXPECTED_DETECTORS.issubset(
                    entry["detectors_seen"]
                ):

                    self._fuse_and_cleanup(
                        event_id,
                        fast_path=entry["fast_path_triggered"],
                        recovery=False
                    )

                    continue

                # Start recovery period.
                entry["recovery_active"] = True

                log.debug(
                    "correlation_recovery_started",
                    event_id=event_id,
                    detectors_received=len(
                        entry["detectors_seen"]
                    ),
                    elapsed_seconds=round(
                        elapsed,
                        4
                    ),
                    recovery_window_s=self.recovery_window_s
                )

            # ─────────────────────────────────────────────────────────
            # Phase 2: late-arrival recovery.
            # ─────────────────────────────────────────────────────────

            if entry["recovery_active"]:

                recovery_deadline = (
                    self.window_s
                    + self.recovery_window_s
                )

                if elapsed >= recovery_deadline:

                    self._fuse_and_cleanup(
                        event_id,
                        fast_path=entry["fast_path_triggered"],
                        recovery=True
                    )

    def _is_fast_path(
        self,
        result: dict
    ) -> bool:
        """Return True if this result triggers Fast Path."""

        if not self.fast_path_enabled:
            return False

        if result.get(
            "severity"
        ) != "CRITICAL":

            return False

        model = result.get(
            "model_name",
            ""
        )

        weight = self.model_weights.get(
            model,
            0.0
        )

        return (
            weight
            >= self.fast_path_weight_threshold
        )

    def _fuse_and_cleanup(
        self,
        event_id: str,
        fast_path: bool = False,
        recovery: bool = False
    ):
        """
        Correlate all received results for event_id,
        publish decision and finalize the event.
        """

        entry = self.pending.pop(
            event_id,
            None
        )

        if entry is None:
            return

        results = entry["results"]

        # ─────────────────────────────────────────────────────────────
        # Correlation timing instrumentation.
        # ─────────────────────────────────────────────────────────────

        correlation_wait = (
            time.monotonic()
            - entry["first_seen_monotonic"]
        )

        detectors_received = len(
            entry["detectors_seen"]
        )

        FUSION_CORRELATION_WAIT.observe(
            correlation_wait
        )

        FUSION_DETECTORS_RECEIVED.observe(
            detectors_received
        )

        if recovery:
            FUSION_LATE_RECOVERY.inc()

        # ─────────────────────────────────────────────────────────────
        # Finalization point.
        # ─────────────────────────────────────────────────────────────

        self.processed_event_ids.add(
            event_id
        )

        start = time.time()

        try:

            fused = self._fuse(
                event_id,
                results,
                fast_path
            )

            if fused is not None:

                # Correlation diagnostics stored in local evaluation file.
                fused["correlation_wait_ms"] = round(
                    correlation_wait * 1000.0,
                    3
                )

                fused["detectors_received"] = (
                    detectors_received
                )

                # NEW:
                # Record exactly which detector models participated in the final
                #correlation decision.
                fused["detectors_seen"] = sorted(
                    entry["detectors_seen"]
                    )

                # NEW:
                # Record which expected detectors did not arrive before finalization.
                fused["missing_detectors"] = sorted(
                    EXPECTED_DETECTORS - entry["detectors_seen"]
                    )
                
                fused["correlation_recovery"] = (
                    recovery
                )

                self._publish(
                    fused
                )

                FUSION_PUBLISHED.inc()

                if (
                    fused["fusion_type"]
                    == "compound"
                ):

                    FUSION_COMPOUND.inc()

                # Existing Fast Path metric remains unchanged.
                #
                # It counts Fast Path events that ultimately produce
                # a published fused event.
                if fast_path:

                    FUSION_FASTPATH.inc()

            else:

                FUSION_SUPPRESSED.inc()

                log.debug(
                    "event_suppressed",
                    event_id=event_id,
                    detectors_received=detectors_received,
                    correlation_wait_ms=round(
                        correlation_wait * 1000.0,
                        3
                    ),
                    recovery=recovery
                )

        except Exception as exc:

            FUSION_ERRORS.inc()

            log.error(
                "fusion_error",
                event_id=event_id,
                error=str(exc)
            )

        finally:

            FUSION_LATENCY.observe(
                time.time() - start
            )

    def _fuse(
        self,
        event_id: str,
        results: List[dict],
        fast_path: bool = False
    ) -> Optional[dict]:
        """
        Combine detector results into a single fused decision.

        Returns None if suppressed.
        """

        anomalies = [
            r
            for r in results
            if r.get("detected")
        ]

        # ─────────────────────────────────────────────────────────────
        # All detectors returned normal.
        # ─────────────────────────────────────────────────────────────

        if not anomalies:

            return None

        contributing = []

        for r in anomalies:

            contributing.append({
                "model_name": r.get(
                    "model_name"
                ),
                "severity": r.get(
                    "severity"
                ),
                "confidence": r.get(
                    "confidence"
                ),
                "detected": True,
            })

        # ─────────────────────────────────────────────────────────────
        # >=2 detector anomalies = compound.
        # ─────────────────────────────────────────────────────────────

        fusion_type = (
            "compound"
            if len(anomalies) >= 2
            else "single"
        )

        # ─────────────────────────────────────────────────────────────
        # Weighted confidence.
        # ─────────────────────────────────────────────────────────────

        max_conf = 0.0

        for r in anomalies:

            model = r.get(
                "model_name",
                ""
            )

            weight = self.model_weights.get(
                model,
                0.5
            )

            weighted_conf = (
                float(
                    r.get(
                        "confidence",
                        0.0
                    )
                )
                * weight
            )

            if weighted_conf > max_conf:

                max_conf = weighted_conf

        fused_confidence = round(
            max_conf,
            4
        )

        # ─────────────────────────────────────────────────────────────
        # Highest severity.
        # ─────────────────────────────────────────────────────────────

        severity_rank = {
            "CRITICAL": 3,
            "HIGH": 2,
            "MEDIUM": 1,
            "LOW": 0,
            "N/A": 0,
        }

        fused_severity = max(
            anomalies,
            key=lambda r: severity_rank.get(
                r.get(
                    "severity",
                    "MEDIUM"
                ),
                0
            )
        )["severity"]

        # ─────────────────────────────────────────────────────────────
        # Existing confidence threshold remains unchanged.
        # ─────────────────────────────────────────────────────────────

        if (
            fusion_type == "single"
            and fused_confidence
            < self.min_confidence
        ):

            return None

        # ─────────────────────────────────────────────────────────────
        # Preserve original event timestamp.
        # ─────────────────────────────────────────────────────────────

        original_ts = next(
            (
                r.get("timestamp")
                for r in results
                if r.get("timestamp")
            ),
            None
        )

        # ─────────────────────────────────────────────────────────────
        # Preserve original event ingestion_time.
        # ─────────────────────────────────────────────────────────────

        original_ingestion_time = next(
            (
                r.get("ingestion_time")
                for r in results
                if r.get("ingestion_time")
            ),
            None
        )

        fused_event = {
            "event_id": event_id,
            "timestamp": original_ts,
            "ingestion_time": original_ingestion_time,
            "fused_severity": fused_severity,
            "fused_confidence": fused_confidence,
            "fusion_type": fusion_type,
            "contributing_models": contributing,
            "fused_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "note": (
                "fast_path"
                if fast_path
                else "standard_window"
            )
        }

        return fused_event

    def _publish(
        self,
        fused_event: dict
    ):
        """Publish fused decision to anomaly.detected."""

        self.ch.basic_publish(
            exchange=self.output_exchange,
            routing_key=self.output_routing_key,
            body=json.dumps(
                fused_event,
                default=str
            ).encode("utf-8"),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json"
            )
        )

        log.info(
            "fused_event_published",
            event_id=fused_event["event_id"],
            severity=fused_event["fused_severity"],
            confidence=fused_event["fused_confidence"],
            type=fused_event["fusion_type"]
        )

        # Local copy for evaluation.
        results_path = (
            Path(__file__).parent
            / "fusion_results.jsonl"
        )

        with open(
            results_path,
            "a"
        ) as f:

            f.write(
                json.dumps(
                    fused_event,
                    default=str
                ) + "\n"
            )


if __name__ == "__main__":
    FusionEngine().run()