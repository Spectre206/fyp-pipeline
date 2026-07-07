"""
Schema Drift Router — Validation Failure → anomaly.detected

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
"""
# layer1/validator/schema_drift_router.py
#
# Routes structural validation failures directly to anomaly.detected.
# Called by ValidatorConsumer when a Pydantic ValidationError is caught.
#
# v1.2 routing: publishes to fyp.events exchange, routing key anomaly.schema_drift
# The Fusion Engine NEVER sees these events — they arrive pre-detected.

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

# Risk tier per severity (for ground truth alignment)
RISK_TIER_MAP = {
    "MEDIUM": "LOW",
    "HIGH":   "HIGH",
}

class SchemaDriftRouter:
    """
    Repackages a failed validation result as a schema_drift anomaly
    and publishes it directly to anomaly.detected via fyp.events exchange.

    This bypasses both the Feature Store and the Fusion Engine —
    malformed events cannot be safely featurised or correlated.
    """

    def __init__(self, channel: pika.adapters.blocking_connection.BlockingChannel):
        self.ch = channel

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
        risk     = RISK_TIER_MAP.get(severity, "LOW")

        anomaly = {
            # Preserve original event_id if present and valid, else generate new one
            "event_id":           raw.get("event_id") or str(uuid.uuid4()),
            
            # FIX 1: Preserve original timestamp to maintain SEG temporal spacing
            "timestamp":          raw.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            
            "anomaly_type":       "schema_drift",
            "severity":           severity,
            
            # FIX 2: Actually include the calculated risk tier in the payload
            "risk_tier":          risk, 
            
            "affected_component": raw.get("affected_component", "unknown"),
            "node":               raw.get("node", "stream-node"),
            "metric_values":      {"validation_error_count": 1.0},
            "context": (
                f"Schema violation [{error_type}]: "
                f"{str(exc)[:300]}"    # truncate long pydantic error messages
            ),
            "feature_vector":     {},   # no Feature Store data for violations
            "bypass_fusion":      True,
            "detection_model":    "pydantic_validator",
            "detection_metadata": {
                "error_type":        error_type,
                "violation_detail":  str(exc)[:500],
                "original_event_id": raw.get("event_id", "MISSING"),
            },
        }

        body = json.dumps(anomaly).encode("utf-8")

        self.ch.basic_publish(
            exchange="fyp.events",
            routing_key="anomaly.schema_drift",   # matches anomaly.# binding
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2,                   # persistent message
                content_type="application/json"
            )
        )

        log.warning(
            f"[SchemaDriftRouter] Routed schema_drift to anomaly.detected "
            f"| event_id={anomaly['event_id']} | type={error_type} | severity={severity}"
        )