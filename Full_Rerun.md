# Final Evaluation Run — Current Cold-System Procedure

**Project:** Distributed Multi-Agent Coordination for Self-Healing Data Pipelines
**Purpose:** reproducible Wi-Fi or Ethernet experiment with a cold Layer 1 Feature Store, cold Layer 2 ChromaDB, reset EMA state, and a fresh Layer 2 evaluation run.

This is the single operational runbook for the current implementation. Run the same checked-out commit on all three nodes. Commands use `~/fyp-pipeline`; set `REPO` differently only if the repository is located elsewhere.

> **Important:** Stop every existing pipeline consumer before Phase 0. A cold run resets process-level metrics by starting fresh processes. It resets only disposable runtime state; it does not remove prior experiment directories, historical evaluation material, source corpus definitions, labels, or tracked files.

## Prerequisites

- **Node 1 — `stream-node`:** Layer 1 — Real-Time Statistical Data Plane, RabbitMQ, and the SEG replay client.
- **Node 2 — `ai-brain-node`:** Layer 2 — AI Control Plane and Ollama.
- **Node 3 — `gateway-node`:** Layer 3 — Execution, Human Oversight & Observability Layer, Prometheus, and Grafana.
- The three nodes resolve the names above and use the same RabbitMQ vhost, `fyp`.
- Dependencies are already installed on each node. Do not install or upgrade packages during a benchmark.
- Record the network medium for each run: `Wi-Fi` or `Ethernet`. The code, corpus, replay speed, and analysis procedure otherwise remain the same.

For a final comparable run, use replay speed `1`. It preserves the corpus arrival-rate scale. Higher values are useful only for a diagnostic because they deliberately increase arrival rate, can build queues, and can alter End-to-End Decision Latency.

## Permanent per-node environment

On every node, add this once to `~/.bashrc`, then open a new shell or run `source ~/.bashrc`:

```bash
export REPO="$HOME/fyp-pipeline"
```

On `stream-node`, also add these Layer 1 defaults once:

```bash
export LAYER1_BASELINES_DIR="$REPO/layer1/feature_store/baselines"
export LAYER1_RESULTS_DIR="$REPO/layer1/runtime_results"
```

Do **not** add a run ID to `~/.bashrc`. It is deliberately per-run and belongs only in the environment file below.

## Run identity and local run-environment files

Each node uses its own `$HOME`; therefore each node needs its own `~/fyp-run-env.sh` with the same literal `RUN_ID` and node-local `$REPO` path. Source this file in every new SSH or VS Code terminal before running an experiment command.

### Node 1 — `stream-node`

```bash
source ~/.bashrc
: "${REPO:?REPO is not set; configure ~/.bashrc first}"
RUN_ID="wifi_cold_$(date -u +%Y%m%d_%H%M%S)"
cat > "$HOME/fyp-run-env.sh" <<EOF
export RUN_ID="$RUN_ID"
export RUN_ROOT="\$REPO/experiment_runs/\$RUN_ID"
export SEG_RUN_DIR="\$RUN_ROOT/seg"
EOF
chmod 600 "$HOME/fyp-run-env.sh"
source "$HOME/fyp-run-env.sh"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${SEG_RUN_DIR:?SEG_RUN_DIR is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
mkdir -p "$RUN_ROOT"
printf 'RUN_ID=%s\n' "$RUN_ID"
```

For an Ethernet run, use `ethernet_cold_...` instead. Do not reuse a run ID.

### Node 2 — `ai-brain-node`

Paste the exact literal `RUN_ID` printed on Node 1; do not copy Node 1's absolute `$RUN_ROOT` path.

```bash
source ~/.bashrc
: "${REPO:?REPO is not set; configure ~/.bashrc first}"
RUN_ID="<paste the exact RUN_ID from stream-node>"
cat > "$HOME/fyp-run-env.sh" <<EOF
export RUN_ID="$RUN_ID"
export RUN_ROOT="\$REPO/experiment_runs/\$RUN_ID"
export LAYER2_EVALUATION_RUN_ID="\$RUN_ID"
export LAYER2_EVALUATION_DIR="\$RUN_ROOT/layer2_evaluation"
EOF
chmod 600 "$HOME/fyp-run-env.sh"
source "$HOME/fyp-run-env.sh"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${LAYER2_EVALUATION_RUN_ID:?LAYER2_EVALUATION_RUN_ID is not set}"
: "${LAYER2_EVALUATION_DIR:?LAYER2_EVALUATION_DIR is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
mkdir -p "$RUN_ROOT" "$LAYER2_EVALUATION_DIR"
```

### Node 3 — `gateway-node`

```bash
source ~/.bashrc
: "${REPO:?REPO is not set; configure ~/.bashrc first}"
RUN_ID="<paste the exact RUN_ID from stream-node>"
cat > "$HOME/fyp-run-env.sh" <<EOF
export RUN_ID="$RUN_ID"
export RUN_ROOT="\$REPO/experiment_runs/\$RUN_ID"
EOF
chmod 600 "$HOME/fyp-run-env.sh"
source "$HOME/fyp-run-env.sh"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
mkdir -p "$RUN_ROOT"
```

## Phase 0 — Full Cold Cleanup

### Node 1 — `stream-node`: Layer 1 state, outputs, and queues

Open a terminal on `stream-node`.

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
cd "$REPO/layer1"
```

#### 1. Reset the Feature Store calibration state

The Feature Store persists one calibration baseline per `affected_component`. It uses `LAYER1_BASELINES_DIR` when set; otherwise its authoritative default is `layer1/feature_store/baselines`. `CALIBRATION_N` is currently **20**. The first 20 accepted events for each component are used for calibration and are withheld from ADM fan-out. Rolling windows are in memory and disappear when ADM stops.

```bash
export BASELINES_DIR="${LAYER1_BASELINES_DIR:-$REPO/layer1/feature_store/baselines}"
printf 'Feature Store baseline directory: %s\n' "$BASELINES_DIR"
case "$BASELINES_DIR" in "$REPO/layer1/feature_store/baselines") ;; *) echo "Unsafe baseline directory: $BASELINES_DIR"; exit 1;; esac
mkdir -p "$BASELINES_DIR"
find "$BASELINES_DIR" -maxdepth 1 -type f -name '*.json' -print -delete
find "$BASELINES_DIR" -maxdepth 1 -type f -name '*.json' -print
```

The final `find` must print nothing. This preserves historical Layer 1 evaluation files and every other file outside the configured baseline directory.

#### 2. Clear disposable current-run Layer 1 outputs

Detector runtime results are written to `LAYER1_RESULTS_DIR`, or by default `layer1/runtime_results`. The historical material under `layer1/evaluation/historical` is not part of this cleanup.

```bash
export RESULTS_DIR="${LAYER1_RESULTS_DIR:-$REPO/layer1/runtime_results}"
case "$RESULTS_DIR" in "$REPO/layer1/runtime_results") ;; *) echo "Unsafe results directory: $RESULTS_DIR"; exit 1;; esac
mkdir -p "$RESULTS_DIR"
find "$RESULTS_DIR" -maxdepth 1 -type f \( \
  -name 'error_results.jsonl' -o -name 'throughput_results.jsonl' -o \
  -name 'auth_results.jsonl' -o -name 'cpu_results.jsonl' -o \
  -name 'schema_results.jsonl' \
\) -print -delete
rm -f "$REPO/layer1/fusion_engine/fusion_results.jsonl"
find "$RESULTS_DIR" -maxdepth 1 -type f -name '*_results.jsonl' -print
test ! -e "$REPO/layer1/fusion_engine/fusion_results.jsonl" && echo 'Fusion scratch output is absent.'
```

#### 3. Purge experiment messages without deleting topology

Run this only after the old consumers have stopped, so messages cannot be consumed during the purge. The commands purge messages only; queues and exchanges remain declared.

```bash
for queue in \
  raw.events validated.event detect.cpu detect.error detect.throughput \
  detect.auth detect.schema fusion.results anomaly.detected triage.result \
  strategy.result auto.execute hitl.queue outcome.feedback dead.letters
do
  sudo rabbitmqctl purge_queue -p fyp "$queue"
done

sudo rabbitmqctl list_queues -p fyp name messages_ready messages_unacknowledged
```

Every experiment queue listed above must show `0` ready and `0` unacknowledged. If a queue is absent, first re-declare the current topology in Phase 1; do not create an improvised queue name.

### Node 2 — `ai-brain-node`: Layer 2 memory, EMA, logs, and evaluation identity

Open a terminal on `ai-brain-node`, paste the same `RUN_ID`, and do this before starting any agent.

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${LAYER2_EVALUATION_RUN_ID:?LAYER2_EVALUATION_RUN_ID is not set}"
: "${LAYER2_EVALUATION_DIR:?LAYER2_EVALUATION_DIR is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
cd "$REPO/layer2"
printf 'Layer 2 evaluation run: %s\n' "$LAYER2_EVALUATION_DIR/$LAYER2_EVALUATION_RUN_ID"
```

`LAYER2_EVALUATION_RUN_ID` accepts this readable timestamp form and causes all agent artifacts to be written beneath the new run directory. Never delete `layer2/evaluation/results/*` as ordinary cold-run cleanup.

#### 4. Reset the authoritative Chroma persistence

The persistent Chroma client uses `layer2/chromadb_data` and collection `incident_history`; it has no environment-path override. Stop the Layer 2 agents before removing this directory.

```bash
export CHROMA_DIR="$REPO/layer2/chromadb_data"
case "$CHROMA_DIR" in "$REPO/layer2/chromadb_data") ;; *) echo "Unsafe Chroma path: $CHROMA_DIR"; exit 1;; esac
rm -rf "$CHROMA_DIR"
mkdir -p "$CHROMA_DIR"
python3 -c 'from chromadb_utils.client import get_document_count; count=get_document_count(); print(f"Chroma incident_history documents: {count}"); assert count == 0'
```

This removes only current experiment RAG/learning memory. It preserves prior Layer 2 evaluation directories and repository source files.

#### 5. Reset EMA threshold and optional disposable agent logs

`config/threshold_config.json` is the current persisted threshold schema. The configured cold starting threshold is `0.65`, `update_count` is `0`, `last_updated` is `initialised`, and `ema_alpha` is `0.9`. The Learning Agent persists later updates atomically; write the reset atomically as well.

```bash
export THRESHOLD_FILE="$REPO/layer2/config/threshold_config.json"
python3 - "$THRESHOLD_FILE" <<'PY'
import json, os, sys, tempfile
path = sys.argv[1]
value = {
    "_comment": "EMA confidence threshold used by the Policy Agent for AUTO vs HITL routing. Hard bounds: [0.60, 0.90]. Reset for fresh evaluation.",
    "confidence_threshold": 0.65,
    "last_updated": "initialised",
    "update_count": 0,
    "ema_alpha": 0.9,
}
directory = os.path.dirname(path)
fd, temporary = tempfile.mkstemp(prefix='.threshold-', suffix='.json', dir=directory)
try:
    with os.fdopen(fd, 'w') as output:
        json.dump(value, output, indent=2)
        output.write('\n')
    os.replace(temporary, path)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
PY
cat "$THRESHOLD_FILE"
rm -f "$REPO/layer2/logs/"*.jsonl
```

The log removal is optional diagnostic cleanup only; it does not touch the fresh evaluation directory.

### Node 3 — `gateway-node`: Django HITL and active decision log

Open a terminal on `gateway-node`, paste the same `RUN_ID`, then verify migrations before removing run state.

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
cd "$REPO/layer3/dashboard"
python3 manage.py showmigrations hitl
python3 manage.py migrate
```

The `HitlIncident` model, including `decided_at`, is managed by Django in `layer3/sqlite_logger/decisions.db`. Clear it through Django. The separate `decisions` table remains active: Auto Executor and HITL actions write it, so clear it too when the existing decision-log database is present.

```bash
python3 manage.py shell -c 'from hitl.models import HitlIncident; deleted, _ = HitlIncident.objects.all().delete(); print(f"Deleted HITL rows: {deleted}")'
python3 - <<'PY'
import sqlite3
from pathlib import Path
database = Path.cwd().parent / "sqlite_logger" / "decisions.db"
if not database.exists():
    print(f"Decision log does not yet exist: {database}")
else:
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM decisions")
        connection.commit()
    print(f"Cleared decisions table: {database}")
PY
python3 manage.py shell -c 'from hitl.models import HitlIncident; print("HITL total:", HitlIncident.objects.count()); print("HITL pending:", HitlIncident.objects.filter(status="PENDING").count())'
```

Both counts must be zero. This does not delete Django migrations, the database file, or non-experiment project files.

## Phase 1 — Start Infrastructure and Layer 1

### Node 1 — declare topology, then start every Layer 1 consumer

In a setup terminal on `stream-node`:

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/rabbitmq"
python3 setup_topology.py
sudo rabbitmqctl list_queues -p fyp name messages_ready messages_unacknowledged
```

Start the following processes in separate terminals. They are persistent RabbitMQ consumers; leave them running until the controlled drain procedure, rather than launching them as a background batch and waiting for them to exit.

If this deployment deliberately uses non-default `LAYER1_BASELINES_DIR` or `LAYER1_RESULTS_DIR`, export the same approved values in the relevant new terminals before starting ADM or a detector. The default paths need no extra export.

**Terminal L1-A — Validator (metrics `:8002`)**

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/validator"
python3 validator.py
```

**Terminal L1-B — ADM Runner / Feature Store**

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/adm"
python3 adm_runner.py
```

**Terminal L1-C — Fusion Engine (metrics `:8003`)**

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/fusion_engine"
python3 fusion_engine.py
```

Fusion has a primary correlation window of `3.0` seconds and a late-recovery window of `0.75` seconds (maximum `3.75` seconds). Its fast-path marker affects priority; it does not finalize a result early.

**Terminal L1-D through L1-H — one detector per terminal**

```bash
# L1-D — error detector, metrics :8004
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/adm"
python3 detectors/error_rate.py
```

```bash
# L1-E — throughput detector, metrics :8005
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/adm"
python3 detectors/throughput_drop.py
```

```bash
# L1-F — authentication detector, metrics :8006
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/adm"
python3 detectors/auth_flood.py
```

```bash
# L1-G — CPU detector, metrics :8007
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/adm"
python3 detectors/cpu_spike.py
```

```bash
# L1-H — schema detector, metrics :8008
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/adm"
python3 detectors/schema_drift.py
```

## Phase 2 — Start Layer 2

Every Layer 2 terminal must source Node 2's `~/fyp-run-env.sh`; an export in one terminal does not propagate to the other three.

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${LAYER2_EVALUATION_RUN_ID:?LAYER2_EVALUATION_RUN_ID is not set}"
: "${LAYER2_EVALUATION_DIR:?LAYER2_EVALUATION_DIR is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
cd "$REPO/layer2"
```

**Terminal L2-A — Triage Agent (metrics `:8010`)**

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${LAYER2_EVALUATION_RUN_ID:?LAYER2_EVALUATION_RUN_ID is not set}"
: "${LAYER2_EVALUATION_DIR:?LAYER2_EVALUATION_DIR is not set}"
python3 agents/triage_agent.py
```

**Terminal L2-B — Strategy Agent (metrics `:8011`)**

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${LAYER2_EVALUATION_RUN_ID:?LAYER2_EVALUATION_RUN_ID is not set}"
: "${LAYER2_EVALUATION_DIR:?LAYER2_EVALUATION_DIR is not set}"
python3 agents/strategy_agent.py
```

**Terminal L2-C — Policy Agent (metrics `:8012`)**

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${LAYER2_EVALUATION_RUN_ID:?LAYER2_EVALUATION_RUN_ID is not set}"
: "${LAYER2_EVALUATION_DIR:?LAYER2_EVALUATION_DIR is not set}"
python3 agents/policy_agent.py
```

**Terminal L2-D — Learning Agent (metrics `:8013`)**

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${LAYER2_EVALUATION_RUN_ID:?LAYER2_EVALUATION_RUN_ID is not set}"
: "${LAYER2_EVALUATION_DIR:?LAYER2_EVALUATION_DIR is not set}"
python3 agents/learning_agent.py
```

Strategy uses structured output. Learning is deterministic; retain its artifacts and the threshold file as evidence rather than changing behavior during a run.

## Phase 3 — Start Layer 3

### Node 3 — `gateway-node`

Start each long-running process in its own terminal.

**Terminal L3-A — Auto Executor (metrics `:8014`)**

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer3"
python3 auto_executor/executor.py
```

**Terminal L3-B — HITL queue consumer**

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer3/dashboard"
python3 manage.py consume_hitl
```

**Terminal L3-C — Django dashboard and HITL metrics**

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer3/dashboard"
python3 manage.py runserver 0.0.0.0:8000
```

Do not repeatedly restart Prometheus or Grafana when their configuration is already loaded. The current dashboard definition is `layer3/grafana/FYP_Hybrid_Agentic_Framework_Observability_v3_Node_Naming.json`, titled **Hybrid Agentic Framework — Final Research Observability**, with these rows:

- `SYSTEM OVERVIEW`
- `LAYER 1 — REAL-TIME STATISTICAL DATA PLANE`
- `LAYER 2 — AI CONTROL PLANE`
- `LAYER 3 — EXECUTION, HUMAN OVERSIGHT & OBSERVABILITY LAYER`
- `INFRASTRUCTURE / HARDWARE`

## Phase 4 — Pre-Run Verification and Metadata

Do not publish an event until every required consumer is running and the following checks pass.

### Endpoint checks

From an appropriate node with network access to all hosts:

```bash
for endpoint in \
  http://stream-node:8002/metrics \
  http://stream-node:8003/metrics \
  http://stream-node:8004/metrics \
  http://stream-node:8005/metrics \
  http://stream-node:8006/metrics \
  http://stream-node:8007/metrics \
  http://stream-node:8008/metrics \
  http://ai-brain-node:8010/metrics \
  http://ai-brain-node:8011/metrics \
  http://ai-brain-node:8012/metrics \
  http://ai-brain-node:8013/metrics \
  http://gateway-node:8014/metrics \
  http://gateway-node:8000/metrics
do
  printf '%s: ' "$endpoint"
  curl -fsS "$endpoint" >/dev/null && echo UP || echo DOWN
done
curl -fsS http://gateway-node:8000/metrics | grep -E '^fyp_hitl_'
```

On the host running Prometheus (normally `gateway-node`), confirm the configured targets are up. If Prometheus is not on port `9090`, use its actual local UI/API address.

```bash
curl -fsS http://localhost:9090/api/v1/targets
```

Check for active Layer 1, Layer 2, Layer 3, RabbitMQ (`:15692`), and node-exporter (`:9100`) targets. The dashboard is available at the configured Grafana address; verify that the current dashboard loads and its targets are UP.

### Zero-state checklist

- [ ] Same Git commit on `stream-node`, `ai-brain-node`, and `gateway-node` (`git rev-parse HEAD`).
- [ ] All listed experiment queues have zero ready and unacknowledged messages.
- [ ] Configured Feature Store baseline directory has no `*.json` files.
- [ ] Chroma `incident_history` document count is zero.
- [ ] Threshold config shows `confidence_threshold: 0.65`, `update_count: 0`, and `ema_alpha: 0.9`.
- [ ] Django reports zero total and pending HITL incidents.
- [ ] The one new Layer 2 evaluation run ID is recorded in all four Layer 2 terminals.
- [ ] Endpoints `8002`–`8008`, `8010`–`8014`, and Django `/metrics` are reachable.
- [ ] Required Prometheus targets are UP and the current dashboard is loaded.
- [ ] Validator, ADM, Fusion, all five detectors, all four Layer 2 agents, Auto Executor, HITL consumer, and Django are running.
- [ ] No SEG replay has begun.

### Record reproducibility metadata

On Node 1, before replay, create an operator-owned record in the new run directory. Replace the network value as needed.

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
cd "$REPO"
{
  printf 'recorded_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'run_id=%s\n' "$RUN_ID"
  printf 'network_medium=%s\n' 'Wi-Fi'
  printf 'git_commit=%s\n' "$(git rev-parse HEAD)"
  printf 'replay_speed=%s\n' '1'
  printf 'corpus=%s\n' "$RUN_ROOT/seg/events_1950.jsonl"
  printf 'corpus_events=%s\n' "$(wc -l < "$RUN_ROOT/seg/events_1950.jsonl")"
  printf 'feature_store_baselines=empty_before_replay\n'
  printf 'chroma_documents=0_before_replay\n'
  printf 'initial_ema_threshold=0.65\n'
  printf 'nodes=stream-node,ai-brain-node,gateway-node\n'
  printf 'queues=zero_ready_and_unacknowledged_before_replay\n'
} | tee "$RUN_ROOT/metadata.txt"
```

Generate the corpus before this metadata command, as described next.

## Corpus generation — do this once per run directory

SEG’s configured corpus contains **1,950 events**: 1,000 normal, four 200-event anomaly types, and 150 schema-drift events. Generation uses the copied config and writes runtime events without ground truth; it writes corresponding ground truth to a separate CSV. Runtime components never receive the CSV.

On Node 1, create a run-specific copy of the SEG config, set its base timestamp, and generate once.

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${SEG_RUN_DIR:?SEG_RUN_DIR is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
case "$SEG_RUN_DIR" in "$RUN_ROOT/seg") ;; *) echo "Unsafe SEG_RUN_DIR: $SEG_RUN_DIR"; exit 1;; esac
printf 'REPO=%s\nRUN_ID=%s\nRUN_ROOT=%s\nSEG_RUN_DIR=%s\n' "$REPO" "$RUN_ID" "$RUN_ROOT" "$SEG_RUN_DIR"
mkdir -p "$SEG_RUN_DIR"
cp "$REPO/layer1/seg/config/seg_config.json" "$SEG_RUN_DIR/seg_config.json"
python3 - "$SEG_RUN_DIR/seg_config.json" <<'PY'
import json, sys
from datetime import datetime, timezone
path = sys.argv[1]
with open(path) as source:
    config = json.load(source)
config['base_timestamp'] = datetime.now(timezone.utc).isoformat()
with open(path, 'w') as output:
    json.dump(config, output, indent=2)
    output.write('\n')
print('base_timestamp =', config['base_timestamp'])
PY
cd "$REPO/layer1/seg"
python3 seg.py --mode generate --config "$SEG_RUN_DIR/seg_config.json" --output "$SEG_RUN_DIR"
wc -l "$SEG_RUN_DIR/events_1950.jsonl"
head -n 1 "$SEG_RUN_DIR/labels.csv"
```

Generation overwrites `events_1950.jsonl` and `labels.csv` in its output directory. Complete any manual `expected_route` and `safe_to_auto` annotation in this new run’s `labels.csv` **after generation and before the final replay**, then never regenerate into this run directory. These annotations are necessary for computable FAR and FER; blank fields intentionally produce `not_computable`, not zero.

`RUN_ROOT` is node-local unless the deployment explicitly mounts shared storage. Before analysis, transfer the final label CSV from Node 1 to the matching Node 2 run directory (or use the approved shared mount). From Node 1, after annotations are complete:

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
test -f "$RUN_ROOT/seg/labels.csv" || { echo "Final labels unavailable: $RUN_ROOT/seg/labels.csv"; exit 1; }
ssh ai-brain-node "mkdir -p \$HOME/fyp-pipeline/experiment_runs/$RUN_ID/seg"
scp "$RUN_ROOT/seg/labels.csv" "ai-brain-node:fyp-pipeline/experiment_runs/$RUN_ID/seg/labels.csv"
```

Use the same transfer for a diagnostic label subset when that diagnostic is analyzed on Node 2. The label files are offline inputs only; never copy or publish them into RabbitMQ or a runtime component.

## Pre-Freeze Diagnostic — 50 Events

This is evidence collection, not the authoritative final experiment. Perform the same Phase 0 resets, fresh-process startup, and Phase 4 checks for its own new diagnostic `RUN_ID`; do not run it in the final run directory. Use a `diagnostic_...` identifier and produce the 1,950-event source corpus as above.

SEG has no `--limit` flag. Do not use the first 50 shuffled lines: a cold Feature Store would withhold an uncontrolled mixture of early per-component calibration events and may not exercise Layer 2. Instead, make a deterministic diagnostic input for one component: its first 20 normal events establish that component’s cold baseline, and the next 30 non-normal events exercise detection and the Layer 2 path. The runtime JSONL remains label-free; make a matching labels subset solely for offline analysis.

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${SEG_RUN_DIR:?SEG_RUN_DIR is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
case "$SEG_RUN_DIR" in "$RUN_ROOT/seg") ;; *) echo "Unsafe SEG_RUN_DIR: $SEG_RUN_DIR"; exit 1;; esac
export CORPUS="$SEG_RUN_DIR/events_1950.jsonl"
export LABELS="$SEG_RUN_DIR/labels.csv"
export DIAG_EVENTS="$SEG_RUN_DIR/events_50_diagnostic.jsonl"
export DIAG_LABELS="$SEG_RUN_DIR/labels_50_diagnostic.csv"
python3 - "$CORPUS" "$LABELS" "$DIAG_EVENTS" "$DIAG_LABELS" <<'PY'
import csv, json, sys
from collections import defaultdict

corpus_path, labels_path, output_events, output_labels = sys.argv[1:]
events = [json.loads(line) for line in open(corpus_path) if line.strip()]
normal, abnormal = defaultdict(list), defaultdict(list)
for event in events:
    component = event.get('affected_component', 'unknown')
    if event.get('anomaly_type', 'NORMAL') == 'NORMAL':
        normal[component].append(event)
    else:
        abnormal[component].append(event)
choices = sorted(component for component in normal if len(normal[component]) >= 20 and len(abnormal[component]) >= 30)
if not choices:
    raise SystemExit('No component has 20 NORMAL and 30 non-NORMAL events; do not substitute an arbitrary head subset.')
component = choices[0]
selected = normal[component][:20] + abnormal[component][:30]
with open(output_events, 'w') as output:
    for event in selected:
        output.write(json.dumps(event) + '\n')
selected_ids = {event['event_id'] for event in selected}
with open(labels_path, newline='') as source, open(output_labels, 'w', newline='') as output:
    reader = csv.DictReader(source)
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames)
    writer.writeheader()
    writer.writerows(row for row in reader if row['event_id'] in selected_ids)
print(f'component={component}; events={len(selected)}; labels={len(selected_ids)}')
PY
wc -l "$DIAG_EVENTS"
ssh ai-brain-node "mkdir -p \$HOME/fyp-pipeline/experiment_runs/$RUN_ID/seg"
scp "$DIAG_LABELS" "ai-brain-node:fyp-pipeline/experiment_runs/$RUN_ID/seg/labels_50_diagnostic.csv"
```

Replay only after every consumer is verified:

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${SEG_RUN_DIR:?SEG_RUN_DIR is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
case "$SEG_RUN_DIR" in "$RUN_ROOT/seg") ;; *) echo "Unsafe SEG_RUN_DIR: $SEG_RUN_DIR"; exit 1;; esac
DIAG_EVENTS="$SEG_RUN_DIR/events_50_diagnostic.jsonl"
test -f "$DIAG_EVENTS" || { echo "Diagnostic events unavailable: $DIAG_EVENTS"; exit 1; }
cd "$REPO/layer1/seg"
python3 seg.py --mode replay --config "$SEG_RUN_DIR/seg_config.json" --input "$DIAG_EVENTS" --speed 1
```

Exactly 50 events are published. The first 20 establish one component baseline and are withheld by Feature Store; fewer than 50 Strategy records are therefore expected, not evidence of loss. This constructed ordering is diagnostic-only and must not be used as the final corpus ordering.

After the pipeline drains, inspect Strategy’s current counters from Prometheus on `gateway-node`:

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
curl -fsS 'http://localhost:9090/api/v1/query?query=fyp_strategy_schema_valid_total'
curl -fsS 'http://localhost:9090/api/v1/query?query=fyp_strategy_schema_invalid_total'
curl -fsS 'http://localhost:9090/api/v1/query?query=fyp_strategy_timeout_total'
```

Then compare them with the diagnostic evaluation artifacts from `ai-brain-node`:

```bash

source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${LAYER2_EVALUATION_DIR:?LAYER2_EVALUATION_DIR is not set}"
DIAG_LABELS="$RUN_ROOT/seg/labels_50_diagnostic.csv"
test -f "$DIAG_LABELS" || { echo "Diagnostic labels unavailable: $DIAG_LABELS"; exit 1; }
cd "$REPO"
python3 -m layer2.evaluation.analyze_run \
  --run-dir "$LAYER2_EVALUATION_DIR/$RUN_ID" \
  --ground-truth "$DIAG_LABELS"
```

The analyzer writes `evaluation_summary.json` and `per_event.csv` in the selected run directory. When invalid records exist, inspect `strategy.jsonl`, `evaluation_summary.json`, and `per_event.csv`; this diagnostic records evidence and does not authorize changes to Strategy.

Shut down all diagnostic consumers, preserve its run directory, then repeat Phase 0 through Phase 4 with a **new final RUN_ID** before the 1,950-event run. This produces fresh counters and genuinely cold persistent state for the final run.

## Phase 5 — Full 1,950-Event Replay

With the final run’s zero-state checklist complete and any required manual labels already saved, replay the full generated corpus from Node 1:

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${SEG_RUN_DIR:?SEG_RUN_DIR is not set}"
case "$SEG_RUN_DIR" in "$RUN_ROOT/seg") ;; *) echo "Unsafe SEG_RUN_DIR: $SEG_RUN_DIR"; exit 1;; esac
cd "$REPO/layer1/seg"
python3 seg.py --mode replay \
  --config "$RUN_ROOT/seg/seg_config.json" \
  --input "$RUN_ROOT/seg/events_1950.jsonl" \
  --speed 1
```

SEG adds live `ingestion_time` on replay. Its configured base timestamp makes corpus generation reproducible; replay speed only changes workload arrival rate. Preserve the generated events and labels for this run.

## Phase 6 — Monitor and Controlled HITL Interaction

While replay and draining proceed, inspect queue state from `stream-node`:

```bash
watch -n 2 'sudo rabbitmqctl list_queues -p fyp name messages_ready messages_unacknowledged'
```

Use the Django dashboard at `http://gateway-node:8000/` to process a controlled subset of pending HITL incidents: approve at least one, reject at least one, and modify at least one where valid incidents are available. Record the IDs and counts in your experiment notes. This demonstrates all three human-decision paths and causes corresponding `outcome.feedback` activity. Do not require every HITL incident to be decided unless the study explicitly defines exhaustive feedback.

Monitor the final dashboard and current metrics, including detector processing latency; Fusion published, suppressed, compound, fast-path, correlation-wait, and late-recovery observations; Strategy Schema Validity Rate and timeout rate; policy routing/reasons; Control-Plane Processing Latency; End-to-End Decision Latency; Feedback Completion Latency; Learning Processing Latency; Chroma upserts; EMA threshold; Strategy tokens/sec; Auto Executor outcomes and latency; HITL pending/outcomes; and Human Decision Latency.

## Phase 7 — Drain and Post-Run Analysis

After SEG exits, do **not** stop consumers immediately. Wait for computational backlogs to settle.

```bash
watch -n 2 'sudo rabbitmqctl list_queues -p fyp name messages_ready messages_unacknowledged'
```

The computational queues `fusion.results`, `anomaly.detected`, `triage.result`, `strategy.result`, and `auto.execute` should drain to zero. `hitl.queue` may remain intentionally non-zero while cases await the controlled human subset. `outcome.feedback` must be allowed to drain after each AUTO action and each handled HITL action. Record any intentional pending HITL count separately from computational backlog.

### Layer 2 offline analysis

Run from the repository root on `ai-brain-node` (or from a copy of the same run artifacts and labels):

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${LAYER2_EVALUATION_DIR:?LAYER2_EVALUATION_DIR is not set}"
test -f "$RUN_ROOT/seg/labels.csv" || { echo "Final labels unavailable: $RUN_ROOT/seg/labels.csv"; exit 1; }
cd "$REPO"
python3 -m layer2.evaluation.analyze_run \
  --run-dir "$LAYER2_EVALUATION_DIR/$RUN_ID" \
  --ground-truth "$RUN_ROOT/seg/labels.csv"
```

Use `--expect-hitl-feedback` only when the experiment intentionally provides feedback for every expected HITL decision. A sampled controlled subset must use the command above without that flag. Risk-Tier Accuracy requires matching risk-tier labels. FAR requires authoritative `safe_to_auto`, and FER requires authoritative `expected_route`; absent manual annotations remain `not_computable`.

### Layer 1 runtime evidence and limitation

Preserve and count the current runtime outputs; they are not ground-truth performance calculations:

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
export RESULTS_DIR="${LAYER1_RESULTS_DIR:?LAYER1_RESULTS_DIR is not set; configure ~/.bashrc}"
case "$RESULTS_DIR" in "$REPO/layer1/runtime_results") ;; *) echo "Unsafe results directory: $RESULTS_DIR"; exit 1;; esac
find "$RESULTS_DIR" -maxdepth 1 -type f -name '*_results.jsonl' -print -exec wc -l {} \;
wc -l "$REPO/layer1/fusion_engine/fusion_results.jsonl"
```

Current code provides these runtime detector and Fusion JSONL artifacts, but it does **not** provide a current Layer 1 final evaluation CLI that joins them to this run’s labels and reports TP, FP, precision, and recall. The files in `layer1/evaluation/historical` are historical experiments, not an authoritative analyzer for this runtime corpus. Preserve the final run outputs and labels; do not claim those detector ground-truth metrics until a separate, verified offline evaluator is implemented.

### Layer 3 and state evidence

On `gateway-node`:

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer3/dashboard"
python3 manage.py shell -c 'from hitl.models import HitlIncident; from collections import Counter; print("HITL statuses:", dict(Counter(HitlIncident.objects.values_list("status", flat=True))))'
python3 - <<'PY'
import sqlite3
from pathlib import Path
database = Path.cwd().parent / "sqlite_logger" / "decisions.db"
if database.exists():
    with sqlite3.connect(database) as connection:
        for row in connection.execute('SELECT decision_type, COUNT(*) FROM decisions GROUP BY decision_type ORDER BY decision_type'):
            print(*row, sep=': ')
PY
```

On `ai-brain-node`:

```bash
source ~/.bashrc
source "$HOME/fyp-run-env.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${LAYER2_EVALUATION_DIR:?LAYER2_EVALUATION_DIR is not set}"
cd "$REPO/layer2"
python3 -c 'from chromadb_utils.client import get_document_count; print("Chroma incident_history documents:", get_document_count())'
cat "$REPO/layer2/config/threshold_config.json"
```

## Phase 8 — Shutdown and Preserve Results

1. Capture any required Grafana/Prometheus observations while the services and counters remain live.
2. Stop the long-running consumers with `Ctrl+C` only after the drain and evidence collection are complete.
3. Preserve `experiment_runs/$RUN_ID`, Layer 1 runtime result files, Fusion output, the run-specific corpus, labels, metadata, and Layer 2 analysis artifacts.
4. Prometheus and Grafana may remain running for infrastructure monitoring.
5. Do not commit, push, delete prior run directories, or overwrite this run’s labels after analysis.
