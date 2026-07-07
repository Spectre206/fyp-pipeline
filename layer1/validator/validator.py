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
(missing field → MEDIUM, type mutation → HIGH), and published directly to the
anomaly.detected RabbitMQ queue — bypassing the Feature Store entirely since
they cannot be safely featurised.
"""
# layer1/validator/validator.py
#
# Pydantic Validator — v1.2
#
# Consumes raw events from fyp.events exchange (routing key: event.raw).
# Valid events → published to fyp.events with routing key: validated.event
# Invalid events → SchemaDriftRouter → anomaly.detected directly
#
# Exposes Prometheus metrics on port 8002.
# Run: python validator.py

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Dict, Optional, Literal

import pika
import structlog
from pydantic import BaseModel, Field, field_validator, ValidationError
from prometheus_client import Counter, start_http_server

from schema_drift_router import SchemaDriftRouter

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [VALIDATOR] %(levelname)s %(message)s"
)
log = structlog.get_logger()

# ── Prometheus metrics (port 8002) ────────────────────────────────────
start_http_server(8002)

VAL_PASSED = Counter(
    "fyp_validation_passed_total",
    "Events that passed Pydantic validation"
)
VAL_ERRORS = Counter(
    "fyp_validation_errors_total",
    "Events that failed Pydantic validation",
    ["error_type"]
)
VAL_DUPLICATES = Counter(
    "fyp_validation_duplicates_total",
    "Duplicate event_ids detected within session"
)


# ══════════════════════════════════════════════════════════════════════
#  PYDANTIC EVENT SCHEMA
#  This is the single source of truth for the event schema on Node 1.
#  All fields must match the SEG output schema exactly.
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
#  One message at a time (prefetch_count=1).
# ══════════════════════════════════════════════════════════════════════

class ValidatorConsumer:

    # Queue this consumer reads from
    INPUT_QUEUE = "raw.events"

    def __init__(self):
        self._seen_ids: set = set()   # session-scoped dedup store

        # ── CORRECTED RabbitMQ connection ──────────────────────────────
        params = pika.ConnectionParameters(
            host="192.168.18.101",          # Explicit node IP
            virtual_host="fyp",             # MUST specify the vhost
            credentials=pika.PlainCredentials("fyp_user", "fyp_pass_2026"),
            heartbeat=60,
            blocked_connection_timeout=30,
        )
        self.conn = pika.BlockingConnection(params)
        self.ch   = self.conn.channel()

        # ── Declare raw.events queue (binds to fyp.events/event.raw) ─
        # This queue receives events published by the SEG in replay mode.
        self.ch.queue_declare(
            queue="raw.events",
            durable=True,
            arguments={"x-dead-letter-exchange": "fyp.dlx",
                       "x-dead-letter-routing-key": "dead"}
        )
        self.ch.queue_bind(
            queue="raw.events",
            exchange="fyp.events",
            routing_key="event.raw"
        )

        # ── Schema drift router (publishes to anomaly.detected) ───────
        self.router = SchemaDriftRouter(self.ch)

        log.info("validator_initialised",
                 input_queue=self.INPUT_QUEUE,
                 metrics_port=8002)

    # ── Main message handler ──────────────────────────────────────────

    def on_message(self, ch, method, props, body):
        """
        Called for each raw event message.
        1. Parse JSON
        2. Check for duplicate event_id
        3. Validate with Pydantic
        4. Route: valid → validated.event | invalid → anomaly.detected
        """
        # Step 1: Parse JSON
        try:
            raw = json.loads(body)
        except json.JSONDecodeError as exc:
            log.error("json_parse_error", error=str(exc))
            VAL_ERRORS.labels(error_type="JSON_PARSE").inc()
            ch.basic_nack(method.delivery_tag, requeue=False)
            return

        event_id = raw.get("event_id", "MISSING")

        # Step 2: Duplicate detection (session-scoped)
        dedup_flag = event_id in self._seen_ids
        if dedup_flag:
            log.warning("duplicate_event_id", event_id=event_id)
            VAL_DUPLICATES.inc()
        self._seen_ids.add(event_id)

        # Step 3: Pydantic validation
        try:
            event = PipelineEvent(**raw)

        except ValidationError as exc:
            # Classify the error type for severity assignment
            error_type = self._classify_error(exc, raw)
            VAL_ERRORS.labels(error_type=error_type).inc()

            log.warning(
                "validation_failed",
                event_id=event_id,
                error_type=error_type,
                errors=exc.error_count()
            )

            # Route directly to anomaly.detected — bypass Feature Store and Fusion Engine
            self.router.route(raw, exc, error_type)
            ch.basic_ack(method.delivery_tag)
            return

        except Exception as exc:
            # Unexpected error — nack and route to dead letters
            log.error("unexpected_validation_error",
                      event_id=event_id, error=str(exc))
            VAL_ERRORS.labels(error_type="UNEXPECTED").inc()
            ch.basic_nack(method.delivery_tag, requeue=False)
            return

        # Step 4: Valid event — enrich and publish to Feature Store
        VAL_PASSED.inc()

        enriched = event.model_dump(mode="json")
        enriched["dedup_flag"]   = dedup_flag
        enriched["validated_at"] = datetime.now(timezone.utc).isoformat()

        self.ch.basic_publish(
            exchange="fyp.events",
            routing_key="event.valid",
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
          MISSING_FIELD    → severity MEDIUM
          TYPE_MUTATION    → severity HIGH
          SCHEMA_VIOLATION → severity MEDIUM (enum violations, value errors)

        Classification is based on the error 'type' field from Pydantic v2.
        """
        required_fields = {
            "event_id", "timestamp", "anomaly_type",
            "severity", "affected_component", "node", "metric_values"
        }

        # Check for missing required fields first
        for field in required_fields:
            if field not in raw:
                return "MISSING_FIELD"

        # Inspect Pydantic error types
        errors = exc.errors()
        if not errors:
            return "UNKNOWN"

        for err in errors:
            etype = err.get("type", "")

            # Pydantic v2 missing field error types
            if "missing" in etype:
                return "MISSING_FIELD"

            # Type errors: int_type, float_type, str_type, dict_type, etc.
            if "type" in etype:
                return "TYPE_MUTATION"

            # Value errors: literal_error, enum violation
            if "literal" in etype or "value" in etype:
                return "SCHEMA_VIOLATION"

        return "SCHEMA_VIOLATION"   # default fallback

    # ── Consume loop ──────────────────────────────────────────────────

    def run(self):
        # ── OPTIMIZED Prefetch Count for High Throughput ──────────────
        self.ch.basic_qos(prefetch_count=100) 
        
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
