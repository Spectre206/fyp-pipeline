# Layer 2 — AI Control Plane

> **Node:** ai‑brain‑node — `192.168.18.102`  
> **Hardware:** AMD Ryzen 5, 8 GB RAM, Ubuntu 24.04 Server (headless)

---

## What This Layer Does

Layer 2 is the asynchronous reasoning core of the self‑healing pipeline. It runs
four independent agents that consume anomaly events from the Fusion Engine,
enrich them with historical context (ChromaDB RAG), generate remediation
strategies via a local LLM (qwen3:1.7b), and decide whether an incident should
be auto‑executed or escalated to a human operator.

A fifth process – the **Learning Agent** – consumes post‑resolution feedback from
Layer 3, updates the ChromaDB knowledge base, and dynamically adjusts the
confidence threshold used for auto‑execution decisions.

All inter‑agent communication happens through RabbitMQ queues on Node 1.  
LLM inference and vector storage run locally on this node.

---

## Components

| Component | Directory / File | Role |
|:----------|:-----------------|:-----|
| Triage Agent | `agents/triage_agent.py` | Rule‑based classification + ChromaDB RAG retrieval. Produces `triage.result`. |
| Strategy Agent | `agents/strategy_agent.py` | Calls **qwen3:1.7b** via Ollama. Generates a 7‑field JSON remediation plan. Produces `strategy.result`. |
| Policy Agent | `agents/policy_agent.py` | Deterministic 5‑rule routing table. Routes to `auto.execute` or `hitl.queue` based on risk tier and confidence. |
| Learning Agent | `agents/learning_agent.py` | Calls **qwen3:0.6b** for incident summarisation. Upserts ChromaDB. Updates EMA confidence threshold. |
| ChromaDB | `chromadb_utils/` + `chromadb_data/` | Persistent vector store for historical incident retrieval (RAG). |
| Ollama | `ollama/` (client) | Local LLM inference server (`localhost:11434`). |

---

## RabbitMQ Queues Used

| Queue | Direction | Purpose |
|:------|:----------|:--------|
| `anomaly.detected` | Fusion Engine → Triage Agent | Fused anomaly events |
| `triage.result` | Triage Agent → Strategy Agent | Enriched event + RAG context |
| `strategy.result` | Strategy Agent → Policy Agent | LLM response + schema validation |
| `auto.execute` | Policy Agent → Layer 3 | Safe for automatic remediation |
| `hitl.queue` | Policy Agent → Layer 3 | Requires human review |
| `outcome.feedback` | Layer 3 → Learning Agent | Post‑resolution outcomes |

---

## Key Design Features

- **Decoupled async processing** – Layer 2 never blocks Layer 1; all communication is via RabbitMQ.
- **RAG‑enhanced reasoning** – The Triage Agent retrieves up to 3 similar past incidents from ChromaDB before the LLM call, improving risk‑tier accuracy.
- **Policy‑bounded autonomy** – The Policy Agent enforces a strict tiered routing table; execution authority lives only in Layer 3.
- **Adaptive threshold** – The Learning Agent uses an EMA (α=0.9) to adjust the confidence threshold for auto‑execution based on real outcomes.
- **Full observability** – All agents expose Prometheus metrics on ports 8010‑8013.

---

## Setup & Usage

For detailed setup, startup order, verification steps, and troubleshooting, see
the **[Layer 2 User Guide](User_Guide.md)**.

For the complete build history and architecture decisions, see the
**[Layer 2 Component Build Log](../docs/layer2_component_log.md)**.