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
