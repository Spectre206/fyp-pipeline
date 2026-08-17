# Project User Guide — Complete Pipeline Operation

**Project:** Distributed Multi-Agent Coordination for Self-Healing Data Pipelines
**Team:** Muhammad Adeel (23JZBCS0226) & Muhammad Asim (23JZBCS0227)
**Supervisor:** Dr. Laeeq Ahmed
**Last updated:** 12 August 2026

This guide covers starting, operating, and monitoring the full three-node self-healing pipeline. For per-node details, see the Layer-specific User Guides inside `layer1/`, `layer2/`, and `layer3/`.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [Quickstart (Full Pipeline)](#3-quickstart-full-pipeline)
4. [Layer-by-Layer Operations](#4-layer-by-layer-operations)
   - [Layer 1 – Data Plane (stream-node)](#layer-1--data-plane-stream-node)
   - [Layer 2 – AI Control Plane (ai-brain-node)](#layer-2--ai-control-plane-ai-brain-node)
   - [Layer 3 – HITL & Observability (gateway-node)](#layer-3--hitl--observability-gateway-node)
5. [Full-System Rerun Procedure](#5-full-system-rerun-procedure)
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

All inter-node communication goes through RabbitMQ on Node 1.
Ollama and ChromaDB run locally on Node 2.
Prometheus scrapes metrics from all three nodes and feeds Grafana on Node 3.

---

## 2. Prerequisites

- All three nodes powered on and network reachable.
- Static IPs configured (see `/etc/hosts` on each node):
  ```
  192.168.18.101  stream-node
  192.168.18.102  ai-brain-node
  192.168.18.103  gateway-node
  ```
- Passwordless SSH working in all directions (six combinations).
- RabbitMQ running on Node 1 with the `fyp` vhost and all exchanges/queues declared.
- Ollama models `qwen3:1.7b` and `qwen3:0.6b` pulled on Node 2.
- ChromaDB collection `incident_history` initialised on Node 2.
- Prometheus and Grafana installed on Node 3.
- Python virtual environments set up on each node with dependencies installed.

**Verify the cluster is ready:**

```bash
# From any node:
ping -c 2 stream-node
ping -c 2 ai-brain-node
ping -c 2 gateway-node
ssh stream-node "hostname"
ssh ai-brain-node "hostname"
ssh gateway-node "hostname"
```

---

## 3. Quickstart (Full Pipeline)

The quickest way to run the entire pipeline is to start all services and then replay the 1,950-event evaluation corpus from Node 1.

### 3.1 Start the Pipeline (All Nodes)

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
# Prometheus & Grafana usually already running
sudo systemctl restart prometheus grafana-server
```

### 3.2 Replay the Corpus

**On stream-node:**
```bash
cd ~/fyp-pipeline/layer1/seg
python3 seg.py --mode replay --speed 50 --input ../../evaluation/events_1950.jsonl
```

Wait for the replay to finish (~30 s). Then run the detectors and Fusion Engine:

```bash
cd ~/fyp-pipeline/layer1/adm
for det in error_rate throughput_drop auth_flood cpu_spike schema_drift; do
    python3 detectors/${det}.py
done
cd ~/fyp-pipeline/layer1/fusion_engine
python3 fusion_engine.py
```

### 3.3 Monitor

| Check | Where |
|---|---|
| Queue depths | Run the script in Section 5.6 |
| Grafana dashboard | `http://192.168.18.103:3000` (Agent Pipeline & Fusion Engine Performance) |
| HITL Dashboard | `http://192.168.18.103:8000` |

When all queues drain, the run is complete.

---

## 4. Layer-by-Layer Operations

### Layer 1 – Data Plane (stream-node)

Refer to `layer1/User_Guide.md` for detailed setup.

**Key commands:**
```bash
# Generate corpus (once)
cd ~/fyp-pipeline/layer1/seg
python3 seg.py --mode generate --output ../../evaluation/

# Replay corpus
cd ~/fyp-pipeline/layer1/seg
python3 seg.py --mode replay --speed 50 --input ../../evaluation/events_1950.jsonl

# Run Validator
cd ~/fyp-pipeline/layer1/validator
python3 validator.py

# Run ADM Runner + Feature Store
cd ~/fyp-pipeline/layer1/adm
python3 adm_runner.py

# Run detectors (any order)
cd ~/fyp-pipeline/layer1/adm
python3 detectors/error_rate.py
python3 detectors/throughput_drop.py
python3 detectors/auth_flood.py
python3 detectors/cpu_spike.py
python3 detectors/schema_drift.py

# Run Fusion Engine
cd ~/fyp-pipeline/layer1/fusion_engine
python3 fusion_engine.py
```

### Layer 2 – AI Control Plane (ai-brain-node)

Refer to `layer2/User_Guide.md` for detailed setup.

**Key commands:**
```bash
cd ~/fyp-pipeline/layer2
python3 agents/triage_agent.py        # port 8010
python3 agents/strategy_agent.py      # port 8011
python3 agents/policy_agent.py        # port 8012
python3 agents/learning_agent.py      # port 8013
```

**Check status:**
```bash
# ChromaDB document count
python3 -c "from chromadb_utils.client import get_document_count; print(get_document_count())"

# EMA threshold
cat config/threshold_config.json
```

### Layer 3 – HITL & Observability (gateway-node)

Refer to `layer3/User_Guide.md` for detailed setup.

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

# Prometheus & Grafana (usually already running)
sudo systemctl restart prometheus grafana-server
```

---

## 5. Full-System Rerun Procedure

This is the complete procedure for a fresh evaluation run (cold-start).

### 5.1 Preparation (Node 1)

```bash
# Purge all queues
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

# Delete cold-start baselines
rm -f ~/fyp-pipeline/layer1/adm/baselines/*.json
```

### 5.2 Start Layer 1 Services (Node 1)

**Terminal 1:**
```bash
cd ~/fyp-pipeline/layer1/validator && python3 validator.py
```

**Terminal 2:**
```bash
cd ~/fyp-pipeline/layer1/adm && python3 adm_runner.py
```

### 5.3 Start Layer 2 Agents (Node 2)

In four separate terminals:

```bash
cd ~/fyp-pipeline/layer2
python3 agents/triage_agent.py
python3 agents/strategy_agent.py
python3 agents/policy_agent.py
python3 agents/learning_agent.py
```

### 5.4 Start Layer 3 Services (Node 3)

**Terminal 1:**
```bash
cd ~/fyp-pipeline/layer3 && python3 auto_executor/executor.py
```

**Terminal 2:**
```bash
cd ~/fyp-pipeline/layer3/dashboard && python3 manage.py consume_hitl
```

**Terminal 3:**
```bash
cd ~/fyp-pipeline/layer3/dashboard && python3 manage.py runserver 0.0.0.0:8000
```

**Prometheus & Grafana:**
```bash
sudo systemctl restart prometheus grafana-server
```

### 5.5 Trigger the Replay (Node 1)

**Terminal 3:**
```bash
cd ~/fyp-pipeline/layer1/seg
python3 seg.py --mode replay --speed 50 --input ../../evaluation/events_1950.jsonl
```

After replay finishes, run detectors (**Terminal 4**):
```bash
cd ~/fyp-pipeline/layer1/adm
for det in error_rate throughput_drop auth_flood cpu_spike schema_drift; do
    python3 detectors/${det}.py
done
```

Then start Fusion Engine (**Terminal 5**):
```bash
cd ~/fyp-pipeline/layer1/fusion_engine && python3 fusion_engine.py
```

### 5.6 Monitor Progress

On any node, run:
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

Use the Grafana dashboard (`http://192.168.18.103:3000`) and the HITL Dashboard (`http://192.168.18.103:8000`) for real-time visibility.

---

## 6. Monitoring & Dashboards

| Dashboard | URL | Credentials |
|---|---|---|
| Grafana (Agent Pipeline) | `http://192.168.18.103:3000` | admin / (set during Phase 0) |
| Prometheus targets | `http://192.168.18.103:9090/targets` | none |
| HITL Queue | `http://192.168.18.103:8000` | none |
| RabbitMQ Management | `http://stream-node:15672` | fyp_user / fyp_pass_2026 |

**Key metrics to watch:**

- **Strategy Agent latency** (target < 35 s)
- **Schema validity rate** (target ≥ 95%)
- **Auto vs HITL routing ratio** (routing decision pie chart)
- **Fusion Engine suppression rate** (normal events filtered before Layer 2)
- **EMA confidence threshold** (should converge over time)
- **ChromaDB document count** (growing with each resolved incident)

---

## 7. Shutdown & Recovery

**To stop the pipeline gracefully:**
1. Press `Ctrl + C` in each agent terminal (agents finish the current message before exiting).
2. Queued messages remain in RabbitMQ and are not lost.
3. To resume, simply restart the agents — they will pick up where they left off.

**To reset everything for a clean rerun:**
1. Purge RabbitMQ queues (see Section 5.1).
2. Delete `layer1/adm/baselines/*.json` for cold-start calibration.
3. *(Optional)* Delete `layer2/chromadb_data/` to start ChromaDB from scratch.
4. *(Optional)* Clear the HITL incident table:
   ```bash
   cd ~/fyp-pipeline/layer3/dashboard
   python3 manage.py shell -c "from hitl.models import HitlIncident; HitlIncident.objects.all().delete()"
   ```

---

## 8. Key Files Reference

| File | Purpose |
|---|---|
| `layer1/User_Guide.md` | Layer 1 component startup & troubleshooting |
| `layer2/User_Guide.md` | Layer 2 agent startup & troubleshooting |
| `layer3/User_Guide.md` | Layer 3 HITL & observability startup |
| `docs/layer1_component_log.md` | Layer 1 build history & architecture decisions |
| `docs/layer2_component_log.md` | Layer 2 build history & architecture decisions |
| `docs/layer3_component_log.md` | Layer 3 build history & architecture decisions |
| `docs/Master_Reference_Document.md` | System design v1.2, agent contracts, evaluation methodology |
| `full_rerun_procedure.txt` | Standalone rerun checklist (this document's Section 5) |
| `evaluation/events_1950.jsonl` | 1,950-event synthetic corpus |
| `evaluation/labels.csv` | Ground-truth labels for evaluation |