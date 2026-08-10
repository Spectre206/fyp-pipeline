# Layer 3 — Component-by-Component Build Log

**Project:** Distributed Multi-Agent Coordination for Self-Healing Data Pipelines  
**Layer:** Layer 3 — HITL & Observability (Node 3, `gateway-node`)  
**Purpose:** Single running record of every Layer 3 component as it's implemented.

---

## 1. RabbitMQ Connection Helper

**Files:** `rabbitmq/connection.py`  
**Status:** ✅ v1.0 — Provides `get_connection()` and `publish()` for all Layer 3 components.

## 2. SQLite Decision Logger

**Files:** `sqlite_logger/logger.py`  
**Status:** ✅ v1.0 — `init_db()` creates the decisions table; `write_decision()` inserts rows. WAL mode for concurrent access by Auto‑Executor and Django.

## 3. Auto‑Execution Engine

**Files:** `auto_executor/executor.py`  
**Status:** ✅ **v1.0 – consumes auto.execute, simulates remediation, logs to SQLite, publishes outcome.feedback. Tested on full 114‑event queue.**

### 3.1 What it does

- Consumes every message from the `auto.execute` queue (placed there by the Policy Agent when risk_tier=LOW and confidence ≥ threshold).
- Extracts the three `recommended_actions` from the Strategy Agent’s LLM response.
- Simulates remediation (0.5 s sleep, all actions succeed for evaluation).
- Writes a decision record to the SQLite `decisions.db` via `sqlite_logger`.
- Builds an `outcome.feedback` payload and publishes it to the `outcome.feedback` queue for the Learning Agent.
- Acknowledges the message after successful processing.

### 3.2 Flow

```mermaid
flowchart TD
    A[auto.execute queue] --> B[Receive policy result]
    B --> C[Extract recommended_actions<br/>from LLM response]
    C --> D[Simulate execution<br/>(0.5s sleep, all successes)]
    D --> E[Write decision row<br/>to SQLite via sqlite_logger]
    E --> F[Build outcome.feedback payload<br/>outcome_type, actions, resolution_ms]
    F --> G[Publish to outcome.feedback queue]
    G --> H[Acknowledge message]
```

### 3.3 Test results (full 114‑event run)

| Metric | Value |
|---|---|
| Messages consumed | 114 / 114 |
| Outcome type | AUTO_EXECUTE_SUCCESS (100%) |
| SQLite rows (total) | 115 (1 initial test + 114 real) |
| `outcome.feedback` messages published | 114 |
| Learning Agent response | Consumed all 114, ChromaDB → 112 documents, EMA threshold 0.65 → 0.80 |

### 3.4 Open items

- Currently all simulated executions succeed. Failure injection (e.g., simulate a failed remediation) can be added later to test the Learning Agent’s negative‑example logic.
- The `node` and `affected_component` fields in early ChromaDB documents show `unknown` (fixed in Learning Agent v1.1). Collection will be purged before final evaluation run.

```

