# Layer 2 — AI Control Plane

> **Node:** ai-brain-node — `192.168.18.102`
> **Hardware:** AMD Ryzen 5, 8 GB RAM, Ubuntu 24.04 Server (headless)

---

## 1. Overview

Layer 2 constitutes the asynchronous reasoning core of the self-healing pipeline. It comprises four independent agents that consume anomaly events from the Fusion Engine, enrich them with historical context retrieved via ChromaDB-based Retrieval-Augmented Generation (RAG), generate remediation strategies through a locally hosted large language model (qwen3:1.7b), and determine whether an incident should be executed automatically or escalated to a human operator.

A fifth process — the **Learning Agent** — consumes post-resolution feedback from Layer 3, updates the ChromaDB knowledge base, and dynamically recalibrates the confidence threshold governing auto-execution decisions.

All inter-agent communication is conducted through RabbitMQ queues hosted on Node 1. LLM inference and vector storage are performed locally on this node.

---

## 2. Components

| Component | Directory / File | Role |
|:----------|:-----------------|:-----|
| Triage Agent | `agents/triage_agent.py` | Performs rule-based classification and ChromaDB RAG retrieval. Produces `triage.result`. |
| Strategy Agent | `agents/strategy_agent.py` | Invokes **qwen3:1.7b** via Ollama to generate a seven-field JSON remediation plan. Produces `strategy.result`. |
| Policy Agent | `agents/policy_agent.py` | Applies a deterministic five-rule routing table, directing incidents to `auto.execute` or `hitl.queue` based on risk tier and confidence. |
| Learning Agent | `agents/learning_agent.py` | Invokes **qwen3:0.6b** for incident summarisation, upserts records into ChromaDB, and updates the EMA-based confidence threshold. |
| ChromaDB | `chromadb_utils/` + `chromadb_data/` | Persistent vector store supporting historical incident retrieval (RAG). |
| Ollama | `ollama/` (client) | Local LLM inference server (`localhost:11434`). |
| File Logger | `utils/file_logger.py` | Shared, append-only JSONL logger used across all agents. |
| Runtime Logs | `logs/` | Persistent per-agent logs enabling restart-safe result tracking. |

---

## 3. RabbitMQ Queues

| Queue | Direction | Purpose |
|:------|:----------|:--------|
| `anomaly.detected` | Fusion Engine → Triage Agent | Fused anomaly events |
| `triage.result` | Triage Agent → Strategy Agent | Enriched event with RAG context |
| `strategy.result` | Strategy Agent → Policy Agent | LLM-generated response with schema validation |
| `auto.execute` | Policy Agent → Layer 3 | Incidents approved for automatic remediation |
| `hitl.queue` | Policy Agent → Layer 3 | Incidents requiring human review |
| `outcome.feedback` | Layer 3 → Learning Agent | Post-resolution outcomes |

---

## 4. Key Design Features

- **Decoupled asynchronous processing** — Layer 2 operates independently of Layer 1; all inter-layer communication occurs via RabbitMQ, ensuring Layer 1 is never blocked.
- **RAG-enhanced reasoning** — The Triage Agent retrieves up to three similar past incidents from ChromaDB prior to the LLM call, improving the accuracy of risk-tier classification.
- **Policy-bounded autonomy** — The Policy Agent enforces a strict, tiered routing table; execution authority resides exclusively within Layer 3.
- **Adaptive thresholding** — The Learning Agent employs an exponential moving average (EMA, α = 0.9) to adjust the auto-execution confidence threshold in response to real-world outcomes.
- **Persistent logging** — Every agent appends one JSON line per processed message to `logs/*.jsonl`, ensuring that cumulative counts remain accurate across process restarts and multi-session pipeline runs.
- **Robust JSON extraction** — The Strategy Agent strips markdown code fences and extracts the first complete JSON object from the LLM output, reducing parsing errors.
- **Full observability** — All agents expose Prometheus metrics on ports 8010–8013.

---

## 5. Timestamp Semantics

Three distinct timestamps are tracked throughout the pipeline:

| Timestamp | Meaning |
|-----------|---------|
| `timestamp` | Original synthetic event time |
| `ingestion_time` | Actual pipeline entry time during replay |
| `triage_timestamp` | Time at which the Triage Agent processed the event |

**Mean Time to Acknowledge (MTTA)** and **Mean Time to Resolution (MTTR)** are defined as control-plane latencies:

- **MTTA** = `policy_timestamp` − `triage_timestamp`
- **MTTR** = `outcome_feedback_time` − `triage_timestamp`

These metrics capture AI reasoning and routing latency independently of queue backlog effects.

---

## 6. Logs

The following files are written to `layer2/logs/`:

| File | Written By | Content |
|------|-----------|---------|
| `triage_agent.jsonl` | Triage Agent | Event ID, anomaly type, severity, protocol, RAG documents, latency |
| `strategy_agent.jsonl` | Strategy Agent | Event ID, JSON validity, schema validity, issues, latency, tokens/second |
| `policy_agent.jsonl` | Policy Agent | Event ID, decision, reason, threshold, latency |
| `learning_agent.jsonl` | Learning Agent | Event ID, outcome type, summary, latency |
| `parse_error.jsonl` | Strategy Agent | Raw LLM output recorded upon JSON parsing failure |

**Note:** The `logs/` directory contains runtime data and is excluded from version control (Git). It should be cleared prior to each clean evaluation run.

---

## 7. Configuration

- `config/threshold_config.json` — EMA-based confidence threshold applied by the Policy Agent; updated automatically by the Learning Agent.
- `prompts/strategy_system_prompt.txt` — System prompt for qwen3:1.7b.
- `prompts/learning_system_prompt.txt` — System prompt for qwen3:0.6b.
- `.env` — Configuration parameters for RabbitMQ, Ollama, and model settings.

---

## 8. Setup & Usage

For detailed setup instructions, startup sequencing, verification procedures, and troubleshooting guidance, refer to the **[Layer 2 User Guide](User_Guide.md)**.

For the complete build history and architectural decision record, refer to the **[Layer 2 Component Build Log](../docs/layer2_component_log.md)**.