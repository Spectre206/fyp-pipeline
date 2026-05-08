# Layer 3 — Human-in-the-Loop & Observability

> **Node:** gateway-node — `192.168.18.103`
> **Hardware:** Intel Core i5, 8GB RAM, Ubuntu 24.04 Desktop

---

## What This Layer Does

Layer 3 is the human interface and observability hub of the pipeline. It runs
two parallel subsystems: the HITL (Human-in-the-Loop) subsystem handles all
incidents that the Policy Agent has routed for human review or automatic
execution, and the observability subsystem (Prometheus + Grafana) scrapes
metrics from all three nodes and presents them in real-time dashboards.

The Django HITL Dashboard displays the full reasoning chain for each incident
in the human review queue — original event, Triage Agent output + RAG context,
Strategy Agent JSON response + raw LLM output, and Policy Agent routing reason.
Operators can approve, reject, or modify the proposed actions. Every decision is
logged to a SQLite database keyed by event_id. The Auto-Execution Engine handles
incidents in the auto.execute queue without human involvement and publishes
outcomes back to the Learning Agent via outcome.feedback.

---

## Components

| Component | Directory | Role |
|:----------|:----------|:-----|
| Django HITL Dashboard | `dashboard/` | Web UI for human review, approval, and decision logging. Real-time queue updates via Server-Sent Events (SSE). |
| Auto-Execution Engine | `auto_executor/` | Consumes `auto.execute` queue. Executes simulated remediation. Publishes outcome to `outcome.feedback`. |
| SQLite Logger | `sqlite_logger/` | Centralised writer for the decision log. All decisions from both HITL and auto-execution flow through here. |
| Prometheus | Installed in Phase 0 | Scrapes Node Exporter metrics from all 3 nodes. Scrapes custom pipeline counters from all agents. |
| Grafana | Installed in Phase 0 | Dashboards for node health, pipeline throughput, MTTA, queue depths, and agent latencies. |

---

## RabbitMQ Queues Used

| Queue | Direction | Purpose |
|:------|:----------|:--------|
| `hitl.queue` | Layer 2 → HITL Dashboard | Incidents requiring human review |
| `auto.execute` | Layer 2 → Auto-Executor | Incidents approved for automatic execution |
| `outcome.feedback` | Auto-Executor / HITL → Layer 2 | Post-dispatch outcomes for Learning Agent |

---

## Key HITL Dashboard Features

The dashboard exposes a real-time incident queue with severity, component, routing
reason, and time-in-queue for each pending incident. Clicking any incident shows
the full multi-step reasoning chain. Operators see three action buttons: APPROVE
(execute as-is), REJECT (log and discard), MODIFY (edit actions before executing).
All decisions require a confirmation step. A separate panel shows auto-execution
events and their outcomes in real time.

---

## Setup

See `User_Guide.md` in this directory for Prometheus, Grafana, and Django
installation instructions on Node 3. Prometheus and Grafana were installed in
Phase 0 — this guide covers the Django application and Auto-Execution Engine.
