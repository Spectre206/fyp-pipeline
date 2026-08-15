

```markdown
# Final Evaluation Run — Full System Procedure

**Project:** Distributed Multi-Agent Coordination for Self-Healing Data Pipelines  
**Approach:** Human-in-the-Loop on Commodity Hardware

---

## Prerequisites

- All three nodes powered on and reachable.
- RabbitMQ running on `stream-node` (Node 1).
- Ollama running on `ai-brain-node` (Node 2).
- Prometheus & Grafana running on `gateway-node` (Node 3).
- (Optional) Ethernet switch connected for final citable benchmarks.

> **Replay speed:**  
> - Use `--speed 1` for final evaluation (real-time, valid MTTA/MTTR).  
> - Use `--speed 50` for quick smoke tests only (MTTA/MTTR will be backlogged).

---

## Phase 0 — Full Cleanup

### Node 1 — stream-node

#### 1. Purge RabbitMQ queues

```bash
sudo rabbitmqctl purge_queue raw.events -p fyp
sudo rabbitmqctl purge_queue validated.event -p fyp
sudo rabbitmqctl purge_queue detect.cpu -p fyp
sudo rabbitmqctl purge_queue detect.error -p fyp
sudo rabbitmqctl purge_queue detect.throughput -p fyp
sudo rabbitmqctl purge_queue detect.auth -p fyp
sudo rabbitmqctl purge_queue detect.schema -p fyp
sudo rabbitmqctl purge_queue fusion.results -p fyp
sudo rabbitmqctl purge_queue anomaly.detected -p fyp
sudo rabbitmqctl purge_queue triage.result -p fyp
sudo rabbitmqctl purge_queue strategy.result -p fyp
sudo rabbitmqctl purge_queue auto.execute -p fyp
sudo rabbitmqctl purge_queue hitl.queue -p fyp
sudo rabbitmqctl purge_queue outcome.feedback -p fyp
sudo rabbitmqctl purge_queue dead.letters -p fyp
```

#### 2. Delete Feature Store baselines and detector results

```bash
rm -f ~/fyp-pipeline/layer1/adm/baselines/*.json
rm -f ~/fyp-pipeline/layer1/adm/error_results.jsonl
rm -f ~/fyp-pipeline/layer1/adm/throughput_results.jsonl
rm -f ~/fyp-pipeline/layer1/adm/auth_results.jsonl
rm -f ~/fyp-pipeline/layer1/adm/cpu_results.jsonl
rm -f ~/fyp-pipeline/layer1/adm/schema_results.jsonl
rm -f ~/fyp-pipeline/layer1/fusion_engine/fusion_results.jsonl
```

#### 3. Update base timestamp and regenerate corpus

```bash
cd ~/fyp-pipeline/layer1/seg

python3 -c "
import json
from datetime import datetime, timezone
cfg = json.load(open('config/seg_config.json'))
cfg['base_timestamp'] = datetime.now(timezone.utc).isoformat()
json.dump(cfg, open('config/seg_config.json','w'), indent=2)
print('base_timestamp =', cfg['base_timestamp'])
"

python3 seg.py --mode generate --output ../../evaluation/
```

### Node 2 — ai-brain-node

#### 4. Clear ChromaDB and reset EMA threshold

```bash
cd ~/fyp-pipeline/layer2

rm -rf chromadb_data/*
rm -rf agents/chromadb_data/*   # safety: remove stray copy if present

cat > config/threshold_config.json << 'EOF'
{
  "_comment": "EMA confidence threshold used by the Policy Agent for AUTO vs HITL routing. Hard bounds: [0.60, 0.90]. Reset for fresh evaluation.",
  "confidence_threshold": 0.65,
  "last_updated": "initialised",
  "update_count": 0,
  "ema_alpha": 0.9
}
EOF

echo "ChromaDB cleared and threshold reset."
```

### Node 3 — gateway-node

#### 5. Clear HITL dashboard and decision log

```bash
cd ~/fyp-pipeline/layer3

python3 -c "import sqlite3; conn = sqlite3.connect('/home/spectre/fyp-pipeline/layer3/sqlite_logger/decisions.db'); conn.execute('DELETE FROM hitl_hitlincident'); conn.execute('DELETE FROM decisions'); conn.commit(); conn.close(); print('HITL incidents and decision log cleared.')"
```

---

## Phase 1 — Start Layer 1 (Node 1)

### 6. Start Validator

```bash
cd ~/fyp-pipeline/layer1/validator
python3 validator.py
```

### 7. Start ADM Runner

```bash
cd ~/fyp-pipeline/layer1/adm
python3 adm_runner.py
```

---

## Phase 2 — Start Layer 2 Agents (Node 2)

Start each agent in a separate terminal, in exactly this order:

### Terminal A — Triage Agent

```bash
cd ~/fyp-pipeline/layer2
python3 agents/triage_agent.py
```

### Terminal B — Strategy Agent

```bash
cd ~/fyp-pipeline/layer2
python3 agents/strategy_agent.py
```

### Terminal C — Policy Agent

```bash
cd ~/fyp-pipeline/layer2
python3 agents/policy_agent.py
```

### Terminal D — Learning Agent

```bash
cd ~/fyp-pipeline/layer2
python3 agents/learning_agent.py
```

---

## Phase 3 — Start Layer 3 Components (Node 3)

### 9. Start Auto‑Executor

```bash
cd ~/fyp-pipeline/layer3
python3 auto_executor/executor.py
```

### 10. Start HITL consumer

```bash
cd ~/fyp-pipeline/layer3/dashboard
python3 manage.py consume_hitl
```

### 11. Start Django web server

```bash
cd ~/fyp-pipeline/layer3/dashboard
python3 manage.py runserver 0.0.0.0:8000
```

### 12. Ensure Prometheus and Grafana are running

```bash
sudo systemctl restart prometheus grafana-server
```

Open `http://192.168.18.103:3000` → load **“Hybrid Agentic Framework — System Observability”**.

---

## Phase 4 — Replay Corpus (Node 1)

### 13. Replay at real-time speed

```bash
cd ~/fyp-pipeline/layer1/seg
python3 seg.py --mode replay --speed 1 --input ../../evaluation/events_1950.jsonl
```

Wait for replay to finish (~32 minutes for 1,950 events).

### 14. Run the five detectors (sequential)

```bash
cd ~/fyp-pipeline/layer1/adm
python3 detectors/error_rate.py
python3 detectors/throughput_drop.py
python3 detectors/auth_flood.py
python3 detectors/cpu_spike.py
python3 detectors/schema_drift.py
```

### 15. Start Fusion Engine

```bash
cd ~/fyp-pipeline/layer1/fusion_engine
python3 fusion_engine.py
```

---

## Phase 5 — Monitor & Interact

### Watch queue depths

```bash
python3 -c "
import sys; sys.path.insert(0,'/home/spectre/fyp-pipeline/layer3')
from rabbitmq.connection import get_connection
conn=get_connection(); ch=conn.channel()
for q in ['anomaly.detected','triage.result','strategy.result','auto.execute','hitl.queue','outcome.feedback']:
    r=ch.queue_declare(q,passive=True)
    print(f'{q}: {r.method.message_count}')
conn.close()
"
```

### HITL Dashboard

Open `http://192.168.18.103:8000`  
Approve / Reject / Modify a few incidents to exercise the full feedback loop.

### Grafana

Open `http://192.168.18.103:3000`  
Watch **“Hybrid Agentic Framework — System Observability”** dashboard.  
Key panels: Control-Plane Latency, MTTA/MTTR, Strategy Outcome Counts, Auto Executor Success Rate, RabbitMQ Queue Depth.

---

## Phase 6 — Post-Run Checks

After all queues drain (allow time for HITL and Learning).

### On ai-brain-node

```bash
python3 -c "from chromadb_utils.client import get_document_count; print(get_document_count())"
cat config/threshold_config.json
```

### On gateway-node

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('sqlite_logger/decisions.db')
rows = conn.execute('SELECT decision_type, COUNT(*) FROM decisions GROUP BY decision_type').fetchall()
for r in rows: print(r[0], r[1])
conn.close()
"
```

### Prometheus key queries

**MTTA p50 / p95**

```promql
histogram_quantile(0.5, rate(fyp_mtta_seconds_bucket[5m]))
histogram_quantile(0.95, rate(fyp_mtta_seconds_bucket[5m]))
```

**MTTR p50 / p95**

```promql
histogram_quantile(0.5, rate(fyp_mttr_seconds_bucket[5m]))
histogram_quantile(0.95, rate(fyp_mttr_seconds_bucket[5m]))
```

**Control-Plane Latency**

```promql
(sum(fyp_triage_latency_s_sum)/sum(fyp_triage_latency_s_count)) +
(sum(fyp_strategy_latency_s_sum)/sum(fyp_strategy_latency_s_count)) +
(sum(fyp_policy_latency_s_sum)/sum(fyp_policy_latency_s_count))
```

---

## Phase 7 — Shutdown

- Press `Ctrl+C` in each agent terminal.
- Prometheus/Grafana can stay running for monitoring.
- Commit results and dashboard JSON to Git.
```

This Markdown is clean and copy‑safe. Every script block is inside a code fence, and here‑doc delimiters are placed at the beginning of the line as required. You can save it in your repo and reuse it for all final runs.