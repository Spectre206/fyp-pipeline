"""
HITL Dashboard Django ORM Models — Decision Log

This module defines the Django ORM model for the decisions table in SQLite.
The Decision model maps to the schema specified in System Design Section 8.2:

  Fields: id, event_id, anomaly_type, severity, affected_component, node,
  routing_reason, risk_tier_from_llm, confidence_from_llm, decision_type,
  decision_timestamp, time_in_queue_seconds, original_actions (JSON),
  final_actions (JSON, may differ from original if operator used Modify),
  operator_notes, auto_execute_outcome, created_at.

The decision_type field takes one of: APPROVE, REJECT, MODIFY, AUTO_EXECUTE.
This model is also used by sqlite_logger.py as the write target — the logger
does not interact with Django's ORM directly but writes to the same SQLite
file via a direct sqlite3 connection to avoid the Django app context dependency
from within the Auto-Execution Engine process.
"""
