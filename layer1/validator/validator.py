"""
Pydantic Validator — Schema Enforcement Gate

This module defines the PipelineEvent Pydantic model and the validation logic
that every incoming raw event must pass before entering the Feature Store.

Validation covers: required field presence, correct data types, enum membership
for anomaly_type / severity / node, at least one entry in metric_values, and
a non-empty affected_component string.

Events that pass validation are returned as PipelineEvent objects and forwarded
to the Feature Store. Events that fail validation are caught, re-packaged as
schema_drift anomaly events with severity determined by violation type
(missing field -> MEDIUM, type mutation -> HIGH), and published directly to the
anomaly.detected RabbitMQ queue -- bypassing the Feature Store entirely since
they cannot be safely featurised.
"""
# layer1/validator/validator.py
#
# Pydantic Validator -- v1.4 (config-driven, hostname-based, no Prometheus)
#
# Consumes raw events from fyp.events exchange (routing key: event.raw).
# Valid events -> published to fyp.events with routing key: validated.event
# Invalid events -> SchemaDriftRouter -> anomaly.detected directly
#
# Run: python validator.py
#
# CHANGELOG v1.3 -> v1.4:
#   - Prometheus metrics removed entirely. Project decision: only the
#     Fusion Engine is scraped from Layer 1 -- no other Layer 1 component
#     (Validator, Feature Store, ADM detectors) exposes or is scraped for
#     metrics. This also removes the start_http_server() call and the
#     import-time port-binding issue that came with it.
#
# CHANGELOG v1.2 -> v1.3 (for reference):
#   - Loads validator_config.json (was previously fully hardcoded, no config
#     file existed at all) -- matches the pattern established in SEG v1.3.
#   - RabbitMQ host defaults to the "stream-node" hostname, not a hardcoded
#     IP.
#   - SchemaDriftRouter receives the exchange/routing key from config
#     instead of hardcoding them a second time in a separate file.

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Literal

import pika
import structlog
from pydantic import BaseModel, Field, field_validator, ValidationError

from schema_drift_router import SchemaDriftRouter

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [VALIDATOR] %(levelname)s %(message)s"
)
log = structlog.get_logger()

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "validator_config.json"

FALLBACK_RABBITMQ = {
    "host": "stream-node", "port": 5672, "virtual_host": "fyp",
    "username": "fyp_user", "password": "fyp_pass_2026",
    "exchange": "fyp.events", "input_queue": "raw.events",
    "valid_routing_key": "event.valid",
    "schema_drift_routing_key": "anomaly.schema_drift",
}


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"validator_config.json not found at {path}. "
            f"The Validator requires this file for RabbitMQ connection "
            f"settings. Pass a different path via "
            f"ValidatorConsumer(config_path=...) if needed."
        )
    with open(path) as f:
        cfg = json.load(f)
    log.info(f"Loaded config from {path}")
    return cfg


# ══════════════════════════════════════════════════════════════════════
#  PYDANTIC EVENT SCHEMA
#  This is the single source of truth for the event schema on Node 1.
#  All fields must match the SEG output schema exactly.
#
#  NOTE on "node": includes "external" in addition to the 3 physical
#  cluster nodes. SEG itself never generates "external" (its node list
#  comes from seg_config.json's 3-entry "nodes" array) -- this 4th value
#  is a deliberately wider validation contract than what SEG currently
#  produces, reserved for events that might one day arrive from outside
#  the 3-node cluster. Not a bug or inconsistency with SEG; it's the
#  Validator's schema contract being intentionally more permissive than
#  its current only producer.
# ══════════════════════════════════════════════════════════════════════

class PipelineEvent(BaseModel):
    event_id: str

    timestamp: datetime

    anomaly_type: Literal[
        "cpu_memory_spike",
        "error_rate_surge",
        "throughput_drop",
        "auth_failure_flood",
        "schema_drift",
        "NORMAL"
    ]

    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL", "N/A"]

    affected_component: str

    node: Literal[
        "stream-node",
        "ai-brain-node",
        "gateway-node",
        "external"
    ]

    metric_values: Dict[str, float] = Field(..., min_length=1)

    context: Optional[str] = ""

    # ── Field-level validators ─────────────────────────────────────────

    @field_validator("metric_values")
    @classmethod
    def at_least_one_metric(cls, v: dict) -> dict:
        if not v:
            raise ValueError("metric_values must contain at least one entry")
        return v

    @field_validator("event_id")
    @classmethod
    def valid_uuid(cls, v: str) -> str:
        import uuid as _uuid
        try:
            _uuid.UUID(v)
        except ValueError:
            raise ValueError(f"event_id must be a valid UUID v4, got: {v!r}")
        return v

    @field_validator("affected_component")
    @classmethod
    def non_empty_component(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("affected_component must be a non-empty string")
        return v.strip()


# ══════════════════════════════════════════════════════════════════════
#  VALIDATOR CONSUMER
#  Consumes from the raw.events queue (bound to fyp.events/event.raw).
#  One message at a time (prefetch controlled by config).
# ══════════════════════════════════════════════════════════════════════

class ValidatorConsumer:

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH):
        self._seen_ids: set = set()   # session-scoped dedup store

        self.config = load_config(Path(config_path))
        rmq = self.config.get("rabbitmq", FALLBACK_RABBITMQ)

        self.host = rmq.get("host", FALLBACK_RABBITMQ["host"])
        self.port = rmq.get("port", FALLBACK_RABBITMQ["port"])
        self.vhost = rmq.get("virtual_host", FALLBACK_RABBITMQ["virtual_host"])
        self.username = rmq.get("username", FALLBACK_RABBITMQ["username"])
        self.password = rmq.get("password", FALLBACK_RABBITMQ["password"])
        self.exchange = rmq.get("exchange", FALLBACK_RABBITMQ["exchange"])
        self.INPUT_QUEUE = rmq.get("input_queue", FALLBACK_RABBITMQ["input_queue"])
        self.valid_routing_key = rmq.get("valid_routing_key", FALLBACK_RABBITMQ["valid_routing_key"])
        self.schema_drift_routing_key = rmq.get(
            "schema_drift_routing_key", FALLBACK_RABBITMQ["schema_drift_routing_key"]
        )
        self.prefetch_count = self.config.get("prefetch_count", 100)

        # RabbitMQ connection -- hostname, not a hardcoded IP.
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

        # Declare raw.events queue (binds to fyp.events/event.raw).
        # This queue receives events published by the SEG in replay mode.
        self.ch.queue_declare(
            queue=self.INPUT_QUEUE,
            durable=True,
            arguments={"x-dead-letter-exchange": "fyp.dlx",
                       "x-dead-letter-routing-key": "dead"}
        )
        self.ch.queue_bind(
            queue=self.INPUT_QUEUE,
            exchange=self.exchange,
            routing_key="event.raw"
        )

        # Schema drift router (publishes to anomaly.detected via fyp.events)
        self.router = SchemaDriftRouter(
            self.ch,
            exchange=self.exchange,
            routing_key=self.schema_drift_routing_key,
        )

        log.info("validator_initialised",
                 host=self.host,
                 input_queue=self.INPUT_QUEUE)

    # ── Main message handler ──────────────────────────────────────────

    def on_message(self, ch, method, props, body):
        """
        Called for each raw event message.
        1. Parse JSON
        2. Check for duplicate event_id
        3. Validate with Pydantic
        4. Route: valid -> validated.event | invalid -> anomaly.detected
        """
        try:
            raw = json.loads(body)
        except json.JSONDecodeError as exc:
            log.error("json_parse_error", error=str(exc))
            ch.basic_nack(method.delivery_tag, requeue=False)
            return

        event_id = raw.get("event_id", "MISSING")

        dedup_flag = event_id in self._seen_ids
        if dedup_flag:
            log.warning("duplicate_event_id", event_id=event_id)
        self._seen_ids.add(event_id)

        try:
            event = PipelineEvent(**raw)

        except ValidationError as exc:
            error_type = self._classify_error(exc, raw)

            log.warning(
                "validation_failed",
                event_id=event_id,
                error_type=error_type,
                errors=exc.error_count()
            )

            self.router.route(raw, exc, error_type)
            ch.basic_ack(method.delivery_tag)
            return

        except Exception as exc:
            log.error("unexpected_validation_error",
                      event_id=event_id, error=str(exc))
            ch.basic_nack(method.delivery_tag, requeue=False)
            return

        enriched = event.model_dump(mode="json")
        enriched["dedup_flag"] = dedup_flag
        enriched["validated_at"] = datetime.now(timezone.utc).isoformat()

        self.ch.basic_publish(
            exchange=self.exchange,
            routing_key=self.valid_routing_key,
            body=json.dumps(enriched).encode("utf-8"),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json"
            )
        )

        log.info(
            "event_validated",
            event_id=event_id,
            anomaly_type=enriched["anomaly_type"],
            dedup_flag=dedup_flag
        )
        ch.basic_ack(method.delivery_tag)

    # ── Error classifier ──────────────────────────────────────────────

    def _classify_error(self, exc: ValidationError, raw: dict) -> str:
        """
        Classifies the Pydantic error into one of three categories:
          MISSING_FIELD    -> severity MEDIUM
          TYPE_MUTATION    -> severity HIGH
          SCHEMA_VIOLATION -> severity MEDIUM (enum violations, value errors)

        NOTE: missing-field is checked first, so a compound violation (a
        field missing AND another field's type mutated in the same event)
        is classified as MISSING_FIELD/MEDIUM even though it also contains
        a HIGH-severity issue. SEG's synthetic corpus never generates
        compound violations (each schema_drift event is exactly one
        subtype), so this doesn't affect the 1,950-event evaluation --
        flagged here in case real/malformed production-like input is ever
        fed through this path.
        """
        required_fields = {
            "event_id", "timestamp", "anomaly_type",
            "severity", "affected_component", "node", "metric_values"
        }

        for field in required_fields:
            if field not in raw:
                return "MISSING_FIELD"

        errors = exc.errors()
        if not errors:
            return "UNKNOWN"

        for err in errors:
            etype = err.get("type", "")

            if "missing" in etype:
                return "MISSING_FIELD"

            if "type" in etype:
                return "TYPE_MUTATION"

            if "literal" in etype or "value" in etype:
                return "SCHEMA_VIOLATION"

        return "SCHEMA_VIOLATION"

    # ── Consume loop ──────────────────────────────────────────────────

    def run(self):
        self.ch.basic_qos(prefetch_count=self.prefetch_count)

        self.ch.basic_consume(
            queue=self.INPUT_QUEUE,
            on_message_callback=self.on_message
        )
        log.info("validator_started",
                 queue=self.INPUT_QUEUE,
                 waiting_for_messages=True)
        try:
            self.ch.start_consuming()
        except KeyboardInterrupt:
            log.info("validator_stopping")
            self.ch.stop_consuming()
        finally:
            if self.conn and not self.conn.is_closed:
                self.conn.close()
                log.info("validator_connection_closed")


# ── Entry point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    ValidatorConsumer().run()