# Layer 2 — AI Control Plane

> **Node:** ai-brain-node — `192.168.18.102`
> **Hardware:** AMD Ryzen 5, 8GB RAM, Ubuntu 24.04 Server (headless)

---

## What This Layer Does

Layer 2 is the reasoning and decision-making core of the pipeline. It runs four
agents in sequence for every anomaly event received from Layer 1. The Triage Agent
performs rapid rule-based classification and retrieves historical context from
ChromaDB. The Strategy Agent calls qwen3:1.7b via Ollama to produce a structured
7-field JSON response. The Policy Agent applies a deterministic routing table to
decide between automatic execution and human escalation. The Learning Agent
processes outcomes after dispatch and continuously updates ChromaDB with resolved
incident knowledge — making future Strategy Agent responses more accurate over time.

All four agents run on Node 2. The only external call is the Strategy Agent's HTTP
request to the Ollama API (also on Node 2, localhost:11434). No cloud API calls
are made anywhere in Layer 2.

---

## Four Agents

| Agent | Model | SLA Target | Input Queue | Output Queue |
|:------|:------|:-----------|:------------|:-------------|
| Triage Agent | None — rule-based + ChromaDB RAG | ≤ 3 seconds | `anomaly.detected` | `triage.result` |
| Strategy Agent | `qwen3:1.7b` via Ollama | ≤ 25 seconds | `triage.result` | `strategy.result` |
| Policy Agent | None — pure Python | ≤ 500 ms | `strategy.result` | `auto.execute` OR `hitl.queue` |
| Learning Agent | `qwen3:0.6b` via Ollama | ≤ 5 seconds (post-dispatch) | `outcome.feedback` | ChromaDB only |

---

## Policy Routing Table

| Priority | risk_tier | confidence | timed_out / parse_error | Decision | Reason Code |
|:--------:|:----------|:-----------|:------------------------|:---------|:------------|
| 1 | Any | Any | True | HITL | TIMEOUT or PARSE_ERROR |
| 2 | HIGH | Any | False | HITL | HIGH_RISK |
| 3 | LOW | < 0.65 | False | HITL | LOW_CONFIDENCE |
| 4 | LOW | ≥ 0.65 | False | AUTO | LOW_RISK_HIGH_CONFIDENCE |

The confidence threshold (0.65) is stored in `config/threshold_config.json` and
is recalibrated by the Learning Agent via Exponential Moving Average after each
resolved incident.

---

## ChromaDB RAG

The Triage Agent retrieves up to 3 similar past incidents from ChromaDB before
calling the Strategy Agent. Context is injected into the system prompt to improve
risk tier calibration. The Learning Agent is the sole writer to ChromaDB — no
other agent modifies the collection.

---

## RabbitMQ Queues Used

| Queue | Direction | Purpose |
|:------|:----------|:--------|
| `anomaly.detected` | Layer 1 → Triage Agent | Incoming anomaly events |
| `triage.result` | Triage → Strategy | Enriched incident + RAG context |
| `strategy.result` | Strategy → Policy | LLM JSON response + metadata |
| `auto.execute` | Policy → Layer 3 | Auto-execution instructions |
| `hitl.queue` | Policy → Layer 3 | Human review queue |
| `outcome.feedback` | Layer 3 → Learning | Post-dispatch outcome signals |

---

## Setup

See `User_Guide.md` in this directory for full Node 2 installation and startup
instructions. Ollama must be running with both qwen3:1.7b and qwen3:0.6b pulled
before starting any agents.
