# Project User Guide — Complete Pipeline Operation

**Project:** Distributed Multi-Agent Coordination for Self-Healing Data Pipelines
**Team:** Muhammad Adeel (23JZBCS0226) & Muhammad Asim (23JZBCS0227)
**Supervisor:** Dr. Laeeq Ahmed
**Last updated:** 20 August 2026

This guide describes the procedure for starting, operating, and monitoring the complete three-node self-healing pipeline. For component-level detail, refer to the layer-specific user guides located in `layer1/`, `layer2/`, and `layer3/`.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Quickstart (Full Pipeline)](#3-quickstart-full-pipeline)
4. [Layer-by-Layer Operations](#4-layer-by-layer-operations)
   - [Layer 1 – Data Plane (stream-node)](#layer1--data-plane-stream-node)
   - [Layer 2 – AI Control Plane (ai-brain-node)](#layer2--ai-control-plane-ai-brain-node)
   - [Layer 3 – HITL & Observability (gateway-node)](#layer3--hitl--observability-gateway-node)
5. [Full-System Evaluation Procedure](#5-full-system-evaluation-procedure)
6. [Monitoring & Dashboards](#6-monitoring--dashboards)
7. [Shutdown & Recovery](#7-shutdown--recovery)
8. [Key Files Reference](#8-key-files-reference)

---

## 1. Architecture Overview

```text
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  stream-node │      │ ai-brain-node│      │ gateway-node │
│  (Node 1)    │      │  (Node 2)    │      │  (Node 3)    │
├──────────────┤      ├──────────────┤      ├──────────────┤
│ SEG          │      │ Triage Agent │      │ HITL Dashboard│
│ Validator    │      │ Strategy Ag. │      │ Auto-Executor│
│ Feature Store│      │ Policy Agent │      │ SQLite Logger│
│ 5 Detectors  │      │ Learning Ag. │      │ Prometheus    │
│ Fusion Engine│      │ ChromaDB     │      │ Grafana       │
│ RabbitMQ     │      │ Ollama       │      │               │
└──────┬───────┘      └──────┬───────┘      └──────┬────────┘
       │                     │                     │
       └─────────────────────┼─────────────────────┘
                     Gigabit Ethernet
```

All inter-node communication is routed through RabbitMQ on Node 1. Ollama and ChromaDB run locally on Node 2. Prometheus scrapes metrics from all three nodes and feeds Grafana, which is hosted on Node 3.

---

## 2. Prerequisites

- All three nodes are powered on and reachable over the network.
- Static IPs are configured in `/etc/hosts` on each node:
  ```
  192.168.18.101  stream-node
  192.168.18.102  ai-brain-node
  192.168.18.103  gateway-node
  ```
- Passwordless SSH is functional in all six directions.
- RabbitMQ is running on Node 1, with the `fyp` vhost and all exchanges and queues declared.
- The Ollama models `qwen3:1.7b` and `qwen3:0.6b` have been pulled on Node 2.
- The ChromaDB collection `incident_history` has been initialised on Node 2.
- Prometheus and Grafana are installed on Node 3.
- Python virtual environments have been set up on each node, with all dependencies installed.
- For final evaluation, all nodes should be connected via **Gigabit Ethernet**, using the static IP addresses listed above.

### Verifying Cluster Readiness

```bash
# From any node
ping -c 2 stream-node
ping -c 2 ai-brain-node
ping -c 2 gateway-node
ssh stream-node "hostname"
ssh ai-brain-node "hostname"
ssh gateway-node "hostname"
```

---

## 3. Quickstart (Full Pipeline)

The fastest way to run a **smoke test** is to start all services and replay the corpus at accelerated speed.

> **For final evaluation**, use `--speed 1` and follow the procedure in Section 5.

### 3.1 Starting the Pipeline

**On stream-node (Node 1):**
```bash
cd ~/fyp-pipeline/layer1/validator && python3 validator.py &
cd ~/fyp-pipeline/layer1/adm && python3 adm_runner.py &
```

**On ai-brain-node (Node 2):**
```bash
cd ~/fyp-pipeline/layer2
python3 agents/triage_agent.py &
python3 agents/strategy_agent.py &
python3 agents/policy_agent.py &
python3 agents/learning_agent.py &
```

**On gateway-node (Node 3):**
```bash
cd ~/fyp-pipeline/layer3
python3 auto_executor/executor.py &
cd dashboard && python3 manage.py consume_hitl &
cd dashboard && python3 manage.py runserver 0.0.0.0:8000 &
sudo systemctl restart prometheus grafana-server
```

### 3.2 Replaying the Corpus (Smoke Test)

**On stream-node:**
```bash
cd ~/fyp-pipeline/layer1/seg
python3 seg.py --mode replay --speed 50 --input ../../evaluation/events_1950.jsonl
```

Then run the detectors **concurrently**, followed by the Fusion Engine:

```bash
cd ~/fyp-pipeline/layer1/adm
python3 detectors/error_rate.py &
python3 detectors/throughput_drop.py &
python3 detectors/auth_flood.py &
python3 detectors/cpu_spike.py &
python3 detectors/schema_drift.py &
wait

cd ~/fyp-pipeline/layer1/fusion_engine
python3 fusion_engine.py
```

### 3.3 Monitoring

| Check | Where |
|---|---|
| Queue depths | Script provided in Section 5.6 |
| Grafana dashboard | `http://192.168.18.103:3000` — **Hybrid Agentic Framework — System Observability** |
| HITL Dashboard | `http://192.168.18.103:8000` |

The smoke test is complete once all queues have drained.

---

## 4. Layer-by-Layer Operations

### Layer 1 – Data Plane (stream-node)

Refer to `layer1/User_Guide.md` for detailed setup instructions.

**Key commands:**
```bash
# Generate corpus
cd ~/fyp-pipeline/layer1/seg
python3 seg.py --mode generate --output ../../evaluation/

# Replay corpus
cd ~/fyp-pipeline/layer1/seg
python3 seg.py --mode replay --speed 1 --input ../../evaluation/events_1950.jsonl

# Run Validator
cd ~/fyp-pipeline/layer1/validator
python3 validator.py

# Run ADM Runner + Feature Store
cd ~/fyp-pipeline/layer1/adm
python3 adm_runner.py

# Run detectors concurrently
cd ~/fyp-pipeline/layer1/adm
python3 detectors/error_rate.py &
python3 detectors/throughput_drop.py &
python3 detectors/auth_flood.py &
python3 detectors/cpu_spike.py &
python3 detectors/schema_drift.py &
wait

# Run Fusion Engine
cd ~/fyp-pipeline/layer1/fusion_engine
python3 fusion_engine.py
```

### Layer 2 – AI Control Plane (ai-brain-node)

Refer to `layer2/User_Guide.md` for detailed setup instructions.

**Key commands:**
```bash
cd ~/fyp-pipeline/layer2
python3 agents/triage_agent.py        # port 8010
python3 agents/strategy_agent.py      # port 8011
python3 agents/policy_agent.py        # port 8012
python3 agents/learning_agent.py      # port 8013
```

**Checking status:**
```bash
# ChromaDB document count
python3 -c "from chromadb_utils.client import get_document_count; print(get_document_count())"

# EMA threshold
cat config/threshold_config.json

# Persistent agent logs
wc -l logs/*.jsonl
```

### Layer 3 – HITL & Observability (gateway-node)

Refer to `layer3/User_Guide.md` for detailed setup instructions.

**Key commands:**
```bash
cd ~/fyp-pipeline/layer3

# Auto-Executor
python3 auto_executor/executor.py

# HITL consumer
cd dashboard
python3 manage.py consume_hitl

# Django web server
python3 manage.py runserver 0.0.0.0:8000

# Prometheus & Grafana
sudo systemctl restart prometheus grafana-server
```

---

## 5. Full-System Evaluation Procedure

This section describes the complete procedure for conducting a **fresh, cold-start, real-time evaluation run**.

Use `--speed 1` for final, citable results. Use `--speed 50` only for smoke tests — under accelerated replay, MTTA/MTTR figures will be backlogged and invalid.

### 5.1 Full Cleanup

#### Node 1 — stream-node

**Purge RabbitMQ queues:**
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

**Delete Feature Store baselines and detector result files:**
```bash
rm -f ~/fyp-pipeline/layer1/adm/baselines/*.json
rm -f ~/fyp-pipeline/layer1/adm/error_results.jsonl
rm -f ~/fyp-pipeline/layer1/adm/throughput_results.jsonl
rm -f ~/fyp-pipeline/layer1/adm/auth_results.jsonl
rm -f ~/fyp-pipeline/layer1/adm/cpu_results.jsonl
rm -f ~/fyp-pipeline/layer1/adm/schema_results.jsonl
rm -f ~/fyp-pipeline/layer1/fusion_engine/fusion_results.jsonl
```

**Update base timestamp and regenerate the corpus:**
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

#### Node 2 — ai-brain-node

**Clear ChromaDB, reset the EMA threshold, and clear agent logs:**
```bash
cd ~/fyp-pipeline/layer2

rm -rf chromadb_data/*
rm -rf agents/chromadb_data/*
rm -f logs/*.jsonl

cat > config/threshold_config.json << 'EOF'
{
  "_comment": "EMA confidence threshold used by the Policy Agent for AUTO vs HITL routing. Hard bounds: [0.60, 0.90]. Reset for fresh evaluation.",
  "confidence_threshold": 0.65,
  "last_updated": "initialised",
  "update_count": 0,
  "ema_alpha": 0.9
}
EOF
```

#### Node 3 — gateway-node

**Clear the HITL dashboard and decision log:**
```bash
cd ~/fyp-pipeline/layer3

python3 -c "import sqlite3; conn = sqlite3.connect('/home/spectre/fyp-pipeline/layer3/sqlite_logger/decisions.db'); conn.execute('DELETE FROM hitl_hitlincident'); conn.execute('DELETE FROM decisions'); conn.commit(); conn.close(); print('HITL incidents and decision log cleared.')"
```

### 5.2 Start Layer 1 Services (Node 1)

**Terminal 1 — Validator:**
```bash
cd ~/fyp-pipeline/layer1/validator
python3 validator.py
```

**Terminal 2 — ADM Runner:**
```bash
cd ~/fyp-pipeline/layer1/adm
python3 adm_runner.py
```

### 5.3 Start Layer 2 Agents (Node 2)

In four separate terminals, start the agents in exactly this order:

```bash
cd ~/fyp-pipeline/layer2
python3 agents/triage_agent.py        # A
python3 agents/strategy_agent.py      # B
python3 agents/policy_agent.py        # C
python3 agents/learning_agent.py      # D
```

### 5.4 Start Layer 3 Services (Node 3)

**Terminal 1 — Auto-Executor:**
```bash
cd ~/fyp-pipeline/layer3
python3 auto_executor/executor.py
```

**Terminal 2 — HITL consumer:**
```bash
cd ~/fyp-pipeline/layer3/dashboard
python3 manage.py consume_hitl
```

**Terminal 3 — Django web server:**
```bash
cd ~/fyp-pipeline/layer3/dashboard
python3 manage.py runserver 0.0.0.0:8000
```

**Prometheus & Grafana:**
```bash
sudo systemctl restart prometheus grafana-server
```

### 5.5 Trigger the Replay (Node 1)

**Terminal 3 — Replay at real-time speed:**
```bash
cd ~/fyp-pipeline/layer1/seg
python3 seg.py --mode replay --speed 1 --input ../../evaluation/events_1950.jsonl
```

**Terminal 4 — Start the Fusion Engine before the detectors:**
```bash
cd ~/fyp-pipeline/layer1/fusion_engine
python3 fusion_engine.py
```

**Terminal 5 — Start all five detectors concurrently:**
```bash
cd ~/fyp-pipeline/layer1/adm

python3 detectors/error_rate.py &
python3 detectors/throughput_drop.py &
python3 detectors/auth_flood.py &
python3 detectors/cpu_spike.py &
python3 detectors/schema_drift.py &

wait
```

> **Why concurrent detectors?**
> Each detector publishes its result to `fusion.results` immediately upon completion. Running the detectors in parallel ensures that all five results for a given event arrive within milliseconds of one another, allowing the Fusion Engine to construct compound incidents correctly. Sequential execution would violate the 3-second correlation window.

Once the detectors have finished, allow `fusion.results` to drain and `anomaly.detected` to stabilise. If the Fusion Engine does not exit automatically, stop it with `Ctrl+C`.

### 5.6 Monitoring Progress

From any node:

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

Use the Grafana and HITL dashboards for real-time visibility into pipeline progress.

---

## 6. Monitoring & Dashboards

| Dashboard | URL | Credentials |
|---|---|---|
| Grafana — System Observability | `http://192.168.18.103:3000` | admin / set during Phase 0 |
| Prometheus targets | `http://192.168.18.103:9090/targets` | none |
| HITL Queue | `http://192.168.18.103:8000` | none |
| RabbitMQ Management | `http://stream-node:15672` | fyp_user / fyp_pass_2026 |

**Key metrics to monitor:**

- **Control-Plane Latency** — average processing time across Triage, Strategy, and Policy.
- **Strategy schema validity rate** — excludes timeouts.
- **Strategy timeout rate** — should remain low following the timeout increase to 35 s.
- **AUTO vs HITL routing ratio** — reflects auto-execution success rate.
- **Fusion suppression rate** — proportion of normal events filtered prior to Layer 2.
- **Compound detection rate** — reflects multi-detector incident merging.
- **EMA confidence threshold** — should converge as the Learning Agent continues to run.
- **ChromaDB document count** — should increase with every resolved incident.

---

## 7. Shutdown & Recovery

### Stopping the Pipeline Gracefully

1. Press `Ctrl+C` in each agent's terminal.
2. Agents complete processing of the current message before exiting; no message loss occurs.
3. Unprocessed messages remain in their respective RabbitMQ queues.
4. To resume operation, restart the stopped agents.

### Resetting for a Clean Rerun

1. Purge the RabbitMQ queues (see Section 5.1).
2. Delete `layer1/adm/baselines/*.json` to enable cold-start calibration.
3. Delete `layer2/chromadb_data/*` to reinitialise ChromaDB from scratch.
4. Delete `layer2/logs/*.jsonl` to clear the agent logs.
5. Clear the HITL incident table:
   ```bash
   cd ~/fyp-pipeline/layer3/dashboard
   python3 manage.py shell -c "from hitl.models import HitlIncident; HitlIncident.objects.all().delete()"
   ```

---

## 8. Key Files Reference

| File | Purpose |
|---|---|
| `README.md` | Project overview and research metrics |
| `USER_GUIDE.md` | This guide — full pipeline operation |
| `Full_Rerun.md` | Detailed final evaluation runbook |
| `layer1/User_Guide.md` | Layer 1 component startup and troubleshooting |
| `layer2/User_Guide.md` | Layer 2 agent startup and troubleshooting |
| `layer3/User_Guide.md` | Layer 3 HITL and observability startup |
| `docs/layer1_component_log.md` | Layer 1 build history and architecture decisions |
| `docs/layer2_component_log.md` | Layer 2 build history and architecture decisions |
| `docs/layer3_component_log.md` | Layer 3 build history and architecture decisions |
| `docs/Master_Reference_Document.md` | System design, agent contracts, and evaluation methodology |
| `evaluation/events_1950.jsonl` | 1,950-event synthetic corpus |
| `evaluation/labels.csv` | Ground-truth labels for evaluation |