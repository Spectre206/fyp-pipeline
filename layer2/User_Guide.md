# Layer 2 User Guide — `ai-brain-node` (192.168.18.102)

This guide describes the procedure for operating the complete **AI Control Plane** on Node 2.

> **Prerequisite:** Layer 1 must be fully operational — all exchanges and queues declared on `stream-node`, with the Fusion Engine publishing to `anomaly.detected`.

---

## 1. Prerequisites Checklist

On `ai-brain-node`, verify the following before starting any agent.

**Hostname**

```bash
hostname          # must return "ai-brain-node"
```

**RabbitMQ (on stream-node) reachable**

```bash
python3 -c "
from rabbitmq.connection import get_connection
conn = get_connection()
ch = conn.channel()
print('OK')
conn.close()
"
```

**Ollama running with required models**

```bash
ollama list | grep qwen3
# Expected: qwen3:1.7b and qwen3:0.6b
```

**ChromaDB collection exists** (cold start is acceptable)

```bash
python3 -c "from chromadb_utils.client import get_collection; print(get_collection().count())"
```

**`/etc/hosts` cluster mapping** (identical to Node 1)

```bash
grep "192.168.18" /etc/hosts
```

---

## 2. Python Environment

```bash
cd ~/fyp-pipeline/layer2
source .venv/bin/activate   # if not auto-activated
```

The virtual environment includes `pika`, `chromadb`, `sentence-transformers`, `ollama`, `prometheus-client`, and related dependencies. If any package is missing, re-run:

```bash
pip install -r requirements_node2.txt
```

---

## 3. Layer 2 Data Flow

```mermaid
flowchart LR
    A[anomaly.detected] --> B[Triage Agent<br/>Rule-based + RAG]
    B -->|triage.result| C[Strategy Agent<br/>qwen3:1.7b via Ollama]
    C -->|strategy.result| D[Policy Agent<br/>5-rule routing table]
    D -->|risk_tier LOW<br/>+ high confidence| E[auto.execute]
    D -->|HIGH risk / timeout / low confidence| F[hitl.queue]

    E --> G[Layer 3: Auto-Executor]
    F --> H[Layer 3: HITL Dashboard]

    G -->|outcome.feedback| I[Learning Agent<br/>qwen3:0.6b]
    H -->|outcome.feedback| I

    I --> J[(ChromaDB<br/>incident_history)]
    I --> K[config/<br/>threshold_config.json]

    B -.->|RAG query| J
    C -.->|LLM call| L[Ollama API<br/>localhost:11434]
    I -.->|LLM call| L
```

**Pipeline:** `anomaly.detected` → Triage Agent → `triage.result` → Strategy Agent (qwen3:1.7b) → `strategy.result` → Policy Agent → `auto.execute` or `hitl.queue`

**Feedback loop:** `outcome.feedback` → Learning Agent (qwen3:0.6b) → ChromaDB upsert + EMA threshold update

All agents connect to RabbitMQ on `stream-node`; Ollama and ChromaDB run locally on `ai-brain-node`.

---

## 4. Startup Order

Agents must always be started in the following sequence:

| Order | Agent | Command (from `layer2/`) | Port |
|:-----:|-------|---------------------------|:----:|
| 1 | Triage Agent | `python3 agents/triage_agent.py` | 8010 |
| 2 | Strategy Agent | `python3 agents/strategy_agent.py` | 8011 |
| 3 | Policy Agent | `python3 agents/policy_agent.py` | 8012 |
| 4 | Learning Agent | `python3 agents/learning_agent.py` | 8013 |

- The Triage Agent must start first, as it produces `triage.result` for the Strategy Agent.
- The Learning Agent may be started at any point — it simply awaits `outcome.feedback`.

---

## 5. Running Each Agent

### 5.1 Triage Agent

```bash
cd ~/fyp-pipeline/layer2
python3 agents/triage_agent.py
```

**Expected output:**
```
triage_agent_started
triage_consuming queue=anomaly.detected
triage_complete event_id=... protocol=... rag_docs=... latency_ms=...
```

| Note | Detail |
|---|---|
| Idle behavior | If `anomaly.detected` is empty, the agent waits silently |
| Latency | Steady-state latency below 5 ms per event |
| Cold start | On ChromaDB cold start (0 documents), RAG context is empty; this is expected behavior |
| Persistent log | Writes one JSON line per event to `logs/triage_agent.jsonl` |

### 5.2 Strategy Agent

```bash
python3 agents/strategy_agent.py
```

**Expected output:**
```
strategy_agent_started model=qwen3:1.7b
strategy_consuming queue=triage.result model=qwen3:1.7b
strategy_complete event_id=... schema_valid=True latency_ms=...
```

| Note | Detail |
|---|---|
| First inference | May require 25–30 s; subsequent calls typically take 20–25 s |
| Timeout | Set to 35 s. If exceeded, `timed_out=True` is recorded and the event still proceeds to `strategy.result` |
| Metrics | Prometheus metrics exposed on port 8011 |
| JSON parsing | Strips markdown code fences and extracts the first complete JSON object, reducing parsing errors |
| Persistent log | Writes one JSON line per event to `logs/strategy_agent.jsonl` |
| Parse error log | On JSON parsing failure, the raw response is saved to `logs/parse_error.jsonl` |

### 5.3 Policy Agent

```bash
python3 agents/policy_agent.py
```

**Expected output:**
```
policy_agent_started
policy_consuming queue=strategy.result
policy_routed event_id=... decision=AUTO reason=LOW_RISK_HIGH_CONFIDENCE
```

| Note | Detail |
|---|---|
| Latency | Sub-millisecond per message |
| Configuration | Loads the confidence threshold from `config/threshold_config.json` on every message |
| Routing | Routes to `auto.execute` if `risk_tier=LOW` **and** confidence ≥ threshold; otherwise routes to `hitl.queue` |
| MTTA | Records `policy_timestamp − triage_timestamp` as the control-plane MTTA |
| Persistent log | Writes one JSON line per event to `logs/policy_agent.jsonl` |

### 5.4 Learning Agent

```bash
python3 agents/learning_agent.py
```

**Expected output:**
```
learning_agent_started model=qwen3:0.6b
learning_consuming queue=outcome.feedback
learning_complete event_id=... outcome=AUTO_EXECUTE_SUCCESS
```

| Note | Detail |
|---|---|
| Impact | Executes post-dispatch, with zero impact on the main pipeline |
| Summarization | Invokes qwen3:0.6b (10 s timeout); falls back to a default summary if the LLM call fails |
| ChromaDB | Upserts the incident into the `incident_history` collection |
| Threshold update | Updates the EMA confidence threshold in `config/threshold_config.json` (bounded to `[0.60, 0.90]`) |
| MTTR | Records `outcome_feedback_time − triage_timestamp` as the control-plane MTTR |
| Persistent log | Writes one JSON line per event to `logs/learning_agent.jsonl` |

---

## 6. Verification

### 6.1 Queue Depths

From any node with RabbitMQ access:

```bash
python3 -c "
from rabbitmq.connection import get_connection
conn = get_connection(); ch = conn.channel()
for q in ['anomaly.detected','triage.result','strategy.result','auto.execute','hitl.queue','outcome.feedback']:
    r = ch.queue_declare(q, passive=True)
    print(f'{q}: {r.method.message_count}')
conn.close()
"
```

### 6.2 ChromaDB Document Count

```bash
python3 -c "from chromadb_utils.client import get_document_count; print(get_document_count())"
```

### 6.3 EMA Threshold

```bash
cat config/threshold_config.json
```

### 6.4 Prometheus Metrics

```bash
curl -s http://localhost:8010/metrics | head   # Triage
curl -s http://localhost:8011/metrics | head   # Strategy
curl -s http://localhost:8012/metrics | head   # Policy
curl -s http://localhost:8013/metrics | head   # Learning
```

Gateway-node's Prometheus instance scrapes these ports automatically.

### 6.5 Persistent Agent Logs

All agents write one JSON line per processed event to `layer2/logs/`. These logs persist across restarts and serve as the authoritative source for cumulative counts when the pipeline is run across multiple sessions.

```bash
cd ~/fyp-pipeline/layer2

# Count processed events per agent
wc -l logs/*.jsonl

# Inspect parse errors
cat logs/parse_error.jsonl

# View last strategy outcome
tail -1 logs/strategy_agent.jsonl
```

---

## 7. Stopping Agents

Press `Ctrl + C` in each agent's terminal.

- The current message is acknowledged **only after** the result has been published, ensuring no message loss.
- Unprocessed messages remain in their respective queues for the next startup.

---

## 8. Full Pipeline Test

1. **Node 1:** Confirm the Fusion Engine is running (along with all Layer 1 components, if re-running the full corpus).
2. **Node 2:** Start the Triage, Strategy, Policy, and Learning agents, in that order (sequence is important).
3. **Node 3:** Start the Auto-Executor and the HITL consumer.
4. **Node 1:** Replay the corpus:
   ```bash
   cd ~/fyp-pipeline/layer1/seg
   python3 seg.py --mode replay --speed 1 --input ../../evaluation/events_1950.jsonl
   ```
   Use `--speed 1` for final evaluation. Use `--speed 50` only for smoke tests.
5. Monitor the queues, persistent logs, and the Grafana dashboard.

---

## 9. Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'rabbitmq'` | Running from the wrong directory | Run from `layer2/`, not from within `agents/` |
| ChromaDB hangs on startup | Internet access required to verify the sentence-transformers model | Set `HF_HUB_OFFLINE=1` (already configured in `chromadb_utils/client.py`) or ensure a local cache exists |
| `Failed to send telemetry event ClientStartEvent` | Harmless ChromaDB telemetry warning | Ignore, or set `ANONYMIZED_TELEMETRY=False` in `.env` |
| Strategy Agent timeouts exceed 20% | Complex prompts or memory (RAM) pressure | Timeout is fixed at 35 s; if the issue persists, stop the Learning Agent to free approximately 400 MB, or restart Ollama |
| `auto.execute` remains empty | All events classified as HIGH-risk or confidence below threshold | Check the EMA threshold; temporarily lower it to 0.55 for testing, or allow the Learning Agent time to adjust it |
| RabbitMQ connection refused | `stream-node` unreachable or RabbitMQ service down | `ping stream-node`; `ssh stream-node "sudo systemctl restart rabbitmq-server"` |
| ChromaDB documents show `unknown` fields | Legacy data predating the Learning Agent fix | Purely cosmetic; similarity search remains unaffected. Purge the collection before final evaluation if required |
| `ai-brain-node:8010` shown as down in Prometheus | Corresponding agent not running | Start the relevant agent |

---

## 10. Directory Reference

```
layer2/
├── agents/               # triage, strategy, policy, learning
├── chromadb_utils/        # client, query, upsert
├── ollama/                # HTTP client for Ollama
├── rabbitmq/              # connection helper
├── utils/                 # shared file logger
├── logs/                  # runtime JSONL logs (ignored by Git)
├── prompts/               # system prompts for qwen3 models
├── config/                # threshold_config.json
├── chromadb_data/         # persistent ChromaDB store (do not delete)
├── .env                   # environment variables
└── requirements_node2.txt
```

For detailed component-by-component build history, refer to `docs/layer2_component_log.md`.