# layer1/fusion_engine/fusion_engine.py
"""
Fusion Engine — Multi‑Detector Signal Correlation (v1.0)

Consumes individual detector results from fusion.results,
groups them by event_id within a configurable correlation window,
and publishes a single fused decision to anomaly.detected.

All‑normal events (all detectors return detected=False) are suppressed.

Prometheus metrics exposed on port 8003 (the only Layer 1 component scraped).
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pika
import structlog
from prometheus_client import Counter, start_http_server

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
    "Events fast‑pathed (CRITICAL with high‑weight model)"
)


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"fusion_config.json not found at {path}")
    with open(path) as f:
        cfg = json.load(f)
    log.info("config_loaded", path=str(path))
    return cfg


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

        self.window_s = float(self.config["correlation_window_s"])
        self.min_confidence = float(self.config["min_confidence_to_publish"])
        self.fast_path_enabled = bool(self.config["fast_path_critical"])
        self.fast_path_weight_threshold = float(
            self.config["fast_path_model_weight_threshold"]
        )
        self.model_weights = self.config["model_weights"]

        # Pending events: event_id → dict of results, methods, first_seen
        self.pending: Dict[str, dict] = {}

        # RabbitMQ connection
        params = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.vhost,
            credentials=pika.PlainCredentials(self.username, self.password),
            heartbeat=60,
            blocked_connection_timeout=30,
        )
        self.conn = pika.BlockingConnection(params)
        self.ch = self.conn.channel()

        log.info("fusion_engine_initialised",
                 input_queue=self.input_queue,
                 correlation_window_s=self.window_s,
                 min_confidence=self.min_confidence,
                 fast_path=self.fast_path_enabled)

    def run(self):
        """Main loop: consume from fusion.results, correlate, publish."""
        log.info("fusion_engine_started")
        try:
            while True:
                # Pull one message with a short timeout
                method, props, body = self.ch.basic_get(
                    queue=self.input_queue, auto_ack=False
                )
                if body is not None:
                    self._handle_message(method, props, body)

                # Check for expired correlation windows
                now = datetime.now(timezone.utc)
                expired = []
                for event_id, entry in self.pending.items():
                    if (now - entry["first_seen"]).total_seconds() >= self.window_s:
                        expired.append(event_id)
                    if len(entry["results"]) == 5:
                        if event_id not in expired:
                            expired.append(event_id)

                for event_id in expired:
                    self._fuse_and_cleanup(event_id)

                time.sleep(0.1)

        except KeyboardInterrupt:
            log.info("fusion_engine_stopping")
        finally:
            if self.conn and not self.conn.is_closed:
                self.conn.close()
                log.info("fusion_engine_connection_closed")

    def _handle_message(self, method, props, body):
        """Process a single detector result."""
        try:
            result = json.loads(body)
        except json.JSONDecodeError:
            log.error("json_parse_error", body=body[:100])
            self.ch.basic_nack(method.delivery_tag, requeue=False)
            return

        event_id = result["event_id"]
        if event_id not in self.pending:
            self.pending[event_id] = {
                "results": [],
                "methods": [],
                "first_seen": datetime.now(timezone.utc),
                "fast_path_triggered": False,
            }

        entry = self.pending[event_id]
        entry["results"].append(result)
        entry["methods"].append(method)

        # Fast‑path check
        if self._is_fast_path(result):
            self._fuse_and_cleanup(event_id, fast_path=True)

    def _is_fast_path(self, result: dict) -> bool:
        """Return True if this result triggers fast‑path processing."""
        if not self.fast_path_enabled:
            return False
        if result.get("severity") != "CRITICAL":
            return False
        model = result.get("model_name", "")
        weight = self.model_weights.get(model, 0.0)
        return weight >= self.fast_path_weight_threshold

    def _fuse_and_cleanup(self, event_id: str, fast_path: bool = False):
        """Correlate all received results for event_id, publish decision, ack messages."""
        entry = self.pending.pop(event_id, None)
        if entry is None:
            return

        results = entry["results"]
        methods = entry["methods"]
        fused = self._fuse(event_id, results, fast_path)

        if fused is not None:
            self._publish(fused)
            FUSION_PUBLISHED.inc()
            if fused["fusion_type"] == "compound":
                FUSION_COMPOUND.inc()
            if fast_path:
                FUSION_FASTPATH.inc()
        else:
            FUSION_SUPPRESSED.inc()

        for method in methods:
            self.ch.basic_ack(method.delivery_tag)

    def _fuse(self, event_id: str, results: List[dict], fast_path: bool = False) -> Optional[dict]:
        """Combine detector results into a single fused decision. Returns None if suppressed."""
        anomalies = [r for r in results if r.get("detected")]
        if not anomalies:
            return None

        contributing = []
        for r in anomalies:
            contributing.append({
                "model_name": r.get("model_name"),
                "severity": r.get("severity"),
                "confidence": r.get("confidence"),
                "detected": True,
            })

        fusion_type = "compound" if len(anomalies) >= 2 else "single"

        max_conf = 0.0
        for r in anomalies:
            model = r.get("model_name", "")
            weight = self.model_weights.get(model, 0.5)
            weighted_conf = float(r.get("confidence", 0.0)) * weight
            if weighted_conf > max_conf:
                max_conf = weighted_conf
        fused_confidence = round(max_conf, 4)

        severity_rank = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1}
        fused_severity = max(
            anomalies, key=lambda r: severity_rank.get(r.get("severity", "MEDIUM"), 0)
        )["severity"]

        if fusion_type == "single" and fused_confidence < self.min_confidence:
            return None

        fused_event = {
            "event_id": event_id,
            "fused_severity": fused_severity,
            "fused_confidence": fused_confidence,
            "fusion_type": fusion_type,
            "contributing_models": contributing,
            "fused_at": datetime.now(timezone.utc).isoformat(),
            "note": "fast_path" if fast_path else "standard_window"
        }
        return fused_event

    def _publish(self, fused_event: dict):
        """Publish fused decision to anomaly.detected."""
        self.ch.basic_publish(
            exchange=self.output_exchange,
            routing_key=self.output_routing_key,
            body=json.dumps(fused_event, default=str).encode("utf-8"),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json"
            )
        )
        log.info("fused_event_published",
                 event_id=fused_event["event_id"],
                 severity=fused_event["fused_severity"],
                 confidence=fused_event["fused_confidence"],
                 type=fused_event["fusion_type"])

        # Local copy for evaluation
        results_path = Path(__file__).parent / "fusion_results.jsonl"
        with open(results_path, "a") as f:
            f.write(json.dumps(fused_event, default=str) + "\n")


if __name__ == "__main__":
    FusionEngine().run()