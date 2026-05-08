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
