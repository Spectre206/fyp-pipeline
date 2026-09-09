# Layer 2 Component Log

## 1. Purpose
This document serves as the technical implementation record of Layer 2 — the AI Control Plane. It strictly documents what is actually implemented in the codebase today, prioritizing source code and configuration reality over intended architecture or design goals.

## 2. Layer 2 Scope
Layer 2 functions as the asynchronous AI Control Plane of the self-healing pipeline. It consumes anomalies detected by Layer 1, retrieves historical context, formulates JSON-structured remediation strategies using a local LLM, and enforces deterministic policy rules to route the incident for either automatic execution or human-in-the-loop (HITL) review. It operates completely independently of Layer 1.

## 3. Physical Deployment
- **Node:** Node 2 (`ai-brain-node`).
- **Hardware:** CPU-only execution (AMD Ryzen 5, 8 GB RAM). No GPU or CUDA requirements.
- **OS:** Ubuntu 24.04 Server (headless).
- **Core Services:** Local Ollama inference server (`http://localhost:11434`), ChromaDB.

## 4. Layer 2 Architecture
Layer 2 consists of four distinct agents communicating via RabbitMQ. 
The architecture enforces a strict boundary between reasoning and policy:
- **Triage (Rule-based)** normalizes and classifies incoming events.
- **Strategy (LLM-based)** proposes remediation strategies.
- **Policy (Rule-based)** enforces safety boundaries and decides execution authority.
- **Learning (LLM/Math)** updates the memory and thresholds based on outcomes.

## 5. Agent Components

### 5.1 Triage Agent
- **Purpose:** Normalizes incoming Layer 1 anomalies, applies deterministic rule-based classification, and retrieves RAG context from ChromaDB. **It is NOT an LLM agent.**
- **File:** `agents/triage_agent.py`
- **Input:** `anomaly.detected` queue.
- **Output:** `triage.result` queue.
- **Processing Logic:** Uses a hardcoded `PROTOCOL_TABLE` to map `(anomaly_type, severity)` to a `response_protocol`. It also derives `anomaly_type` from `contributing_models` for fused events.
- **RAG Usage:** Queries ChromaDB for up to 3 similar incidents with positive outcomes to provide historical context.

### 5.2 Strategy Agent
- **Purpose:** Ollama-backed reasoning component that generates a structured JSON remediation plan.
- **File:** `agents/strategy_agent.py`
- **Input:** `triage.result` queue.
- **Output:** `strategy.result` queue.
- **Model:** `qwen3:1.7b` via local Ollama.
- **Processing Logic:** Compiles a prompt using the original event, Triage response protocol, and RAG context. Generates a response and extracts the JSON object (stripping markdown).
- **Validation:** Enforces a strict 7-field JSON schema.
- **Fallback:** On JSON extraction failure or LLM timeout, sets `valid_json=False` or `timed_out=True`, which the Policy Agent will subsequently route to HITL.

### 5.3 Policy Agent
- **Purpose:** Deterministic policy enforcement component. **It does NOT use an LLM.**
- **File:** `agents/policy_agent.py`
- **Input:** `strategy.result` queue.
- **Output:** `auto.execute` or `hitl.queue` queue.
- **Processing Logic:** Uses a 5-rule deterministic routing table:
  1. Timeout or parse error → HITL
  2. Fusion Engine low confidence → HITL
  3. Risk tier HIGH → HITL
  4. Confidence < Threshold → HITL
  5. Low risk, high confidence → AUTO

### 5.4 Learning Agent
- **Purpose:** Summarizes resolved incidents, upserts them to ChromaDB, and mathematically updates the confidence threshold.
- **File:** `agents/learning_agent.py`
- **Physical Location:** Runs on Node 2 (`ai-brain-node`), alongside other Layer 2 agents.
- **Input:** `outcome.feedback` queue (from Layer 3).
- **Model:** `qwen3:0.6b` via local Ollama.
- **Processing Logic:** Generates a one-sentence incident summary. Upserts the summary and incident metadata to ChromaDB. 
- **Learning Mechanism:** Updates the `confidence_threshold` via an Exponential Moving Average (EMA, α=0.9) mathematically based on the outcome type. No formal LLM model fine-tuning or weight updating occurs. 

## 6. Agent Communication
All agents communicate entirely asynchronously via the `fyp.events` exchange on the Node 1 RabbitMQ broker. Agents consume messages, process them, and publish to the next queue without direct agent-to-agent synchronous calls.

## 7. RabbitMQ Topology

| Exchange | Type | Queue | Routing Key | Producer | Consumer |
| -------- | ---- | ----- | ----------- | -------- | -------- |
| `fyp.events` | `topic` | `anomaly.detected` | `anomaly.#` | Layer 1 | Triage Agent |
| `fyp.events` | `topic` | `triage.result` | `triage.result` | Triage Agent | Strategy Agent |
| `fyp.events` | `topic` | `strategy.result` | `strategy.result` | Strategy Agent | Policy Agent |
| `fyp.events` | `topic` | `hitl.queue` | `hitl.queue` | Policy Agent | Layer 3 |
| `fyp.events` | `topic` | `auto.execute` | `auto.execute` | Policy Agent | Layer 3 |
| `fyp.events` | `topic` | `outcome.feedback` | `outcome.feedback` | Layer 3 | Learning Agent |

## 8. Message Contracts

### Layer 1 → Triage (`anomaly.detected`)
- **Required fields:** `event_id`, `timestamp`
- Layer 2 receives two distinct structures here:
  - **Structural Schema Anomalies:** Have `anomaly_type="schema_drift"` and `severity`.
  - **Fused Incidents:** Lack `anomaly_type` directly; use `contributing_models` and `fused_severity`.

### Triage → Strategy (`triage.result`)
- **Required fields:** `event_id`, `triage_timestamp`, `response_protocol`, `original_event`.
- **Optional/Generated:** `rag_context`, `rag_context_formatted`, `triage_agent_latency_ms`.

### Strategy → Policy (`strategy.result`)
- **Required fields:** `event_id`, `strategy_timestamp`, `valid_json`, `schema_valid`, `timed_out`, `triage_result`.
- **Schema Output:** `llm_response` (containing 7 required fields: `anomaly_type`, `severity`, `affected_component`, `recommended_actions`, `confidence`, `risk_tier`, `reasoning`).

## 9. LLM Integration
| Component | LLM | Model | Provider | ChromaDB/RAG | Purpose |
| --------- | --- | ----- | -------- | ------------ | ------- |
| Triage | No | N/A | N/A | Retrieval | Searches historical context to calibrate risk tier. |
| Strategy | Yes | `qwen3:1.7b` | Ollama (Local) | None | Generates JSON remediation plan. |
| Policy | No | N/A | N/A | None | Deterministic routing rules. |
| Learning | Yes | `qwen3:0.6b` | Ollama (Local) | Persistence | Summarizes incident for long-term ChromaDB storage. |

## 10. Ollama Configuration
- **Host:** `http://localhost:11434`
- **Execution:** CPU-only.
- **Strategy Agent:** `qwen3:1.7b`, timeout 35s, `num_predict=512`.
- **Learning Agent:** `qwen3:0.6b`, timeout 10s, `num_predict=256`.

## 11. ChromaDB / Historical Memory
- **Collection Name:** `incident_history`
- **Embedding:** `all-MiniLM-L6-v2` (SentenceTransformers)
- **Retrieval:** Triage Agent retrieves up to 3 documents filtering only for positive outcomes (`AUTO_EXECUTE_SUCCESS` or `HITL_APPROVED`) to inject into the Strategy prompt.
- **Persistence:** Learning Agent upserts resolved incidents. Negative examples are stored (with `negative_example=True`) but are excluded from RAG retrieval.

## 12. Decision Flow
1. **Layer 1** detects an anomaly.
2. **Triage Agent** assigns a baseline protocol and fetches historical RAG context.
3. **Strategy Agent** (LLM) evaluates context and outputs a confident score and a risk tier.
4. **Policy Agent** acts as a hard boundary. If Strategy's confidence is too low or risk tier is too high, it overrides and routes to HITL. Otherwise, it routes to AUTO.

## 13. Policy and Safety Boundaries
The LLM does **not** have unconstrained authority to execute actions. 
- Strategy **proposes** a remediation strategy and calculates a confidence score.
- Policy **enforces** safety. It strictly blocks `HIGH` risk tier actions and low-confidence proposals from auto-execution. 
- All JSON schema parse failures or timeouts are deterministically routed to HITL.

## 14. Error Handling
- **Missing Layer 1 Fields:** Triage Agent's `_normalize_event()` explicitly maps missing `anomaly_type` fields from `contributing_models` for fused incidents.
- **LLM Parse Failure:** Strategy Agent sets `valid_json=False`, saves raw text to `parse_error.jsonl`.
- **RAG Failure:** Triage Agent uses an empty list `[]` and proceeds.
- **Learning LLM Failure:** Learning Agent uses a hardcoded fallback string.
- **Missing Timestamps:** Policy/Learning Agents increment a `fyp_timestamp_missing_total` Prometheus counter and skip MTTA/MTTR calculations.

## 15. Retry / Failure Behavior
- RabbitMQ failures are handled via `basic_nack(requeue=False)` when an unhandled exception occurs inside the agent, effectively dropping or dead-lettering the message to prevent infinite loops.
- There are no LLM internal retry loops. A failed LLM generation results in a `TIMEOUT` or `PARSE_ERROR` route to Layer 3.

## 16. Metrics and Observability
All agents export Prometheus metrics:
- **Triage (8010):** `fyp_triage_latency_s`, `fyp_triage_processed_total`
- **Strategy (8011):** `fyp_strategy_latency_s`, `fyp_strategy_schema_valid_total`, `fyp_strategy_tokens_per_s`
- **Policy (8012):** `fyp_policy_latency_s`, `fyp_routing_decision_total`, `fyp_mtta_seconds`
- **Learning (8013):** `fyp_learning_outcomes_total`, `fyp_learning_threshold_updates_total`, `fyp_mttr_seconds`

**Logging:** All agents use append-only JSONL files in `layer2/logs/` (`triage_agent.jsonl`, `strategy_agent.jsonl`, `policy_agent.jsonl`, `learning_agent.jsonl`, `parse_error.jsonl`).

## 17. Evaluation and Research Metrics
- **Control Plane Latency (CPL):** Defined as `triage_timestamp` to `policy_timestamp`. Documented target `< 30s`.
- **MTTA:** Measured in Policy Agent as `policy_timestamp - triage_timestamp`. Note: This is an AI control-plane acknowledgement latency, not human MTTA.
- **MTTR:** Measured in Learning Agent as `outcome_time - triage_timestamp`. Note: This is a decision-to-outcome latency, not infrastructure recovery time.
- **Schema Validity Rate (SVR):** Tracked dynamically by Strategy Agent.
- **Model Benchmark Distinction:** The Phase 0 Offline Benchmark demonstrated `qwen3:1.7b` achieving ~90% schema-valid outputs on 30 strict adversarial prompts. This is a **model-level benchmark** and is explicitly distinct from the runtime system SVR target (≥95%).
- **Learning Evaluation:** Formal quantitative Learning Agent quality/accuracy evaluation was **not found in the inspected repository**. Learning is currently an observable implementation of threshold Math updates and ChromaDB writes.

## 18. Known Implementation Limitations
- Formal Learning Agent quantitative accuracy evaluation is missing.
- Risk Tier Accuracy comparison against a ground truth dataset is not implemented in code.
- Continuous end-to-end runs are required to establish an accurate runtime CPL and SVR; previous gapped runs invalidated Prometheus counters.

## 19. Hardcoded Configuration / Deployment Limitations
- **ChromaDB Path:** `chromadb_utils/client.py` uses an absolute/relative path combo that assumes the current working directory structure.
- **RabbitMQ Host:** `layer2/rabbitmq/connection.py` hardcodes the default host to `stream-node`.
- **Ollama Host:** `layer2/ollama/client.py` hardcodes `localhost:11434`.
- **Deployment:** The Node 2 IP `192.168.18.102` is statically tied to the Layer 2 documentation context.

## 20. Cross-Layer Contracts
- **Layer 1 to Layer 2:** 
  - Structural schema drift events arrive with `anomaly_type="schema_drift"`.
  - Fused events arrive **without** an `anomaly_type`. Triage Agent bridges this contract by dynamically parsing `contributing_models` to establish a classification.
- **Layer 2 to Layer 3:**
  - Policy Agent guarantees a strict, schema-validated route decision out to `auto.execute` or `hitl.queue`.

## 21. Current Implementation Status
The implementation reflects an asynchronous multi-agent system where a rule-based Triage Agent fetches RAG context, an LLM Strategy Agent generates JSON, and a deterministic Policy Agent enforces routing boundaries.