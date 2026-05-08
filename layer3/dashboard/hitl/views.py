"""
HITL Dashboard Views — Queue, Incident Detail, Operator Actions

This module contains all Django views for the HITL Dashboard:

  - QueueView: renders the real-time incident queue page. Connects to the
    hitl.queue RabbitMQ consumer and displays all pending incidents ordered
    by arrival time. Each row shows event_id, anomaly_type, severity,
    affected_component, node, routing_reason, and time_in_queue.

  - IncidentDetailView: renders the full reasoning chain for a single incident.
    Shows the original event payload, Triage Agent output + RAG context,
    Strategy Agent JSON + raw LLM output, and Policy Agent routing decision.

  - ApproveView, RejectView, ModifyView: operator action endpoints. Each
    requires a POST request with a confirmation token. All three write to the
    SQLite decision log via sqlite_logger and publish to outcome.feedback.
    ModifyView accepts an edited actions list before publishing.

  - AutoMonitorView: separate panel showing the auto.execute queue history
    and execution outcomes from the Auto-Execution Engine.
"""
