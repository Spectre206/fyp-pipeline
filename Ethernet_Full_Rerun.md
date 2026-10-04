# Ethernet Full Rerun — 50-Event Diagnostic and 1,950-Event Full Run

**Project:** Distributed Multi-Agent Coordination for Self-Healing Data Pipelines — Human-in-the-Loop on Commodity Hardware.

This is the Ethernet companion to [Full_Rerun.md](Full_Rerun.md), derived from its cold-system procedure at deployment revision **c0ad6be9c84955240cf4499d586ad46b1d579ecc**, branch **feature/ethernet-migration**. The shared phases below reproduce its resets, startup order, queues, replay speed, analysis and shutdown. Execute one mode at a time using the numbered mode checklist; shared blocks are included here in full so no chat history is needed.

**50 events = integration evidence only. 1,950 events = candidate formal measurement only after the experimental freeze is complete.** Never carry diagnostic state into a full run. Do not change prompts, model options, detectors, Fusion, Policy, Learning, thresholds beyond the existing cold reset, labels, ports, or topology. Do not merge baseline branches. No commands in this document have been executed as an experiment during document preparation.

## Mode 1 — 50-event Ethernet diagnostic: execution checklist

1. On **all three nodes**, execute the revision gate below; stop and archive old consumers/state before any reset.
2. Create a unique `ethernet-diagnostic-50-YYYYMMDD-HHMMSS` identity using Session setup. Prepare per-node pane bootstraps and credentials once.
3. Run Network and process preflight; save routes, link state and counters.
4. Run shared Phase 0 on each node, confirming every destructive block. Use the same cold reset as Wi-Fi; this run's state is disposable only after archival.
5. Run shared Phases 1, 2, 3, in order (Layer 3: Auto Executor, HITL consumer, Django, matching Wi-Fi). Use separate panes.
6. Run Phase 4, then Ethernet transport gate and Grafana checkpoint. Confirm consumers and no competing controller.
7. Generate the source corpus using Corpus generation below, then run Diagnostic subset preparation. Keep source events unchanged and transfer only the diagnostic labels for offline analysis.
8. Run Corpus verification for the selected 50 events and record metadata. Start optional captures in separate panes before publication.
9. Run Diagnostic publication exactly once, at speed 1; preserve start/end timestamps and SEG exit status.
10. Execute shared Phases 6–7: observe metrics, perform controlled HITL review, drain queues, reconcile all 50 input events and downstream records. Use the diagnostic analyzer command, not the full-label command.
11. Complete Evidence capture while metrics are live, stop captures, then Phase 8 shutdown and archival. Complete the diagnostic PASS/FAIL checklist. An unexercised AUTO or HITL path is incomplete coverage, not permission to tune routes or inject more events into this 50-event run.
12. Preserve the diagnostic directory. For a full run, stop all diagnostic consumers and restart at Mode 2 step 1 with a new ID and cold state.

## Mode 2 — full 1,950-event Ethernet run: execution checklist

1. On **all three nodes**, repeat the revision gate below. A diagnostic pass does not replace this check.
2. Confirm the frozen independent ground truth, repetition/condition order, timeout/rerun criteria, model loading/warmup, human-review and monitoring policies. See `evaluation/baselines/BASELINE_EXPERIMENT_DESIGN.md`, especially Sections 6, 11–14 and 18. Unresolved freeze items prevent a formal-evidence claim. This is the full-pipeline procedure, not the primary identical-incident controller comparison.
3. Create a new `ethernet_cold_YYYYMMDD_HHMMSS` identity with Session setup; archive previous runtime state before resetting it.
4. Repeat Network and process preflight and shared Phase 0 exactly, including empty Feature Store, Chroma, EMA 0.65/0.9/update_count 0, SQLite and queues. Start fresh processes for fresh counters.
5. Run Phases 1–4 and the Ethernet transport gate. No workload until every required service and transport check passes.
6. For a **formal matched Wi-Fi-vs-Ethernet run, frozen-source reuse is mandatory**: reuse the approved `events_1950.jsonl`, final `labels.csv`, and `seg_config.json`, verified against the independent frozen manifest. Preserve identical event IDs, event order, file hashes and replay speed 1. Fresh generation is allowed **only for non-formal engineering/full-pipeline validation**, recorded as `engineering`; it cannot qualify as a matched formal run. Never regenerate into a frozen run directory. Keep all 1,950 events in original order: NORMAL 1000; cpu_memory_spike 200; error_rate_surge 200; throughput_drop 200; auth_failure_flood 200; schema_drift 150.
7. For formal matched runs, retain the already approved final labels unchanged; for engineering runs, finalize independent labels before replay. Transfer the final CSV to Node 2. Run full Corpus verification and metadata recording. Preserve exact corpus/config/labels hashes and revision.
8. Run Full publication once at speed 1. Record timestamps. Do not change model warmup or review policy mid-run.
9. Execute Phases 6–7 and exhaustive HITL handling when reproducing the completed Wi-Fi protocol: zero pending, feedback drained. The historical 469 HITL / 639 feedback counts are reference observations, not expected counts to force on a new run.
10. Capture metrics/evidence before shutdown; preserve all per-node artifacts, then Phase 8 and credential cleanup. Record failures and deviations. Successful execution alone does not establish publishable research evidence.

## Revision gate — mandatory at the beginning of BOTH modes, all nodes

```bash
export REPO="$HOME/fyp-pipeline"
cd "$REPO"
FROZEN_BASE=c0ad6be9c84955240cf4499d586ad46b1d579ecc
EXPERIMENT_HEAD=$(git rev-parse --verify HEAD) || exit 1
export FROZEN_BASE EXPERIMENT_HEAD
git branch --show-current
git rev-parse HEAD
git status --short
printf 'deployment_base=%s\nexperiment_head=%s\n' "$FROZEN_BASE" "$EXPERIMENT_HEAD"
[[ "$(git branch --show-current)" == feature/ethernet-migration ]] || exit 1
git merge-base --is-ancestor "$FROZEN_BASE" "$EXPERIMENT_HEAD" || exit 1
WORKTREE_STATUS=$(git status --porcelain=v1 --untracked-files=all) || exit 1
[[ -z "$WORKTREE_STATUS" ]] || { echo 'Stop: working tree is not clean'; exit 1; }
git diff --quiet --no-ext-diff --no-textconv --no-renames \
  "$FROZEN_BASE" "$EXPERIMENT_HEAD" -- . ':(top,exclude,literal)Ethernet_Full_Rerun.md' \
  || { echo 'Stop: changes outside the permitted runbook relative to the frozen base'; exit 1; }
# Review this permitted documentation difference before authorizing measurement:
git --no-pager diff "$FROZEN_BASE" "$EXPERIMENT_HEAD" -- ':(top,literal)Ethernet_Full_Rerun.md'
```

The base remains the authoritative application/deployment revision; the actual experiment HEAD is recorded separately. The gate requires a clean tracked/untracked working tree, descent from the base, and no tree differences anywhere except the **exact root file `Ethernet_Full_Rerun.md`**. The root-anchored literal exclusion does not exempt other Markdown files, configuration, scripts, dependencies or deployment files. Disabling renames/external diff/text conversion keeps the comparison about Git tree content and modes. A later reviewed documentation-only commit containing this runbook is therefore allowed; any final-tree application/deployment change fails. The comparison proves final-tree identity outside the allowlisted file, not that every intervening commit was documentation-only or that ignored runtime files/model installations are identical. Those remain subject to the existing runtime freeze checks. The permitted runbook diff still requires review; the gate does not establish review approval automatically.

All nodes must use the same approved actual experiment HEAD. Save the printed base/HEAD and gate output in each node's `transport/revision-before.txt` once its run directory exists, repeating the complete gate before measurement. Do not hide source changes with ignore rules, assume-unchanged or skip-worktree flags. The currently untracked runbook must be reviewed and committed through the normal process before this clean-tree gate can pass; this procedure does not stage or commit it.

Repeat `git status --short` immediately before measurement. Generated `experiment_runs/` artifacts are not globally ignored here. To retain the authoritative artifact path and a clean source tree, the session setup below records a **local Git exclude for only this run directory** in `.git/info/exclude`; this is runtime bookkeeping outside tracked files, not an exclusion for source changes. Do not exclude the new runbook or any source/config file. Inspect tracked changes independently with `git diff --exit-code` before measurement. Runtime EMA changes after publication are expected evidence: archive the final threshold and diff; never reset them just to make the post-run tree appear clean.

## Session setup — once per node and run

Use Bash. Dependencies are already installed; do not upgrade them during a benchmark. Node 1 uses its established Wi-Fi Python environment (no Node 1 virtualenv path is specified by the source runbook). Node 2 uses `/home/spectre206/fyp-pipeline/.venv`; Node 3 uses `/home/spectre/fyp-pipeline/venv`. Confirm these local paths before proceeding.

On Node 1 select **one** ID command:

```bash
export REPO="$HOME/fyp-pipeline"
RUN_ID="ethernet-diagnostic-50-$(date -u +%Y%m%d-%H%M%S)"  # diagnostic only
# Full mode instead: RUN_ID="ethernet_cold_$(date -u +%Y%m%d_%H%M%S)"
printf 'RUN_ID=%s\n' "$RUN_ID"
```

On Nodes 2 and 3, set `REPO="$HOME/fyp-pipeline"` and `read -r -p 'Exact RUN_ID from Node 1: ' RUN_ID`. Then run this on **each node**, entering its number. This writes only runtime files outside Git. Never reuse an existing run directory.

```bash
read -r -p 'Node number (1, 2, 3): ' FYP_NODE
[[ "$FYP_NODE" =~ ^[123]$ ]] || exit 1
[[ "$RUN_ID" =~ ^(ethernet-diagnostic-50-[0-9]{8}-[0-9]{6}|ethernet_cold_[0-9]{8}_[0-9]{6})$ ]] || exit 1
export RUN_ID REPO
export RUN_ROOT="$REPO/experiment_runs/$RUN_ID"
test ! -e "$RUN_ROOT" || { echo 'Stop: run directory already exists'; exit 1; }
# Local-only runtime artifact exclusion; no tracked files or global ignores change.
cd "$REPO"
printf '/experiment_runs/%s/\n' "$RUN_ID" >> "$(git rev-parse --git-path info/exclude)"
umask 077
mkdir -p "$RUN_ROOT/transport" "$RUN_ROOT/metrics"
{
  printf 'export REPO=%q\nexport RUN_ID=%q\n' "$REPO" "$RUN_ID"
  printf 'export RUN_ROOT="$REPO/experiment_runs/$RUN_ID"\n'
  printf 'export SEG_RUN_DIR="$RUN_ROOT/seg"\n'
  if [[ "$FYP_NODE" == 2 ]]; then
    printf 'export LAYER2_EVALUATION_RUN_ID="$RUN_ID"\n'
    printf 'export LAYER2_EVALUATION_DIR="$RUN_ROOT/layer2_evaluation"\n'
  fi
} > "$HOME/fyp-run-env.sh"
chmod 600 "$HOME/fyp-run-env.sh"
source "$HOME/fyp-run-env.sh"
```

On **Nodes 2 and 3 only**, enter RabbitMQ credentials once per node/session. `mktemp` avoids a predictable shared `/tmp` filename; Bash `%q` safely quotes special characters. Disable shell tracing and do not print or archive this file.

```bash
set +x
umask 077
FYP_RUNTIME_ENV=$(mktemp /tmp/fyp-runtime.XXXXXXXX.env)
read -r -p 'RabbitMQ user: ' RABBITMQ_USER
read -r -s -p 'RabbitMQ password: ' RABBITMQ_PASS
printf '\n'
printf 'export RABBITMQ_USER=%q\nexport RABBITMQ_PASS=%q\n' \
  "$RABBITMQ_USER" "$RABBITMQ_PASS" > "$FYP_RUNTIME_ENV"
chmod 600 "$FYP_RUNTIME_ENV"
unset RABBITMQ_USER RABBITMQ_PASS
```

On **each node**, still in that setup shell, create the pane bootstrap. It references the permanent non-secret Ethernet profile rather than duplicating its network exports.

```bash
{
  printf 'source "$HOME/fyp-run-env.sh"\n'
  case "$FYP_NODE" in
    1) printf 'export LAYER1_BASELINES_DIR="$REPO/layer1/feature_store/baselines"\nexport LAYER1_RESULTS_DIR="$REPO/layer1/runtime_results"\n' ;;
    2) printf 'source "$REPO/.venv/bin/activate"\nsource "$REPO/deployment/ethernet/node2.env.sh"\n' ;;
    3) printf 'source "$REPO/venv/bin/activate"\nsource "$REPO/deployment/ethernet/node3.env.sh"\n' ;;
  esac
  if [[ "$FYP_NODE" != 1 ]]; then
    printf 'export FYP_RUNTIME_ENV=%q\n' "$FYP_RUNTIME_ENV"
    printf 'set +x\nsource "$FYP_RUNTIME_ENV"\n'
  fi
} > "$HOME/fyp-ethernet-pane.sh"
chmod 600 "$HOME/fyp-ethernet-pane.sh"
source "$HOME/fyp-ethernet-pane.sh"
mkdir -p "$RUN_ROOT/transport" "$RUN_ROOT/metrics"
```

Every new application or evidence pane begins with `source "$HOME/fyp-ethernet-pane.sh"`. Do not overwrite these session files while old processes are still running. Vhost remains `fyp`; local Ollama remains `http://localhost:11434`; Chroma and SQLite stay local. Node 1's co-located broker/topology configuration remains unchanged. Its configured hostname may resolve to its own Wi-Fi address but is local-kernel traffic, not an inter-node hop.

## Network and process preflight — all nodes

| Node | Address | Ethernet interface | Peers for route checks |
|---|---|---|---|
| stream-node | 10.10.10.11 | enp2s0 | 10.10.10.12 10.10.10.13 |
| ai-brain-node | 10.10.10.12 | enp2s0 | 10.10.10.11 10.10.10.13 |
| gateway-node | 10.10.10.13 | enx00e04c681057 | 10.10.10.11 10.10.10.12 |

Wi-Fi stays enabled and remains the Internet/default route. Do not change `/etc/hosts`, NetworkManager, or gateways. Physical iperf3 validation is already complete; do not rerun it during an application experiment.

In the setup pane, select the matching row (Node 1 shown; replace both values on other nodes):

```bash
source "$HOME/fyp-ethernet-pane.sh"
ETH_IF=enp2s0
PEERS='10.10.10.12 10.10.10.13'
# Node 2: ETH_IF=enp2s0; PEERS='10.10.10.11 10.10.10.13'
# Node 3: ETH_IF=enx00e04c681057; PEERS='10.10.10.11 10.10.10.12'
for peer in $PEERS; do ip route get "$peer"; done | tee "$RUN_ROOT/transport/routes-before.txt"
ip -s link show dev "$ETH_IF" | tee "$RUN_ROOT/transport/counters-before.txt"
sudo ethtool "$ETH_IF" | tee "$RUN_ROOT/transport/link.txt"
sudo ss -lntp | tee "$RUN_ROOT/transport/listeners-before.txt"
ps -eo pid,args | grep -E 'validator.py|adm_runner.py|fusion_engine.py|detectors/|agents/|auto_executor|consume_hitl|runserver|threshold_only|single_agent|seg.py' | tee "$RUN_ROOT/transport/processes-before.txt"
```

Require peer routes on the listed Ethernet interface with the node's `10.10.10.x` source, **Speed: 1000Mb/s**, **Duplex: Full**, **Link detected: yes**. Check there are no leftover consumers/replayers or occupied application metrics ports before startup. Keep RabbitMQ, Ollama, Prometheus, Grafana and node exporters running. Stop old applications gracefully in their owning panes; do not blindly kill by pattern.

Before Phase 0, archive previous run directories and stopped runtime state to a unique protected location outside the checkout: Node 1 baselines/runtime_results/Fusion output; Node 2 Chroma, threshold_config.json, logs and evaluation artifacts; Node 3 decisions.db plus any SQLite sidecars. A stopped SQLite backup can use Python's `sqlite3.Connection.backup`; do not copy a changing database. Record archive location in operator notes. Preserve all Wi-Fi evidence. The reset blocks below are the Wi-Fi reset commands, not a new purge policy. If an archive is unavailable, stop before deletion.

## Phase 0 — Full Cold Cleanup

### Node 1 — `stream-node`: Layer 1 state, outputs, and queues

Open a terminal on `stream-node`.

```bash
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
cd "$REPO/layer1"
```

#### 1. Reset the Feature Store calibration state

**DELETE / RESET — visually inspect the paths and archived state first.**

```bash
read -r -p "Archive checked, all old consumers stopped; type RESET: " confirmation
[[ "$confirmation" == RESET ]] || { echo "Stop: reset not approved"; exit 1; }
```


The Feature Store persists one calibration baseline per `affected_component`. It uses `LAYER1_BASELINES_DIR` when set; otherwise its authoritative default is `layer1/feature_store/baselines`. `CALIBRATION_N` is currently **20**. Calibration uses 20 accepted events per component. The first 19 are withheld from ADM fan-out; the twentieth completes calibration and can be enriched/fanned out. Rolling windows are in memory and disappear when ADM stops.

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

**DELETE / RESET — visually inspect the paths and archived state first.**

```bash
read -r -p "Archive checked, all old consumers stopped; type RESET: " confirmation
[[ "$confirmation" == RESET ]] || { echo "Stop: reset not approved"; exit 1; }
```


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

**DELETE / RESET — visually inspect the paths and archived state first.**

```bash
read -r -p "Archive checked, all old consumers stopped; type RESET: " confirmation
[[ "$confirmation" == RESET ]] || { echo "Stop: reset not approved"; exit 1; }
```


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
source "$HOME/fyp-ethernet-pane.sh"
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

**DELETE / RESET — visually inspect the paths and archived state first.**

```bash
read -r -p "Archive checked, all old consumers stopped; type RESET: " confirmation
[[ "$confirmation" == RESET ]] || { echo "Stop: reset not approved"; exit 1; }
```


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

**DELETE / RESET — visually inspect the paths and archived state first.**

```bash
read -r -p "Archive checked, all old consumers stopped; type RESET: " confirmation
[[ "$confirmation" == RESET ]] || { echo "Stop: reset not approved"; exit 1; }
```


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
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
cd "$REPO/layer3/dashboard"
python3 manage.py showmigrations hitl
python3 manage.py migrate
```

The `HitlIncident` model, including `decided_at`, is managed by Django in `layer3/sqlite_logger/decisions.db`. Clear it through Django. The separate `decisions` table remains active: Auto Executor and HITL actions write it, so clear it too when the existing decision-log database is present.

**DELETE / RESET — confirm the stopped gateway database has been archived.**

```bash
read -r -p "Archive checked; type RESET: " confirmation
[[ "$confirmation" == RESET ]] || { echo "Stop: reset not approved"; exit 1; }
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
source "$HOME/fyp-ethernet-pane.sh"
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
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/validator"
python3 validator.py
```

**Terminal L1-B — ADM Runner / Feature Store**

```bash
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/adm"
python3 adm_runner.py
```

**Terminal L1-C — Fusion Engine (metrics `:8003`)**

```bash
source "$HOME/fyp-ethernet-pane.sh"
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
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/adm"
python3 detectors/error_rate.py
```

```bash
# L1-E — throughput detector, metrics :8005
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/adm"
python3 detectors/throughput_drop.py
```

```bash
# L1-F — authentication detector, metrics :8006
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/adm"
python3 detectors/auth_flood.py
```

```bash
# L1-G — CPU detector, metrics :8007
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/adm"
python3 detectors/cpu_spike.py
```

```bash
# L1-H — schema detector, metrics :8008
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer1/adm"
python3 detectors/schema_drift.py
```

## Phase 2 — Start Layer 2

Every Layer 2 terminal must source Node 2's `~/fyp-run-env.sh`; an export in one terminal does not propagate to the other three.

```bash
source "$HOME/fyp-ethernet-pane.sh"
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
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${LAYER2_EVALUATION_RUN_ID:?LAYER2_EVALUATION_RUN_ID is not set}"
: "${LAYER2_EVALUATION_DIR:?LAYER2_EVALUATION_DIR is not set}"
cd "$REPO/layer2"
python3 agents/triage_agent.py
```

**Terminal L2-B — Strategy Agent (metrics `:8011`)**

```bash
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${LAYER2_EVALUATION_RUN_ID:?LAYER2_EVALUATION_RUN_ID is not set}"
: "${LAYER2_EVALUATION_DIR:?LAYER2_EVALUATION_DIR is not set}"
cd "$REPO/layer2"
python3 agents/strategy_agent.py
```

**Terminal L2-C — Policy Agent (metrics `:8012`)**

```bash
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${LAYER2_EVALUATION_RUN_ID:?LAYER2_EVALUATION_RUN_ID is not set}"
: "${LAYER2_EVALUATION_DIR:?LAYER2_EVALUATION_DIR is not set}"
cd "$REPO/layer2"
python3 agents/policy_agent.py
```

**Terminal L2-D — Learning Agent (metrics `:8013`)**

```bash
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${LAYER2_EVALUATION_RUN_ID:?LAYER2_EVALUATION_RUN_ID is not set}"
: "${LAYER2_EVALUATION_DIR:?LAYER2_EVALUATION_DIR is not set}"
cd "$REPO/layer2"
python3 agents/learning_agent.py
```

Strategy uses structured output. Learning is deterministic; retain its artifacts and the threshold file as evidence rather than changing behavior during a run.

## Phase 3 — Start Layer 3

### Node 3 — `gateway-node`

Start each long-running process in its own terminal.

**Terminal L3-A — Auto Executor (metrics `:8014`)**

```bash
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer3"
python3 auto_executor/executor.py
```

**Terminal L3-B — HITL queue consumer**

```bash
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
cd "$REPO/layer3/dashboard"
python3 manage.py consume_hitl
```

**Terminal L3-C — Django dashboard and HITL metrics**

```bash
source "$HOME/fyp-ethernet-pane.sh"
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
- `SYSTEM / INFRASTRUCTURE HEALTH`
- `HARDWARE / NODE RESOURCES`

## Phase 4 — Pre-Run Verification and Metadata

Do not publish an event until every required consumer is running and the following checks pass.

### Endpoint checks

From an appropriate node with network access to all hosts:

```bash
for endpoint in \
  http://10.10.10.11:8002/metrics \
  http://10.10.10.11:8003/metrics \
  http://10.10.10.11:8004/metrics \
  http://10.10.10.11:8005/metrics \
  http://10.10.10.11:8006/metrics \
  http://10.10.10.11:8007/metrics \
  http://10.10.10.11:8008/metrics \
  http://10.10.10.12:8010/metrics \
  http://10.10.10.12:8011/metrics \
  http://10.10.10.12:8012/metrics \
  http://10.10.10.12:8013/metrics \
  http://10.10.10.13:8014/metrics \
  http://10.10.10.13:8000/metrics
do
  printf '%s: ' "$endpoint"
  curl -fsS "$endpoint" >/dev/null && echo UP || echo DOWN
done
curl -fsS http://10.10.10.13:8000/metrics | grep -E '^fyp_hitl_'
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

## Ethernet transport gate — after startup, BEFORE either workload

On Node 2 and Node 3:

```bash
source "$HOME/fyp-ethernet-pane.sh"
sudo ss -ntp | grep ':5672' | tee "$RUN_ROOT/transport/rabbitmq-sockets-before.txt"
```

Require established remote connections to `10.10.10.11:5672` from `.12`/`.13`. On Node 1:

```bash
source "$HOME/fyp-ethernet-pane.sh"
sudo rabbitmqctl list_connections name peer_host peer_port user vhost | tee "$RUN_ROOT/transport/rabbitmq-peers-before.txt"
sudo rabbitmqctl list_queues -p fyp name consumers messages_ready messages_unacknowledged | tee "$RUN_ROOT/transport/queues-before.txt"
sudo rabbitmqctl list_consumers -p fyp | tee "$RUN_ROOT/transport/consumers-before.txt"
```

Require Node 2/3 peers `10.10.10.12`/`10.10.10.13`, not `192.168.18.102`/`.103`; distinguish Node 1 local connections. Check one intended owner per input queue: Validator/raw.events; ADM/validated.event; five detectors/detect.*; Fusion/fusion.results; Triage/anomaly.detected; Strategy/triage.result; Policy/strategy.result; Auto Executor/auto.execute; HITL consumer/hitl.queue; Learning/outcome.feedback. No Threshold or Single-Agent consumer may compete. `dead.letters` has no required consumer and must be empty. Preserve existing topology; absent queues require the source Phase 1 declaration followed by zero-state verification.

### Effective Prometheus configuration — gateway only

The live config is already migrated. **Do not install the template or reload on every run.** Validate the disk file, then inspect the running server's effective config and targets:

```bash
source "$HOME/fyp-ethernet-pane.sh"
sudo promtool check config /etc/prometheus/prometheus.yml
sudo sha256sum /etc/prometheus/prometheus.yml | tee "$RUN_ROOT/transport/prometheus-disk.sha256"
sha256sum "$REPO/deployment/ethernet/prometheus.ethernet.yml" | tee "$RUN_ROOT/transport/prometheus-template.sha256"
curl -fsS http://localhost:9090/api/v1/status/config > "$RUN_ROOT/transport/prometheus-effective.json"
curl -fsS http://localhost:9090/api/v1/targets > "$RUN_ROOT/transport/prometheus-targets-before.json"
python3 - "$RUN_ROOT/transport/prometheus-targets-before.json" <<'PYTARGET'
import json, sys
from urllib.parse import urlsplit
nodes = {'stream-node':'10.10.10.11', 'ai-brain-node':'10.10.10.12', 'gateway-node':'10.10.10.13'}
required = {'fyp-cluster':3, 'rabbitmq':1, 'fyp-layer1':7,
            'fyp-agent-pipeline':4, 'fyp-layer3-autoexec':1, 'fyp-layer3-hitl':1}
seen = {job:0 for job in required}
for t in json.load(open(sys.argv[1]))['data']['activeTargets']:
    job = t['labels']['job']; instance = t['labels'].get('instance', '')
    url = urlsplit(t['scrapeUrl'])
    print(job, instance, t['scrapeUrl'], t['health'], t.get('lastError', ''))
    if job in {'prometheus', 'node'}:
        continue  # intentionally local identities retained
    name, port = instance.rsplit(':', 1)
    assert name in nodes and url.hostname == nodes[name] and url.port == int(port), t
    if job in required:
        seen[job] += 1
        assert t['health'] == 'up', t
assert seen == required, (seen, required)
PYTARGET
for job in fyp-cluster rabbitmq fyp-layer1 fyp-agent-pipeline fyp-layer3-autoexec fyp-layer3-hitl; do
  curl -fsSG http://localhost:9090/api/v1/query \
    --data-urlencode "query=up{job=\"$job\"}" > "$RUN_ROOT/transport/up-$job.json"
done
```

Wait for initial scrapes before this gate. Review the effective config against `deployment/ethernet/prometheus.ethernet.yml`: global scrape/evaluation 15s; cluster, Layer 1, agents, both baselines and HITL 5s; cluster timeout 5s; RabbitMQ and Auto Executor inherit 15s. All 10 jobs/21 targets and original `hostname:port` labels remain. Local `prometheus`/`node` retain localhost identities. Disk validation alone does not prove what is loaded. Any discrepancy must be resolved before measurement using the reviewed deployment procedure, not by silently copying configuration. Inactive baseline targets may be DOWN.

### Grafana checkpoint

Open the current **Hybrid Agentic Framework — Final Research Observability** dashboard at the existing Grafana URL. Require populated cluster hardware and active application panels and unchanged logical node names. Intentionally inactive controller panels may show “No data.” Do not change datasource or dashboard configuration. The combined network graph includes Wi-Fi Internet traffic and is not sole Ethernet proof.

### Optional bounded packet observation — diagnostic only by default

In a separate pane on each node, start before diagnostic publication. Use `enp2s0` on Nodes 1/2 and `enx00e04c681057` on Node 3:

```bash
source "$HOME/fyp-ethernet-pane.sh"
ETH_IF=enp2s0  # gateway: enx00e04c681057
sudo timeout 120 tcpdump -nn -l -i "$ETH_IF" \
 'net 10.10.10.0/24 and tcp and (port 5672 or portrange 8000-8030 or port 9100 or port 15692)' \
 > "$RUN_ROOT/transport/ethernet-tcpdump-summary.txt" 2>&1
```

For the Wi-Fi side, identify the actual interface via `ip -br addr`; enter it rather than assuming a device name. This filter limits observation to traffic between distinct known FYP Wi-Fi peers, excluding local-host traffic:

```bash
source "$HOME/fyp-ethernet-pane.sh"
ip -br addr
read -r -p 'Actual Wi-Fi interface: ' WIFI_IF
sudo timeout 120 tcpdump -nn -l -i "$WIFI_IF" \
 'tcp and ((host 192.168.18.101 and host 192.168.18.102) or (host 192.168.18.101 and host 192.168.18.103) or (host 192.168.18.102 and host 192.168.18.103)) and (port 5672 or portrange 8000-8030 or port 9100 or port 15692)' \
 > "$RUN_ROOT/transport/wifi-tcpdump-summary.txt" 2>&1
```

Confirm current Wi-Fi addresses before using that optional filter; record any substitutions. Equivalent inter-node FYP packets on Wi-Fi fail the transport check; unrelated Internet traffic does not. Captures end automatically after 120 seconds or with Ctrl+C; timeout exit 124 is normal. Record observation coverage and packet-drop statistics. No payload capture is required. For full runs, use the frozen monitoring policy; do not introduce extra capture load on one condition only.

## Corpus generation — do this once per run directory

SEG’s configured corpus contains **1,950 events**: 1,000 normal, four 200-event anomaly types, and 150 schema-drift events. Generation uses the copied config and writes runtime events without ground truth; it writes corresponding ground truth to a separate CSV. Runtime components never receive the CSV.

**Diagnostic or non-formal engineering validation only. Never use this generation block for a formal matched-network experiment.** For full runs, select the purpose in this setup/replay shell before preparing a corpus:

```bash
read -r -p 'Full run purpose (formal-matched or engineering): ' FULL_RUN_PURPOSE
case "$FULL_RUN_PURPOSE" in formal-matched|engineering) ;; *) exit 1;; esac
export FULL_RUN_PURPOSE
```

A diagnostic does not need this full-run selection. Formal matched runs must skip generation and use Frozen-source reuse below. On Node 1, create a run-specific copy of the SEG config, set its base timestamp, and generate once only for the permitted purposes.

```bash
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${SEG_RUN_DIR:?SEG_RUN_DIR is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
case "$SEG_RUN_DIR" in "$RUN_ROOT/seg") ;; *) echo "Unsafe SEG_RUN_DIR: $SEG_RUN_DIR"; exit 1;; esac
case "$RUN_ID" in
  ethernet-diagnostic-50-*) ;;
  ethernet_cold_*) [[ "${FULL_RUN_PURPOSE:-}" == engineering ]] || { echo 'Stop: generation is engineering-only for full runs'; exit 1; } ;;
  *) exit 1 ;;
esac
printf 'REPO=%s\nRUN_ID=%s\nRUN_ROOT=%s\nSEG_RUN_DIR=%s\n' "$REPO" "$RUN_ID" "$RUN_ROOT" "$SEG_RUN_DIR"
mkdir -p "$SEG_RUN_DIR"
test ! -e "$SEG_RUN_DIR/events_1950.jsonl" && test ! -e "$SEG_RUN_DIR/labels.csv" || { echo "Stop: corpus already exists"; exit 1; }
umask 077
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
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
test -f "$RUN_ROOT/seg/labels.csv" || { echo "Final labels unavailable: $RUN_ROOT/seg/labels.csv"; exit 1; }
ssh spectre206@10.10.10.12 "mkdir -p \$HOME/fyp-pipeline/experiment_runs/$RUN_ID/seg"
scp "$RUN_ROOT/seg/labels.csv" "spectre206@10.10.10.12:fyp-pipeline/experiment_runs/$RUN_ID/seg/labels.csv"
```

Use the same transfer for a diagnostic label subset when that diagnostic is analyzed on Node 2. The label files are offline inputs only; never copy or publish them into RabbitMQ or a runtime component.

### Frozen-source reuse for a matched full run

Fresh generation changes UUID4 event IDs and base timestamps. It is ineligible for a formal matched transport comparison. **Formal matched runs require the same approved source files used for Wi-Fi, unchanged**, including final labels and config, verified against an independently approved SHA-256 manifest before copying and again immediately before replay. Equal event-file bytes preserve event IDs and line order. Replay speed must equal the approved Wi-Fi speed **1**; if that protocol used another speed, stop and resolve the protocol instead of changing this run's speed.

The approved source directory and manifest are runtime inputs not supplied here. Do not generate a new manifest from a fresh corpus and call it frozen evidence. Use an approved `sha256sum`-format manifest with exactly the three bare filenames `events_1950.jsonl`, `labels.csv`, `seg_config.json`, one SHA-256 entry each; obtain a reviewed extract if the original manifest has additional files or paths. On Node 1, before populating `seg/`:

```bash
source "$HOME/fyp-ethernet-pane.sh"
[[ "${FULL_RUN_PURPOSE:-}" == formal-matched ]] || exit 1
read -r -p 'Absolute approved frozen SEG directory: ' FROZEN_SEG
read -r -p 'Absolute independent approved SHA-256 manifest: ' FROZEN_MANIFEST
[[ "$FROZEN_SEG" == /* && "$FROZEN_MANIFEST" == /* ]] || exit 1
read -r -p 'Approved Wi-Fi replay speed: ' FROZEN_REPLAY_SPEED
[[ "$FROZEN_REPLAY_SPEED" == 1 ]] || { echo 'Stop: replay-speed mismatch'; exit 1; }
python3 - "$FROZEN_MANIFEST" <<'PYMANIFEST'
import re, sys
from pathlib import Path
lines = Path(sys.argv[1]).read_text().splitlines()
entries = [re.fullmatch(r'([0-9a-fA-F]{64}) [ *](events_1950\.jsonl|labels\.csv|seg_config\.json)', line) for line in lines]
if len(entries) != 3 or not all(entries) or {m[2] for m in entries} != {'events_1950.jsonl', 'labels.csv', 'seg_config.json'}:
    raise SystemExit('Stop: approved manifest must contain exactly the three required SHA-256 entries')
PYMANIFEST
[[ $? == 0 ]] || exit 1
(cd "$FROZEN_SEG" && sha256sum --check --strict "$FROZEN_MANIFEST") || exit 1
mkdir -p "$SEG_RUN_DIR"
for file in events_1950.jsonl labels.csv seg_config.json; do
  test ! -e "$SEG_RUN_DIR/$file" || { echo 'Stop: destination already populated; do not relabel a generated corpus as formal'; exit 1; }
done
test ! -e "$RUN_ROOT/frozen-manifest.sha256" || exit 1
cp "$FROZEN_MANIFEST" "$RUN_ROOT/frozen-manifest.sha256" || exit 1
for file in events_1950.jsonl labels.csv seg_config.json; do
  cp -p "$FROZEN_SEG/$file" "$SEG_RUN_DIR/$file" || exit 1
done
(cd "$SEG_RUN_DIR" && sha256sum --check --strict "$RUN_ROOT/frozen-manifest.sha256") || exit 1
printf 'source=%s\nmanifest=%s\nreplay_speed=1\n' "$FROZEN_SEG" "$FROZEN_MANIFEST" > "$RUN_ROOT/frozen-source.txt"
export FROZEN_MANIFEST_SHA256=$(sha256sum "$RUN_ROOT/frozen-manifest.sha256" | cut -d ' ' -f 1)
```

Keep this setup/replay shell for the formal publication gate below. Do not modify any of the three copied files or annotate the final labels again. Transfer labels using the Ethernet commands above and verify Node 2's CSV hash against the same approved manifest entry before analysis. Preserve the approved manifest and source record with the run. Runtime SEG config copies may contain existing broker credentials: keep run directories private (umask 077); never commit/share an unredacted config or credential file. Retain the exact private config for hash verification; share only a separately redacted copy when needed.

## Diagnostic subset preparation — existing Wi-Fi rule, unchanged

SEG has no `--limit`. Select the lexicographically first component with at least 20 NORMAL and 30 non-NORMAL source events; emit its first 20 NORMAL then first 30 non-NORMAL, each in original within-group order. The first 19 accepted calibration events are withheld; the twentieth may reach detectors. This is deterministic **for the same frozen input file**, not across newly generated UUIDs. Do not use arbitrary first-50 lines, tune the selection to get preferred routes, or treat this ordering as formal data. Runtime JSONL contains no ground-truth fields; labels remain offline.

```bash
source "$HOME/fyp-ethernet-pane.sh"
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
ssh spectre206@10.10.10.12 "mkdir -p \$HOME/fyp-pipeline/experiment_runs/$RUN_ID/seg"
scp "$DIAG_LABELS" "spectre206@10.10.10.12:fyp-pipeline/experiment_runs/$RUN_ID/seg/labels_50_diagnostic.csv"
```

## Corpus verification — Node 1, select one mode

```bash
source "$HOME/fyp-ethernet-pane.sh"
# Diagnostic:
RUN_MODE=diagnostic
INPUT_EVENTS="$SEG_RUN_DIR/events_50_diagnostic.jsonl"
INPUT_LABELS="$SEG_RUN_DIR/labels_50_diagnostic.csv"
EXPECTED_EVENTS=50
# Full mode instead:
# RUN_MODE=full
# INPUT_EVENTS="$SEG_RUN_DIR/events_1950.jsonl"
# INPUT_LABELS="$SEG_RUN_DIR/labels.csv"
# EXPECTED_EVENTS=1950
python3 - "$INPUT_EVENTS" "$INPUT_LABELS" "$EXPECTED_EVENTS" <<'PYCORPUS'
import csv, json, sys
from collections import Counter
events = [json.loads(x) for x in open(sys.argv[1]) if x.strip()]
labels = list(csv.DictReader(open(sys.argv[2])))
ids = [e['event_id'] for e in events]
assert len(events) == len(set(ids)) == int(sys.argv[3])
assert len(labels) == len(events) and {r['event_id'] for r in labels} == set(ids)
assert all(not any(k.startswith('ground_truth') or k in {'expected_route','safe_to_auto'} for k in e) for e in events)
counts = Counter(e.get('anomaly_type','NORMAL') for e in events)
if len(events) == 1950:
    assert counts == {'NORMAL':1000, 'cpu_memory_spike':200, 'error_rate_surge':200,
                      'throughput_drop':200, 'auth_failure_flood':200, 'schema_drift':150}, counts
else:
    assert len({e['affected_component'] for e in events}) == 1
    assert all(e.get('anomaly_type','NORMAL') == 'NORMAL' for e in events[:20])
    assert all(e.get('anomaly_type','NORMAL') != 'NORMAL' for e in events[20:])
print('events:',len(events),'composition:',dict(counts))
PYCORPUS
sha256sum "$SEG_RUN_DIR/events_1950.jsonl" "$INPUT_EVENTS" "$INPUT_LABELS" "$SEG_RUN_DIR/seg_config.json" | tee "$RUN_ROOT/corpus.sha256"
```

No checksum is prefilled: hash the actual selected source/subset and preserve its source reference. The Validator's structural-schema failures route through `fyp.events` with routing key `anomaly.schema_drift` directly to `anomaly.detected`, bypassing Feature Store/ADM and Fusion; they are not automatically lost events or DLQ. Valid value-shift cases retain the normal detector path. Calibration and Fusion suppression mean input count is not decision count.

Before publication, repeat the complete revision gate on every node and save its output to `transport/revision-before.txt`; require a clean source tree. Record the pre-run cold threshold and model/config references, independent label provenance, review policy, warmup policy and condition/repetition identifier in operator notes. Do not infer missing freeze decisions from this runbook.

### Record reproducibility metadata

On Node 1, before replay, create an operator-owned record in the new run directory. The network medium is fixed to ethernet in this runbook.

```bash
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
case "$RUN_ROOT" in "$REPO/experiment_runs/"*) ;; *) echo "Unsafe RUN_ROOT: $RUN_ROOT"; exit 1;; esac
cd "$REPO"
{
  printf 'recorded_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'run_id=%s\n' "$RUN_ID"
  printf 'network_medium=%s\n' 'ethernet'
  printf 'git_commit=%s\n' "$(git rev-parse HEAD)"
  printf 'deployment_revision=%s\n' 'c0ad6be9c84955240cf4499d586ad46b1d579ecc'
  printf 'run_mode=%s\n' "$RUN_MODE"
  printf 'full_run_purpose=%s\n' "${FULL_RUN_PURPOSE:-not_applicable_diagnostic}"
  printf 'replay_speed=%s\n' '1'
  printf 'corpus=%s\n' "$INPUT_EVENTS"
  printf 'corpus_events=%s\n' "$(wc -l < "$INPUT_EVENTS")"
  printf 'feature_store_baselines=empty_before_replay\n'
  printf 'chroma_documents=0_before_replay\n'
  printf 'initial_ema_threshold=0.65\n'
  printf 'nodes=stream-node,ai-brain-node,gateway-node\n'
  printf 'queues=zero_ready_and_unacknowledged_before_replay\n'
} | tee "$RUN_ROOT/metadata.txt"
```

Select and verify the mode-specific corpus before this metadata command. Run this in the Node 1 setup/replay pane where INPUT_EVENTS and RUN_MODE are set.

## Diagnostic publication — exactly 50 events, once

On Node 1, in the pane used for Corpus verification and metadata:

```bash
[[ "$RUN_MODE" == diagnostic && "$EXPECTED_EVENTS" == 50 ]] || exit 1
cd "$REPO/layer1/seg"
date -u +%Y-%m-%dT%H:%M:%SZ | tee "$RUN_ROOT/start_utc.txt"
set -o pipefail
python3 seg.py --mode replay --config "$SEG_RUN_DIR/seg_config.json" \
  --input "$INPUT_EVENTS" --speed 1 2>&1 | tee "$RUN_ROOT/seg-replay.log"
replay_status=${PIPESTATUS[0]}
printf '%s\n' "$replay_status" > "$RUN_ROOT/seg-exit-status.txt"
date -u +%Y-%m-%dT%H:%M:%SZ | tee "$RUN_ROOT/replay_end_utc.txt"
[[ "$replay_status" == 0 ]] || { echo 'Stop: partial/failed replay; preserve evidence, do not replay into this run'; exit 1; }
```

SEG publication completion does not mean downstream completion. Proceed to Phases 6–7 and reconciliation. AUTO/HITL coverage depends on existing decisions; absence of either is incomplete diagnostic coverage and must be reported without modifying the workload or model.

## Phase 5 — Full 1,950-Event Replay

With the zero-state checklist complete, replay the full corpus from Node 1. The formal branch below requires the approved frozen files and rechecks all hashes immediately before publication; engineering runs are explicitly non-formal. Missing purpose or frozen verification fails closed:

```bash
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${SEG_RUN_DIR:?SEG_RUN_DIR is not set}"
case "$SEG_RUN_DIR" in "$RUN_ROOT/seg") ;; *) echo "Unsafe SEG_RUN_DIR: $SEG_RUN_DIR"; exit 1;; esac
[[ "$RUN_MODE" == full && "$EXPECTED_EVENTS" == 1950 ]] || { echo "Stop: select full mode and verify corpus first"; exit 1; }
case "${FULL_RUN_PURPOSE:-}" in
  formal-matched)
    : "${FROZEN_MANIFEST_SHA256:?Complete approved frozen-source reuse in this shell first}"
    printf '%s  %s\n' "$FROZEN_MANIFEST_SHA256" "$RUN_ROOT/frozen-manifest.sha256" | sha256sum --check --strict || exit 1
    (cd "$SEG_RUN_DIR" && sha256sum --check --strict "$RUN_ROOT/frozen-manifest.sha256") || exit 1
    ;;
  engineering) printf 'NON-FORMAL engineering/full-pipeline validation only\n' ;;
  *) echo 'Stop: select and record full run purpose before corpus preparation'; exit 1 ;;
esac
cd "$REPO/layer1/seg"
date -u +%Y-%m-%dT%H:%M:%SZ | tee "$RUN_ROOT/start_utc.txt"
set -o pipefail
python3 seg.py --mode replay \
  --config "$RUN_ROOT/seg/seg_config.json" \
  --input "$RUN_ROOT/seg/events_1950.jsonl" \
  --speed 1 2>&1 | tee "$RUN_ROOT/seg-replay.log"
replay_status=${PIPESTATUS[0]}
printf '%s\n' "$replay_status" > "$RUN_ROOT/seg-exit-status.txt"
date -u +%Y-%m-%dT%H:%M:%SZ | tee "$RUN_ROOT/replay_end_utc.txt"
[[ "$replay_status" == 0 ]] || { echo 'Stop: failed/partial replay; do not rerun into this state'; exit 1; }
```

SEG adds live `ingestion_time` on replay. Fresh generation is not byte-reproducible because it creates new UUIDs and timestamps. Formal matched runs reuse the verified frozen files and speed 1; preserve those exact files, approved manifest and labels. Freshly generated full runs remain non-formal engineering validation.

## Phase 6 — Monitor and Controlled HITL Interaction

While replay and draining proceed, inspect queue state from `stream-node`:

```bash
watch -n 2 'sudo rabbitmqctl list_queues -p fyp name messages_ready messages_unacknowledged'
```

Use the Django dashboard at `http://10.10.10.13:8000/` to process a controlled subset of pending HITL incidents: approve at least one, reject at least one, and modify at least one where valid incidents are available. Record the IDs and counts in your experiment notes. This demonstrates all three human-decision paths and causes corresponding `outcome.feedback` activity. This subset is a diagnostic workflow. The authoritative Wi-Fi experiment used exhaustive handling: all 469 HITL incidents were decided, with zero pending at completion and 639 total feedback records. Reproducing that completion criterion requires handling every HITL incident.

Monitor the final dashboard and current metrics, including detector processing latency; Fusion published, suppressed, compound, fast-path, correlation-wait, and late-recovery observations; Strategy Schema Validity Rate and timeout rate; policy routing/reasons; Control-Plane Processing Latency; End-to-End Decision Latency; Feedback Completion Latency; Learning Processing Latency; Chroma upserts; EMA threshold; Strategy tokens/sec; Auto Executor outcomes and latency; HITL pending/outcomes; and Human Decision Latency.

## Phase 7 — Drain and Post-Run Analysis

After SEG exits, do **not** stop consumers immediately. Wait for computational backlogs to settle.

```bash
watch -n 2 'sudo rabbitmqctl list_queues -p fyp name messages_ready messages_unacknowledged'
```

The queues `fusion.results`, `anomaly.detected`, `triage.result`, `strategy.result`, `auto.execute`, and `hitl.queue` should drain to zero. The Django consumer drains `hitl.queue` by persisting incidents; human review then resolves those persisted incidents. Database-backed `fyp_hitl_pending_incidents` measures incidents awaiting review, independently of RabbitMQ backlog. A diagnostic subset may leave persisted incidents pending; the authoritative Wi-Fi completion criterion requires zero pending. `outcome.feedback` must drain after AUTO and handled HITL actions.

### Layer 2 offline analysis — full mode only (diagnostic command below)

Run from the repository root on `ai-brain-node` (or from a copy of the same run artifacts and labels):

```bash
source "$HOME/fyp-ethernet-pane.sh"
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
source "$HOME/fyp-ethernet-pane.sh"
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
source "$HOME/fyp-ethernet-pane.sh"
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
source "$HOME/fyp-ethernet-pane.sh"
: "${REPO:?REPO is not set}"
: "${RUN_ID:?RUN_ID is not set}"
: "${RUN_ROOT:?RUN_ROOT is not set}"
: "${LAYER2_EVALUATION_DIR:?LAYER2_EVALUATION_DIR is not set}"
cd "$REPO/layer2"
python3 -c 'from chromadb_utils.client import get_document_count; print("Chroma incident_history documents:", get_document_count())'
cat "$REPO/layer2/config/threshold_config.json"
```

## Phase 8 — Shutdown and Preserve Results

Execute the detailed Reconciliation and evidence capture section below **before** stopping processes; then follow this shutdown order.

1. Capture any required Grafana/Prometheus observations while the services and counters remain live.
2. Stop the long-running consumers with `Ctrl+C` only after the drain and evidence collection are complete.
3. Preserve `experiment_runs/$RUN_ID`, Layer 1 runtime result files, Fusion output, the run-specific corpus, labels, metadata, and Layer 2 analysis artifacts.
4. Prometheus and Grafana may remain running for infrastructure monitoring.
5. Do not commit, push, delete prior run directories, or overwrite this run’s labels after analysis.
## Diagnostic offline analysis — Node 2

Use this instead of the full labels analysis command in Phase 7:

```bash
source "$HOME/fyp-ethernet-pane.sh"
cd "$REPO"
test -f "$RUN_ROOT/seg/labels_50_diagnostic.csv" || exit 1
python3 -m layer2.evaluation.analyze_run \
 --run-dir "$LAYER2_EVALUATION_DIR/$RUN_ID" \
 --ground-truth "$RUN_ROOT/seg/labels_50_diagnostic.csv"
```

It writes `evaluation_summary.json` and `per_event.csv`. Preserve `triage.jsonl`, `strategy.jsonl`, `policy.jsonl`, `feedback.jsonl`, and `learning.jsonl`; inspect missing/duplicate IDs and invalid records, not just totals. Do not use `--expect-hitl-feedback` for sampled human review. For exhaustive full-run review that flag is available, but only after confirming the protocol expects all HITL feedback. Blank independent route/safety labels correctly yield `not_computable` FAR/FER.

## Reconciliation and evidence capture — before stopping services

Record a table in `$RUN_ROOT/reconciliation.txt` with input count, Validator valid/schema/errors, calibration withholding, detector/Fusion outputs (published/suppressed/compound), Triage/Strategy/Policy records, AUTO, HITL, execution outcomes, feedback, Learning records, persisted pending rows, and DLQ. Use the Phase 7 database counts and analyzer outputs plus the snapshots below. Explain differences by event ID, schema bypass, calibration, Fusion behavior, missing/duplicate delivery, or explicit failures. Do not assert 50 input events imply 50 decisions, or 1,950 imply 1,950 incidents. No current Layer 1 final ground-truth CLI exists; do not fabricate TP/FP metrics.

For full completion, every HITL incident must be resolved under the frozen review policy and pending must be zero. For the sampled diagnostic, explicitly record any retained pending rows and the matching ungenerated feedback; an unexplained count is failure. A drained `hitl.queue` does not imply no pending database incidents. Require both ready and unacknowledged counts zero on every experiment queue, including `outcome.feedback`; investigate any `dead.letters` without deleting evidence. Preserve review IDs, approve/reject/modify counts, decision times and operator notes. Do not force the historical Wi-Fi counts.

On Node 1, after computational and human processing settle:

```bash
source "$HOME/fyp-ethernet-pane.sh"
sudo rabbitmqctl list_queues -p fyp name consumers messages_ready messages_unacknowledged | tee "$RUN_ROOT/transport/queues-after.txt"
sudo rabbitmqctl list_connections name peer_host peer_port user vhost | tee "$RUN_ROOT/transport/rabbitmq-peers-after.txt"
mkdir -p "$RUN_ROOT/layer1_runtime"
cp -a "$REPO/layer1/runtime_results/." "$RUN_ROOT/layer1_runtime/"
cp -p "$REPO/layer1/fusion_engine/fusion_results.jsonl" "$RUN_ROOT/layer1_runtime/"
```

If a runtime file is missing, record and investigate rather than creating an empty replacement. On gateway, snapshot all active application metrics while alive:

```bash
source "$HOME/fyp-ethernet-pane.sh"
for target in 10.10.10.11:8002 10.10.10.11:8003 10.10.10.11:8004 10.10.10.11:8005 10.10.10.11:8006 10.10.10.11:8007 10.10.10.11:8008 10.10.10.12:8010 10.10.10.12:8011 10.10.10.12:8012 10.10.10.12:8013 10.10.10.13:8014 10.10.10.13:8000; do
  curl -fsS "http://$target/metrics" > "$RUN_ROOT/metrics/$target.prom" || exit 1
done
curl -fsS http://localhost:9090/api/v1/targets > "$RUN_ROOT/transport/prometheus-targets-after.json"
for metric in fyp_strategy_schema_valid_total fyp_strategy_schema_invalid_total fyp_strategy_timeout_total; do
  curl -fsSG http://localhost:9090/api/v1/query --data-urlencode "query=$metric" > "$RUN_ROOT/metrics/$metric.json"
done
```

Preserve the agreed Prometheus/Grafana time-window export/screenshots for resource and latency analysis; these point-in-time text snapshots alone are not a complete time series. Use the same export/monitoring policy as the matched Wi-Fi run. No repository command establishes a universal Grafana export format.

On each node, set `ETH_IF` to its table value and capture counters, sockets and revision. On Node 2 preserve the final EMA file. Record completion only after the chosen review/drain criterion is met:

```bash
source "$HOME/fyp-ethernet-pane.sh"
ETH_IF=enp2s0  # gateway: enx00e04c681057
ip -s link show dev "$ETH_IF" > "$RUN_ROOT/transport/counters-after.txt"
sudo ss -ntp > "$RUN_ROOT/transport/sockets-after.txt"
cd "$REPO"
{ git branch --show-current; git rev-parse HEAD; git status --short; } > "$RUN_ROOT/transport/revision-after.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$RUN_ROOT/completion_utc.txt"
# Node 2 only:
# cp -p "$REPO/layer2/config/threshold_config.json" "$RUN_ROOT/threshold-final.json"
```

Then stop optional captures and gracefully Ctrl+C all application consumers as in Phase 8 (after drain). Keep infrastructure services running. On gateway, with writers stopped, preserve the database using a consistent backup:

```bash
source "$HOME/fyp-ethernet-pane.sh"
python3 - <<'PYDB'
import os, sqlite3
from pathlib import Path
source = Path(os.environ['REPO']) / 'layer3/sqlite_logger/decisions.db'
target = Path(os.environ['RUN_ROOT']) / 'decisions-final.db'
assert source.exists() and not target.exists()
with sqlite3.connect(f'file:{source}?mode=ro', uri=True) as src, sqlite3.connect(target) as dst:
    src.backup(dst)
PYDB
```

On Nodes 2/3 remove only the session's temporary credentials after all clients stop; on every node remove the temporary bootstrap/run-env files after archival:

```bash
# Nodes 2/3, bootstrap already sourced in this pane:
case "${FYP_RUNTIME_ENV:-}" in /tmp/fyp-runtime.*.env) rm -- "$FYP_RUNTIME_ENV" ;; *) echo 'No recognized credential file; inspect manually' ;; esac
unset RABBITMQ_USER RABBITMQ_PASS
# All nodes, after the last evidence command:
rm -- "$HOME/fyp-ethernet-pane.sh" "$HOME/fyp-run-env.sh"
```

### Artifact inventory and diagnostic PASS/FAIL

Retain the same node-local `experiment_runs/$RUN_ID` layout: Node 1 `seg/`, source/subset hashes, metadata and replay log; Node 2 `layer2_evaluation/$RUN_ID/` and offline summaries/labels; Node 3 SQLite backup and monitoring observations. Additional `transport/`, `metrics/`, timestamps, reconciliation and operator notes live under each node's existing run root. Archive node-local roots separately by node name to avoid overwriting files with the same name. Keep diagnostic and formal IDs/directories separate. Do not commit generated evidence or secrets. Produce a per-node inventory after shutdown:

```bash
# Run before removing fyp-run-env.sh, or retain RUN_ROOT in the current shell.
find "$RUN_ROOT" -type f ! -name artifact-sha256.txt -exec sha256sum {} \; > "$RUN_ROOT/artifact-sha256.txt"
```

Diagnostic PASS requires all of these; mark missing evidence/coverage INCOMPLETE, observed violations FAIL:

- [ ] Intended services started, no tracebacks/crashes or competing controller ownership; expected consumers present.
- [ ] Exactly 50 unique selected inputs, matching 50 offline label IDs, successful single replay; all accounted for without pretending calibration/suppression is loss.
- [ ] AUTO and HITL exercised; controlled approve/reject/modify paths recorded where valid incidents exist. Missing coverage is recorded, never manufactured by tuning.
- [ ] Queue ready/unacknowledged backlogs drained; no unexplained DLQ; persisted HITL pending and feedback reconcile under the chosen diagnostic review scope.
- [ ] Node 2/3 broker sockets and peers use Ethernet, all active Prometheus URLs use Ethernet with original labels, all required exporters/services UP.
- [ ] Ethernet routes/link/counters, peer/socket/scrape evidence saved; no observed unintended inter-node FYP Wi-Fi traffic. If optional capture was omitted, state the scope of route/socket evidence instead of claiming exhaustive packet absence.
- [ ] Grafana hardware/active panels work; exact revision, timestamps, corpus hashes, final state and artifact inventory saved.

There are no model-quality or research-performance thresholds for this smoke test.

## Later Threshold-only and Single-Agent conditions

Use their dedicated runbooks on their reviewed branches, not copied controller commands here. They are absent from this frozen Proposed checkout; verify the actual branch files before following them. Apply only reviewed deployment settings: Node 2/3 Ethernet environment, gateway allowlist/dependency fix and unchanged labeled Prometheus template. Record each controller revision and the deployment-profile revision separately; do not demand the Proposed commit for a different controller or merge their implementations into this branch. Preserve each controller's state/model/evaluation semantics.

| Condition | Node 2 metrics | Broker | Model |
|---|---|---|---|
| Proposed | 10.10.10.12:8010–8013 | 10.10.10.11:5672, vhost fyp | localhost:11434 |
| Threshold-only | 10.10.10.12:8020 | same | inactive |
| Single-Agent | 10.10.10.12:8030 | same | localhost:11434 |

Only one controller owns shared queues. Adapt the active-job preflight accordingly; never start inactive controllers to turn monitoring green. Common Ethernet profiles remain the source of non-secret endpoints. The primary controller comparison requires the separately frozen identical incident dataset; this 1,950-event full-pipeline procedure cannot substitute for that protocol.

## Optional Wi-Fi rollback — outside measurement

Gracefully stop Ethernet applications after drain/evidence collection. Preserve the active Ethernet config if needed. On gateway, only if deliberately restoring Wi-Fi monitoring:

```bash
sudo promtool check config /etc/prometheus/prometheus.yml.backup-wifi-20260924
sudo cp -p /etc/prometheus/prometheus.yml.backup-wifi-20260924 /etc/prometheus/prometheus.yml
sudo promtool check config /etc/prometheus/prometheus.yml
sudo systemctl reload prometheus
curl -fsS http://localhost:9090/api/v1/status/config
curl -fsS http://localhost:9090/api/v1/targets
```

Do not reload after failed validation; use the established deployment reload procedure if the service lacks reload support. Start fresh application panes without the Ethernet bootstrap/profile; ensure inherited `RABBITMQ_HOST`/`RABBITMQ_PORT` are unset and the prior protected Wi-Fi launch environment restored. Verify actual hostname resolution, broker sockets/peers and Wi-Fi scrape URLs before publication. Logical labels remain unchanged; Grafana needs no edits. Do not disable Wi-Fi, edit `/etc/hosts`, or roll back Git. Use a new run identity if starting a new workload.
