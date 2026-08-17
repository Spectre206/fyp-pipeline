# Layer 3 — Human-in-the-Loop & Observability

> **Node:** gateway-node — `192.168.18.103`  
> **Hardware:** Intel Core i5, 8 GB RAM, Ubuntu 24.04 Desktop

---

## What This Layer Does

Layer 3 is the human interface and observability hub of the pipeline. It runs
two parallel subsystems: the HITL (Human‑in‑the‑Loop) subsystem handles all
incidents that the Policy Agent has routed for human review or automatic
execution, and the observability subsystem (Prometheus + Grafana) scrapes
metrics from all three nodes and presents them in real‑time dashboards.

The Django HITL Dashboard displays the full reasoning chain for each incident
in the human review queue — original event, Triage Agent output + RAG context,
Strategy Agent JSON response + raw LLM output, and Policy Agent routing reason.
Operators can **approve**, **reject**, or **modify** the proposed actions. Every decision is
logged to a SQLite database keyed by `event_id`. The Auto‑Execution Engine handles
incidents in the `auto.execute` queue without human involvement and publishes
outcomes back to the Learning Agent via `outcome.feedback`.

---

## Components

| Component | Directory | Role |
|:----------|:----------|:-----|
| Django HITL Dashboard | `dashboard/` | Web UI for human review, approval, and decision logging. |
| Auto‑Execution Engine | `auto_executor/` | Consumes `auto.execute` queue. Executes simulated remediation. Publishes `outcome.feedback`. |
| SQLite Logger | `sqlite_logger/` | Centralised writer for the decision log. All decisions from both HITL and auto‑execution flow through here. |
| Prometheus | Installed in Phase 0 | Scrapes Node Exporter metrics from all 3 nodes. Scrapes custom pipeline counters from all agents. |
| Grafana | Installed in Phase 0 | Dashboards for node health, pipeline throughput, MTTA, queue depths, and agent latencies. |

---

## RabbitMQ Queues Used

| Queue | Direction | Purpose |
|:------|:----------|:--------|
| `hitl.queue` | Layer 2 → HITL Dashboard | Incidents requiring human review |
| `auto.execute` | Layer 2 → Auto‑Executor | Incidents approved for automatic execution |
| `outcome.feedback` | Auto‑Executor / HITL → Layer 2 | Post‑dispatch outcomes for Learning Agent |

---

## Key HITL Dashboard Features

- **Real‑time incident queue** – shows severity, component, routing reason, and time‑in‑queue for each pending incident.
- **Full reasoning chain** – clicking an incident reveals the Triage Agent output, Strategy Agent JSON + raw LLM response, and Policy Agent routing decision.
- **Three operator actions** – **APPROVE** (execute as‑is), **REJECT** (log and discard), **MODIFY** (edit the recommended actions before executing).
- **Auto‑execution monitor** – a separate panel shows auto‑executed events and their outcomes.
- **Grafana dashboard** – real‑time pipeline metrics (Agent Pipeline & Fusion Engine Performance).

---

## Setup

See the **[Layer 3 User Guide](User_Guide.md)** for startup order, verification, and troubleshooting.  
For the complete build history and architecture decisions, see the **[Layer 3 Component Build Log](../docs/layer3_component_log.md)**.