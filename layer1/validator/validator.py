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
"""
Pydantic Validator — Schema Enforcement Gate with Prometheus Metrics

v1.5: Prometheus metrics added on port 8002:
  - fyp_validator_events_total
  - fyp_validator_valid_total
  - fyp_validator_schema_violations_total{reason}
  - fyp_validator_errors_total
  - fyp_validator_latency_seconds
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Literal

import pika
import structlog
from pydantic import BaseModel, Field, field_validator, ValidationError
from prometheus_client import Counter, Histogram, start_http_server

from schema_drift_router import SchemaDriftRouter

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [VALIDATOR] %(levelname)s %(message)s"
)
log = structlog.get_logger()

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "validator_config.json"

# ── Prometheus metrics (port 8002) ────────────────────────────────────
start_http_server(8002)

VAL_EVENTS = Counter(
    "fyp_validator_events_total",
    "Total events received by validator"
)
VAL_VALID = Counter(
    "fyp_validator_valid_total",
    "Events that passed Pydantic validation"
)
VAL_VIOLATIONS = Counter(
    "fyp_validator_schema_violations_total",
    "Events that failed Pydantic validation",
    ["reason"]
)
VAL_ERRORS = Counter(
    "fyp_validator_errors_total",
    "Unexpected errors or JSON parse errors"
)
VAL_LATENCY = Histogram(
    "fyp_validator_latency_seconds",
    "Validation latency in seconds",
    buckets=(0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1)
)


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


class PipelineEvent(BaseModel):
    event_id: str
    timestamp: datetime
    anomaly_type: Literal[
        "cpu_memory_spike", "error_rate_surge", "throughput_drop",
        "auth_failure_flood", "schema_drift", "NORMAL"
    ]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL", "N/A"]
    affected_component: str
    node: Literal["stream-node", "ai-brain-node", "gateway-node", "external"]
    metric_values: Dict[str, float] = Field(..., min_length=1)
    context: Optional[str] = ""

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


class ValidatorConsumer:

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH):
        self._seen_ids: set = set()

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

        self.router = SchemaDriftRouter(
            self.ch,
            exchange=self.exchange,
            routing_key=self.schema_drift_routing_key,
        )

        log.info("validator_initialised",
                 host=self.host,
                 input_queue=self.INPUT_QUEUE)

    def on_message(self, ch, method, props, body):
        start = time.time()
        VAL_EVENTS.inc()

        try:
            raw = json.loads(body)
        except json.JSONDecodeError as exc:
            VAL_ERRORS.inc()
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
            VAL_VALID.inc()
            VAL_LATENCY.observe(time.time() - start)

        except ValidationError as exc:
            error_type = self._classify_error(exc, raw)
            VAL_VIOLATIONS.labels(reason=error_type).inc()
            VAL_LATENCY.observe(time.time() - start)

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
            VAL_ERRORS.inc()
            log.error("unexpected_validation_error",
                      event_id=event_id, error=str(exc))
            ch.basic_nack(method.delivery_tag, requeue=False)
            return

        enriched = event.model_dump(mode="json")
        enriched["dedup_flag"] = dedup_flag
        enriched["validated_at"] = datetime.now(timezone.utc).isoformat()
        enriched["ingestion_time"] = raw.get("ingestion_time")

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

    def _classify_error(self, exc: ValidationError, raw: dict) -> str:
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


if __name__ == "__main__":
    ValidatorConsumer().run()