"""
HITL Dashboard Serializers — Incident and Decision JSON Serialisation

This module contains Django REST Framework serializers for the Decision model
and for the incident payload structure consumed from the hitl.queue RabbitMQ
queue. The incident serializer validates that all required fields from the
Policy Agent output (full reasoning chain, routing decision, reason code)
are present before the incident is stored or displayed.

The decision serializer handles the JSON serialisation of original_actions and
final_actions list fields to/from SQLite TEXT storage, and validates that
decision_type is one of the four allowed values.
"""
