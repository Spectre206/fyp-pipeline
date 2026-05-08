# Layer 3 User Guide — gateway-node (192.168.18.103)

This guide covers the Django HITL Dashboard and Auto-Execution Engine setup on Node 3.
Prometheus and Grafana were installed and configured in Phase 0 — those steps are in
Phase_0_Infrastructure/User_Guide.md. Layers 1 and 2 must be running before Layer 3
can be functionally tested end-to-end.

---

## 1. Prerequisites Checklist

Before starting Layer 3, confirm: Node 3 has static IP 192.168.18.103, hostname
gateway-node, Prometheus is running and all three node targets show as UP at
http://192.168.18.103:9090, Grafana is accessible at http://192.168.18.103:3000,
the hitl.queue and auto.execute queues are visible in the RabbitMQ management UI
at http://192.168.18.101:15672, and Node 3 can reach the RabbitMQ broker on Node 1
at port 5672.

---

## 2. Python Environment Setup

This section will cover creating a virtual environment on Node 3, installing all
dependencies from requirements_node3.txt, and verifying the Django installation.
The SQLite database file location, ALLOWED_HOSTS setting, and SECRET_KEY
configuration for the Django project will be documented here. For development and
evaluation purposes, Django runs with DEBUG=True — this section will note what to
change for a more hardened deployment.

---

## 3. Django Database Migrations

This section will cover running the initial Django migrations to create the
decisions table in SQLite, verifying the schema matches the specification in the
System Design document Section 8.2, and confirming the database file is in the
correct location (excluded from git by .gitignore).

---

## 4. Starting the Django HITL Dashboard

This section will document starting the Django development server, the expected
URL (http://192.168.18.103:8000), how to verify that Server-Sent Events (SSE) are
working for real-time queue updates, and what the initial empty queue view looks
like. It will also cover how to create a superuser account for the dashboard login.

---

## 5. Starting the Auto-Execution Engine

This section will describe starting the Auto-Execution Engine as a standalone
Python process consuming from the auto.execute queue. It will explain the simulated
remediation actions (for evaluation purposes, remediation is simulated with a logged
sleep — the Action field from the Strategy Agent output is recorded but not executed
against real infrastructure), how outcome messages are constructed and published to
outcome.feedback, and how to verify that the SQLite logger is recording auto-execution
events correctly.

---

## 6. End-to-End Pipeline Test

This section will walk through a complete pipeline test: triggering a known anomaly
event from the SEG on Node 1, watching it flow through Layer 1 to anomaly.detected,
through the four Layer 2 agents, and arriving at either the HITL Dashboard or the
Auto-Execution Engine on Node 3. Expected log output at each stage and queue depths
in the RabbitMQ management UI will be shown for both the AUTO and HITL paths.

---

## 7. Grafana Dashboard Configuration

This section will cover adding the custom pipeline metrics from Layer 1 and Layer 2
agents as Prometheus scrape targets, importing or creating Grafana dashboard panels
for MTTA, queue depths, tokens/second, and per-agent latencies, and setting up
alerting rules for the Ollama service down condition described in the System Design
document failure paths.

---

## 8. Troubleshooting

Common issues will be documented here: Django SSE not updating in real time (Django
Channels configuration), decisions not appearing in SQLite (SQLite logger not running
or wrong database path), auto.execute queue growing without being consumed (executor
process not running), Prometheus targets showing DOWN for Layer 1/2 custom metrics
(check that prometheus-client is running in each agent process).
