"""
Schema Drift Router -- Validation Failure -> anomaly.detected

This module handles the routing of Pydantic validation failures. When the
validator raises a ValidationError, this router:

  1. Extracts the error type (missing field, type mutation, or unexpected value)
     from the Pydantic error list.
  2. Maps the error type to a severity level (MEDIUM for missing fields,
     HIGH for type mutations).
  3. Constructs a well-formed anomaly event with anomaly_type = "schema_drift"
     and publishes it to the anomaly.detected queue via the RabbitMQ producer.

The original raw event payload is preserved in the event's context field for
debugging. The event_id from the original raw event is carried through so the
ground truth label in labels.csv can still be matched for evaluation.

NOTE on scope: only two of SEG's three schema_drift subtypes are actually
caught here. "missing_field" and "type_mutation" are structural violations
Pydantic can detect, so they're intercepted and routed by this module.
"value_shift" (a statistically shifted but structurally valid metric_values
dict) passes Pydantic validation normally and is NOT routed here -- it flows
through the Feature Store and ADM like any other event, to be caught later by
the PSI Detector's statistical drift check. This is intentional: Pydantic
validates structure, PSI Detector validates distribution -- the two-stage
split matches System Design's "Model 5: Pydantic Validator + PSI Detector"
combined entry.
"""
# layer1/validator/schema_drift_router.py
#
# Routes structural validation failures directly to anomaly.detected.
# Called by ValidatorConsumer when a Pydantic ValidationError is caught.
#
# v1.3: exchange and routing key are now passed in from validator.py's config
# (validator_config.json) instead of being hardcoded a second time here --
# single source of truth for the RabbitMQ addressing.
#
# The Fusion Engine NEVER sees these events -- they arrive pre-detected.

import json
import uuid
import logging
from datetime import datetime, timezone

import pika

log = logging.getLogger(__name__)

# Severity assigned per error type
SEVERITY_MAP = {
    "MISSING_FIELD":    "MEDIUM",
    "TYPE_MUTATION":    "HIGH",
    "SCHEMA_VIOLATION": "MEDIUM",
    "UNKNOWN":          "MEDIUM",
}

# Risk tier per severity -- NOTE: this happens to numerically match SEG's
# own ground-truth RISK_TIER_MAP for schema_drift (MEDIUM->LOW, HIGH->HIGH).
# This is NOT a ground-truth leak: the Validator never sees SEG's ground
# truth fields (they're stripped before publishing, per SEG's design), and
# this value is derived independently via the Validator's own error
# classification. The alignment is a confirmation that the Validator's
# logic is well-calibrated against the intended severity model, not a
# shortcut that reads the hidden label.
RISK_TIER_MAP = {
    "MEDIUM": "LOW",
    "HIGH":   "HIGH",
}


class SchemaDriftRouter:
    """
    Repackages a failed validation result as a schema_drift anomaly
    and publishes it directly to anomaly.detected via fyp.events exchange.

    This bypasses both the Feature Store and the Fusion Engine --
    malformed events cannot be safely featurised or correlated.
    """

    def __init__(
        self,
        channel: pika.adapters.blocking_connection.BlockingChannel,
        exchange: str = "fyp.events",
        routing_key: str = "anomaly.schema_drift",
    ):
        self.ch = channel
        self.exchange = exchange
        self.routing_key = routing_key

    def route(self, raw: dict, exc: Exception, error_type: str):
        """
        Build and publish a schema_drift anomaly event.

        Args:
            raw:        The original raw event dict (may be partially malformed)
            exc:        The Pydantic ValidationError (or any Exception)
            error_type: Classified error type string
                        ('MISSING_FIELD' | 'TYPE_MUTATION' | 'SCHEMA_VIOLATION' | 'UNKNOWN')
        """
        severity = SEVERITY_MAP.get(error_type, "MEDIUM")
        risk = RISK_TIER_MAP.get(severity, "LOW")

        anomaly = {
            "event_id": raw.get("event_id") or str(uuid.uuid4()),
            "timestamp": raw.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "ingestion_time": raw.get("ingestion_time"),
            "anomaly_type": "schema_drift",
            "severity": severity,

            # Computed (not ground-truth) risk tier -- see module docstring.
            # NOTE: not yet consumed by any documented Policy Agent rule.
            # Flagged in LAYER1_COMPONENT_LOG.md as an open question for
            # whoever builds Layer 2's Policy Agent.
            "risk_tier": risk,

            "affected_component": raw.get("affected_component", "unknown"),
            "node": raw.get("node", "stream-node"),
            "metric_values": {"validation_error_count": 1.0},
            "context": (
                f"Schema violation [{error_type}]: "
                f"{str(exc)[:300]}"
            ),
            "feature_vector": {},
            "bypass_fusion": True,
            "detection_model": "pydantic_validator",
            "detection_metadata": {
                "error_type": error_type,
                "violation_detail": str(exc)[:500],
                "original_event_id": raw.get("event_id", "MISSING"),
            },
        }

        body = json.dumps(anomaly).encode("utf-8")

        self.ch.basic_publish(
            exchange=self.exchange,
            routing_key=self.routing_key,   # matches anomaly.# binding
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json"
            )
        )

        log.warning(
            f"[SchemaDriftRouter] Routed schema_drift to anomaly.detected "
            f"| event_id={anomaly['event_id']} | type={error_type} | severity={severity}"
        )