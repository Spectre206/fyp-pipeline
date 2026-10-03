# Threshold Ethernet Mode B — diagnostic and frozen full run

Prepared procedure, not an execution record. No experiment has been run by this
migration. Follow the [shared contract](../ETHERNET_SHARED_EXPERIMENT_CONTRACT.md)
and its final routing metrics. The legacy Threshold runbook/analyzer remains
historical for final Ethernet scoring. Never launch proposed agents, Chroma,
EMA or a model for Threshold. No live incident capture consumer is used.

Use Bash. Execute **one mode**, then archive and restart from Phase 0 for the
other. Diagnostic evidence is integration evidence only. A diagnostic PASS
never authorizes a formal run by itself. All application commands below are
foreground processes in separate panes. Do not paste all blocks as one script.

| Node | Address/interface | Role |
|---|---|---|
| stream-node | 10.10.10.11 / enp2s0 | RabbitMQ, SEG, unchanged Layer 1 |
| ai-brain-node | 10.10.10.12 / enp2s0 | Threshold + accounting workers, :8020 |
| gateway-node | 10.10.10.13 / enx00e04c681057 | Auto Executor :8014, HITL/Django :8000, monitoring |

## Phase 0 — reviewed freeze, identity, inputs and revision

Before any reset, select a reviewed full controller commit on
`experiment/threshold-baseline` on every node. The migration's starting commit
was `1df34773e27a2f80a8d3fb340c5afa06c92e501d`; it does **not** include these
uncommitted adaptations. Review/commit/distribute the adaptation first using the
normal process. No command here stages, commits, pushes, pulls or bypasses the
clean-tree requirement. Record the actual approved full commit, not that starting
hash. Freeze review scope, repetition/order, clocks, cutoff/drain timeout and
failure/rerun criteria in `protocol-freeze.txt` before publication. For formal
runs use exhaustive HITL completion unless the approved comparison says otherwise.

On Node 1 choose one unique ID, then copy its literal value to Nodes 2 and 3:

```bash
RUN_ID="threshold-ethernet-diagnostic-$(date -u +%Y%m%d-%H%M%S)"
# Formal mode instead, selected before setup:
# RUN_ID="threshold-ethernet-full-$(date -u +%Y%m%d-%H%M%S)"
printf '%s\n' "$RUN_ID"
```

On each node, in the setup pane (Nodes 2/3 first `read -r -p 'Exact RUN_ID: ' RUN_ID`):

```bash
export REPO="$HOME/fyp-pipeline"
cd "$REPO" || exit 1
[[ "$RUN_ID" =~ ^threshold-ethernet-(diagnostic|full)-[0-9]{8}-[0-9]{6}$ ]] || exit 1
read -r -p 'Node number (1/2/3): ' NODE
[[ "$NODE" =~ ^[123]$ ]] || exit 1
read -r -p 'Absolute existing Python environment on THIS node: ' EXPERIMENT_VENV
[[ "$EXPERIMENT_VENV" == /* && -f "$EXPERIMENT_VENV/bin/activate" ]] || exit 1
export RUN_ID NODE EXPERIMENT_VENV
export RUN_ROOT="$REPO/experiment_runs/$RUN_ID"
export SEG_RUN_DIR="$RUN_ROOT/seg"
export RUN_BASE="$REPO/evaluation/baselines/results/threshold_only/ethernet/$RUN_ID"
test ! -e "$RUN_ROOT" && test ! -e "$RUN_BASE" || exit 1
umask 077
mkdir -p "$RUN_ROOT/seg" "$RUN_ROOT/transport" "$RUN_ROOT/metrics" "$RUN_ROOT/offline_eval_inputs" "$RUN_BASE"
# Only this runtime directory; never hide source/config changes.
printf '/experiment_runs/%s/\n' "$RUN_ID" >> "$(git rev-parse --git-path info/exclude)"
# Baseline results already have a repository runtime .gitignore; inspect it.
cat evaluation/baselines/results/.gitignore
{
  printf 'export REPO=%q RUN_ID=%q NODE=%q EXPERIMENT_VENV=%q\n' "$REPO" "$RUN_ID" "$NODE" "$EXPERIMENT_VENV"
  cat <<'ENV'
export RUN_ROOT="$REPO/experiment_runs/$RUN_ID"
export SEG_RUN_DIR="$RUN_ROOT/seg"
export RUN_BASE="$REPO/evaluation/baselines/results/threshold_only/ethernet/$RUN_ID"
export NETWORK_MEDIUM=ethernet
source "$EXPERIMENT_VENV/bin/activate"
export PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}"
if [[ "$NODE" == 1 ]]; then
  export LAYER1_BASELINES_DIR="$REPO/layer1/feature_store/baselines"
  export LAYER1_RESULTS_DIR="$REPO/layer1/runtime_results"
elif [[ "$NODE" == 2 ]]; then
  source "$REPO/deployment/ethernet/node2.env.sh"
elif [[ "$NODE" == 3 ]]; then
  source "$REPO/deployment/ethernet/node3.env.sh"
  export DJANGO_SETTINGS_MODULE=evaluation.baselines.common.presentation_settings
fi
if [[ "$NODE" != 1 ]]; then
  set +x
  read -r -p 'RabbitMQ user: ' RABBITMQ_USER
  read -r -s -p 'RabbitMQ password: ' RABBITMQ_PASS
  printf '\n'
  export RABBITMQ_USER RABBITMQ_PASS
fi
ENV
} > "$HOME/fyp-threshold-pane.sh"
chmod 600 "$HOME/fyp-threshold-pane.sh"
source "$HOME/fyp-threshold-pane.sh"
```

Every new pane starts with `source "$HOME/fyp-threshold-pane.sh"`; credential
entry is local to each pane and never written to disk. The generic Node 2 profile
also exports local OLLAMA_HOST; Threshold never reads it or starts a model.
Do not dump environments. Dependency upgrades belong before the freeze.

**Immutable inputs, Node 1:** obtain the preserved approved corpus directory and
independently approved `sha256sum` manifest containing the four bare filenames
below. Source labels remain untouched; use the already frozen derived labels.
Do not generate new source events or infer annotations from decisions.

```bash
read -r -p 'Absolute approved frozen input directory: ' FROZEN_INPUTS
read -r -p 'Absolute approved four-file checksum manifest: ' INPUT_MANIFEST
[[ "$FROZEN_INPUTS" == /* && "$INPUT_MANIFEST" == /* ]] || exit 1
(cd "$FROZEN_INPUTS" && sha256sum --check --strict "$INPUT_MANIFEST") || exit 1
for f in events_1950.jsonl seg_config.json labels.csv labels_routing.csv; do
  test -f "$FROZEN_INPUTS/$f" && test ! -e "$SEG_RUN_DIR/$f" || exit 1
  cp -p "$FROZEN_INPUTS/$f" "$SEG_RUN_DIR/$f" || exit 1
  cmp "$FROZEN_INPUTS/$f" "$SEG_RUN_DIR/$f" || exit 1
done
cp "$INPUT_MANIFEST" "$RUN_ROOT/frozen-inputs.sha256"
(cd "$SEG_RUN_DIR" && sha256sum --check --strict "$RUN_ROOT/frozen-inputs.sha256") || exit 1
```

Transfer only labels plus checksum provenance to Node 2 and gateway for offline
analysis/revision checks. From Node 1, once those run directories exist:

```bash
cd "$SEG_RUN_DIR"
sha256sum labels.csv labels_routing.csv > labels-transfer.sha256
read -r -p 'Node 2 SSH user@10.10.10.12: ' NODE2_SSH
read -r -p 'Gateway SSH user@10.10.10.13: ' NODE3_SSH
for destination in "$NODE2_SSH" "$NODE3_SSH"; do
  remote="fyp-pipeline/experiment_runs/$RUN_ID/seg"
  ssh "$destination" "test -d \"\$HOME/$remote\" && test ! -e \"\$HOME/$remote/labels.csv\" && test ! -e \"\$HOME/$remote/labels_routing.csv\"" || exit 1
  scp labels.csv labels_routing.csv labels-transfer.sha256 "$destination:$remote/" || exit 1
  ssh "$destination" "cd \"\$HOME/$remote\" && sha256sum --check --strict labels-transfer.sha256 && sha256sum labels.csv labels_routing.csv" \
    > "$RUN_ROOT/transport/labels-copy-${destination##*@}.txt" || exit 1
done
```

Never substitute the source node's absolute home path for a remote path. Keep
SEG configuration private; it may contain existing broker credentials.

**Revision manifest:** prepare and review a per-node JSON using the schema in
the shared contract. It must include controller_branch, full controller_commit,
shared_evaluation_revision, deployment_profile_revision, routing_policy_revision,
review_reference and the four file-inventory groups. Add these Threshold fields:

```json
{
  "controller": "threshold_only",
  "network_medium": "ethernet",
  "replay_speed": 1,
  "node": "stream-node",
  "frozen_input_hashes": {
    "events_1950.jsonl": "APPROVED_SHA256",
    "seg_config.json": "APPROVED_SHA256",
    "labels.csv": "APPROVED_SHA256",
    "labels_routing.csv": "APPROVED_SHA256"
  }
}
```

Merge these keys into the complete shared manifest, not a standalone JSON above.
Use ai-brain-node/gateway-node on those nodes. `files.corpus` lists all four local
SEG files on Node 1, and the two CSVs on Nodes 2/3; frozen_input_hashes records
all four on every node. Source paths are repository-relative.

`files.shared_evaluation` must include shared evaluate.py, verify_revision.py
and threshold_only/ethernet_checks.py; review/include their tests and other
scaffolding too. `files.deployment` includes both node profiles, the Ethernet
Prometheus template, gateway settings and requirements, and the two gateway
HITL source files whose imports now resolve the node-local Layer 3 directory. `files.routing_policy`
includes the unchanged generator and policy specification. Each group records
hashes matching the declared full source revision. Record rules.py/rules.json
hashes and the dedicated dashboard/runbook in the reviewed inventory as well.
Do not make approved hashes from an unreviewed working tree. The manifest is an
operator-reviewed input; this document cannot preapprove a future commit.

On **every node**, copy that reviewed manifest to
`$RUN_ROOT/approved-revision.json`, then run:

```bash
cd "$REPO"
python -B -m evaluation.baselines.threshold_only.ethernet_checks revision \
  --repo "$REPO" --manifest "$RUN_ROOT/approved-revision.json" \
  > "$RUN_ROOT/transport/revision-before.json" || exit 1
sha256sum "$RUN_ROOT/approved-revision.json" > "$RUN_ROOT/transport/revision-manifest.sha256"
```

This wraps the shared verifier, adds Threshold identity/inventory checks and
allows a reviewed controller commit instead of the obsolete proposed one-file
exception. It does not approve a manifest or certify installed external state.
Repeat before publication. Stop on a dirty tree, mismatched hash or missing file.

## Phase 1 — archive and cold reset (destructive, operator executed)

First stop all old publishers/application consumers gracefully, including
Threshold and gateway writers. No proposed agents or capture consumers may run.
Keep infrastructure services available. Archive old run roots and journals
separately; never reuse controller/replay/analysis directories. Choose a unique
protected archive **outside the checkout** on each node and record its path.

Node 1:

```bash
source "$HOME/fyp-threshold-pane.sh"
read -r -p 'New absolute archive directory outside repository: ' ARCHIVE
export ARCHIVE
python - <<'PY'
import os
from pathlib import Path
p=Path(os.environ['ARCHIVE']);repo=Path(os.environ['REPO']).resolve()
assert p.is_absolute()
p=p.resolve()
assert not p.is_relative_to(repo) and not p.exists()
p.mkdir(parents=True,mode=0o700)
PY
for relative in layer1/feature_store/baselines layer1/runtime_results layer1/fusion_engine/fusion_results.jsonl; do
  if test -e "$REPO/$relative"; then
    mkdir -p "$ARCHIVE/$(dirname "$relative")"
    cp -a "$REPO/$relative" "$ARCHIVE/$relative" || exit 1
  fi
done
printf '%s\n' "$ARCHIVE" > "$RUN_ROOT/prior-state-archive.txt"
sudo rabbitmqctl list_consumers -p fyp
# STOP unless all old application consumers/publishers are confirmed stopped.
read -r -p 'Archive verified, old applications stopped; type RESET: ' answer
[[ "$answer" == RESET ]] || exit 1
python - <<'PY'
import os
from pathlib import Path
repo=Path(os.environ['REPO']).resolve()
for relative in ['layer1/feature_store/baselines','layer1/runtime_results','layer1/fusion_engine']:
 p=repo/relative
 assert p.resolve()==p, 'Refuse symlinked reset directory'
 p.mkdir(parents=True,exist_ok=True)
for p in (repo/'layer1/feature_store/baselines').glob('*.json'):p.unlink()
for name in ['error','throughput','auth','cpu','schema']:
 (repo/f'layer1/runtime_results/{name}_results.jsonl').unlink(missing_ok=True)
(repo/'layer1/fusion_engine/fusion_results.jsonl').unlink(missing_ok=True)
PY
cd "$REPO/layer1/rabbitmq"
python setup_topology.py
for queue in raw.events validated.event detect.cpu detect.error detect.throughput detect.auth detect.schema fusion.results anomaly.detected triage.result strategy.result auto.execute hitl.queue outcome.feedback dead.letters; do
  sudo rabbitmqctl purge_queue -p fyp "$queue" || exit 1
done
sudo rabbitmqctl list_queues -p fyp name messages_ready messages_unacknowledged
```

Require every listed queue zero ready/unacknowledged. Do not purge a live failed
run to make it look successful. Calibration is empty; first 19 accepted events
per component are withheld, and fresh ADM processes clear in-memory windows.

Node 2: preserve old results; confirm `$RUN_BASE/controller` and the new analysis
directory do not exist. No Chroma, EMA or model reset applies.

Gateway, with all database writers stopped:

```bash
source "$HOME/fyp-threshold-pane.sh"
read -r -p 'New absolute database backup outside repository: ' DB_ARCHIVE
export DB_ARCHIVE
python - <<'PY'
import os,sqlite3
from pathlib import Path
repo=Path(os.environ['REPO']).resolve();dest=Path(os.environ['DB_ARCHIVE'])
assert dest.is_absolute() and not dest.resolve().is_relative_to(repo) and not dest.exists()
source=repo/'layer3/sqlite_logger/decisions.db'
if source.exists():
 with sqlite3.connect(f'file:{source}?mode=ro',uri=True) as src,sqlite3.connect(dest) as dst:src.backup(dst)
 with sqlite3.connect(dest) as db:assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
else:print('No previous database; record this in operator notes.')
PY
cd "$REPO/layer3/dashboard"
python manage.py migrate
read -r -p 'Backup verified, writers stopped; type RESET: ' answer
[[ "$answer" == RESET ]] || exit 1
python manage.py shell -c 'from hitl.models import HitlIncident; print(HitlIncident.objects.all().delete())'
python - <<'PY'
import os,sqlite3
from pathlib import Path
path=Path(os.environ['REPO'])/'layer3/sqlite_logger/decisions.db'
with sqlite3.connect(path) as db:
 if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='decisions'").fetchone():
  db.execute('DELETE FROM decisions');db.commit()
PY
python manage.py shell -c 'from hitl.models import HitlIncident; assert HitlIncident.objects.count()==0; print("HITL zero")'
```

## Phase 2 — infrastructure and shared gateway

Verify the existing RabbitMQ service on Node 1 and exporters on every node are
healthy using their established service procedures. Do not reinstall or tune
infrastructure during a measurement. On gateway, review/install the Ethernet
Prometheus template only if needed using `deployment/ethernet/README.md`; validate
with promtool and inspect effective configuration. Preserve the previous config.
No automatic deployment command runs from the helper scripts.

Gateway uses three separate panes, each beginning with the bootstrap:

```bash
# Gateway AUTO pane
source "$HOME/fyp-threshold-pane.sh"
cd "$REPO/layer3"
python auto_executor/executor.py
```

```bash
# Gateway HITL consumer pane
source "$HOME/fyp-threshold-pane.sh"
cd "$REPO/layer3/dashboard"
python manage.py consume_hitl
```

```bash
# Gateway Django pane
source "$HOME/fyp-threshold-pane.sh"
cd "$REPO/layer3/dashboard"
python manage.py runserver 0.0.0.0:8000 --noreload
```

Use `http://10.10.10.13:8000`. The presentation overlay retains neutral Threshold
rendering and inserts node-local repository paths; no proposed agents execute
behind the compatibility envelope's legacy serialization keys.

## Phase 3 — unchanged Layer 1 on Node 1

Each row is a separate persistent pane. Start with the bootstrap and change to
the indicated path beneath REPO. Do not start SEG yet.

| Process | Directory | Command | Metrics |
|---|---|---|---|
| Validator | layer1/validator | python validator.py | 8002 |
| ADM/Feature Store | layer1/adm | python adm_runner.py | — |
| Fusion | layer1/fusion_engine | python fusion_engine.py | 8003 |
| Error | layer1/adm | python detectors/error_rate.py | 8004 |
| Throughput | layer1/adm | python detectors/throughput_drop.py | 8005 |
| Authentication | layer1/adm | python detectors/auth_flood.py | 8006 |
| CPU | layer1/adm | python detectors/cpu_spike.py | 8007 |
| Schema | layer1/adm | python detectors/schema_drift.py | 8008 |

For example:

```bash
source "$HOME/fyp-threshold-pane.sh"
cd "$REPO/layer1/validator"
python validator.py
```

## Phase 4 — Threshold on Node 2

In its own pane, supply the approved source corpus digest from the reviewed
manifest, even for the diagnostic (record the selected subset digest separately):

```bash
source "$HOME/fyp-threshold-pane.sh"
cd "$REPO"
DATASET_SHA256=$(python -c 'import json,os; from pathlib import Path; print(json.loads((Path(os.environ["RUN_ROOT"])/"approved-revision.json").read_text())["frozen_input_hashes"]["events_1950.jsonl"])')
test ! -e "$RUN_BASE/controller" || exit 1
python -m evaluation.baselines.threshold_only.controller \
  --live --run-id "$RUN_ID" --output "$RUN_BASE/controller" \
  --network-medium ethernet --dataset-sha256 "$DATASET_SHA256"
```

Metrics bind 0.0.0.0:8020. Controller and feedback workers have separate AMQP
connections and exclusive subscriptions. The CLI's dataset digest is provenance,
not an automatic verifier of arriving payloads. No runtime ground truth is read.

## Phase 5 — readiness and Ethernet transport gate

Node 1, save and review:

```bash
source "$HOME/fyp-threshold-pane.sh"
sudo rabbitmqctl list_queues -p fyp name consumers messages_ready messages_unacknowledged | tee "$RUN_ROOT/transport/queues-before.txt"
sudo rabbitmqctl list_consumers -p fyp | tee "$RUN_ROOT/transport/consumers-before.txt"
sudo rabbitmqctl list_connections name peer_host peer_port user vhost | tee "$RUN_ROOT/transport/broker-peers-before.txt"
```

Require exactly one intended consumer per active input: Validator/raw.events,
ADM/validated.event, five detectors/detect.*, Fusion/fusion.results,
Threshold/anomaly.detected, Auto Executor/auto.execute, HITL/hitl.queue,
Threshold accounting/outcome.feedback. Require zero consumers on triage.result,
strategy.result and dead.letters, and all experiment queues empty before replay.
Verify process identities manually; counts alone do not prove controller identity.

Each node selects its actual table interface and peers, then records:

```bash
source "$HOME/fyp-threshold-pane.sh"
case "$NODE" in
  1) ETH_IF=enp2s0; PEERS='10.10.10.12 10.10.10.13' ;;
  2) ETH_IF=enp2s0; PEERS='10.10.10.11 10.10.10.13' ;;
  3) ETH_IF=enx00e04c681057; PEERS='10.10.10.11 10.10.10.12' ;;
esac
for peer in $PEERS; do ip route get "$peer"; done | tee "$RUN_ROOT/transport/routes-before.txt"
sudo ethtool "$ETH_IF" | tee "$RUN_ROOT/transport/link.txt"
ip -s link show "$ETH_IF" > "$RUN_ROOT/transport/counters-before.txt"
sudo ss -ntp > "$RUN_ROOT/transport/sockets-before.txt"
timedatectl status > "$RUN_ROOT/transport/clock-before.txt"
```

Require Ethernet peer routes, 1000Mb/s full duplex/link up, Node 2/3 established
broker sockets to .11:5672 and matching .12/.13 peers. Confirm clock sync against
the frozen tolerance using the existing clock tooling; no tolerance is invented
here. Wi-Fi stays enabled for Internet access. Node 1 co-located traffic is local.

Gateway, after initial scrapes:

```bash
source "$HOME/fyp-threshold-pane.sh"
cd "$REPO"
curl -fsS http://10.10.10.12:8020/metrics > "$RUN_ROOT/metrics/threshold-before.prom" || exit 1
rg 'fyp_threshold_worker_up' "$RUN_ROOT/metrics/threshold-before.prom"
# Both controller and feedback gauges must equal 1.
sudo promtool check config /etc/prometheus/prometheus.yml || exit 1
curl -fsS http://localhost:9090/api/v1/status/config > "$RUN_ROOT/transport/prometheus-effective.json" || exit 1
curl -fsS http://localhost:9090/api/v1/targets > "$RUN_ROOT/transport/prometheus-targets-before.json" || exit 1
python -B -m evaluation.baselines.threshold_only.ethernet_checks targets \
 --input "$RUN_ROOT/transport/prometheus-targets-before.json" || exit 1
```

The reviewed template has 21 targets; 16 are required for Threshold Mode B:
Layer 1 seven, Threshold one, Layer 3 two, RabbitMQ one, cluster exporters three,
local Prometheus and node jobs two. Proposed agents four and Single-Agent one
are intentionally inactive. The checker validates exact identities/URLs/health,
not a blind count. It does not prove inactive processes are absent: check queues.

Load the dedicated `observability/FYP_Threshold_Baseline_Observability.json` in
Grafana using the existing datasource. Check Threshold, shared Layer 1/3, hardware,
NTP, backlog and DLQ panels. Select Mode B. Its job selectors now match the shared
Ethernet template; no proposed-agent panels are required. Do not install the
legacy prometheus.threshold.yml over the Ethernet configuration.

## Phase 6 — verify frozen source; select full or isolated diagnostic

Node 1, in the setup/replay pane:

```bash
source "$HOME/fyp-threshold-pane.sh"
cd "$REPO"
python -B -m evaluation.baselines.threshold_only.ethernet_checks corpus \
 --directory "$SEG_RUN_DIR" --manifest "$RUN_ROOT/approved-revision.json" \
 > "$RUN_ROOT/corpus-verification.json" || exit 1
case "$RUN_ID" in
  threshold-ethernet-full-*)
    INPUT_EVENTS="$SEG_RUN_DIR/events_1950.jsonl"
    INPUT_LABELS="$SEG_RUN_DIR/labels_routing.csv"
    EXPECTED_EVENTS=1950 ;;
  threshold-ethernet-diagnostic-*)
    python -B -m evaluation.baselines.threshold_only.prepare_ethernet_diagnostic \
      --corpus "$SEG_RUN_DIR/events_1950.jsonl" --labels "$SEG_RUN_DIR/labels_routing.csv" \
      --output "$RUN_ROOT/diagnostic" || exit 1
    INPUT_EVENTS="$RUN_ROOT/diagnostic/events_50_diagnostic.jsonl"
    INPUT_LABELS="$RUN_ROOT/diagnostic/labels_routing_50_diagnostic.csv"
    EXPECTED_EVENTS=50 ;;
  *) exit 1 ;;
esac
export INPUT_EVENTS INPUT_LABELS EXPECTED_EVENTS
sha256sum "$INPUT_EVENTS" "$INPUT_LABELS" > "$RUN_ROOT/selected-inputs.sha256"
```

The diagnostic uses the first sorted component with 20 NORMAL and 30 anomalous
source events, in original within-group order; no synthetic preferred routes
are injected. Selection is offline; labels never appear in event payloads.
Transfer the diagnostic CSV to Node 2 under the same node-relative run path with
its checksum using the Phase 0 pattern. For example, from Node 1:

```bash
if [[ "$EXPECTED_EVENTS" == 50 ]]; then
  cd "$RUN_ROOT/diagnostic"
  sha256sum labels_routing_50_diagnostic.csv > diagnostic-labels.sha256
  remote="fyp-pipeline/experiment_runs/$RUN_ID/offline_eval_inputs"
  ssh "$NODE2_SSH" "test ! -e \"\$HOME/$remote/labels_routing_50_diagnostic.csv\"" || exit 1
  scp labels_routing_50_diagnostic.csv diagnostic-labels.sha256 "$NODE2_SSH:$remote/" || exit 1
  ssh "$NODE2_SSH" "cd \"\$HOME/$remote\" && sha256sum --check --strict diagnostic-labels.sha256" || exit 1
fi
```

No guarantee of AUTO/HITL coverage is manufactured. If the diagnostic does not
exercise both, record INCOMPLETE and design a separately reviewed diagnostic;
do not add events or tune rules in the same run.

## Phase 7 — metadata and final source check

Every node reruns Phase 0's revision gate and saves fresh output before input.
Node 1 rechecks the frozen corpus command. Record metadata on every node:

```bash
cd "$REPO"
{
  printf 'timestamp=%s\nrun_id=%s\nnode=%s\n' "$(date -u +%FT%TZ)" "$RUN_ID" "$(hostname)"
  printf 'branch=%s\ncommit=%s\n' "$(git branch --show-current)" "$(git rev-parse HEAD)"
  printf 'controller=threshold_only\nnetwork_medium=ethernet\nevaluation_mode=B\nreplay_speed=1\n'
  printf 'run_root=%s\ncontroller_path=%s\n' "$RUN_ROOT" "$RUN_BASE/controller"
  sha256sum "$RUN_ROOT/approved-revision.json" "$SEG_RUN_DIR/labels.csv" "$SEG_RUN_DIR/labels_routing.csv"
  sha256sum evaluation/baselines/threshold_only/rules.py evaluation/baselines/threshold_only/rules.json
} > "$RUN_ROOT/metadata.txt"
python -m pip freeze > "$RUN_ROOT/dependencies.txt"
```

Node 1 appends source/config hashes and actual selected count:

```bash
sha256sum "$SEG_RUN_DIR/events_1950.jsonl" "$SEG_RUN_DIR/seg_config.json" "$INPUT_EVENTS" >> "$RUN_ROOT/metadata.txt"
printf 'selected_events=%s\n' "$EXPECTED_EVENTS" >> "$RUN_ROOT/metadata.txt"
```

Save a completed cold-state/ownership/transport/clock checklist and the approved
cutoff, human-review and monitoring protocol; do not merely prefill “cold=true”.

## Phase 8 — single replay (operator execution only)

Node 1, same setup/replay pane with selected variables intact:

```bash
case "$RUN_ID" in
 threshold-ethernet-full-*) [[ "$EXPECTED_EVENTS" == 1950 && "$INPUT_EVENTS" == "$SEG_RUN_DIR/events_1950.jsonl" ]] || exit 1 ;;
 threshold-ethernet-diagnostic-*) [[ "$EXPECTED_EVENTS" == 50 && "$INPUT_EVENTS" == "$RUN_ROOT/diagnostic/events_50_diagnostic.jsonl" ]] || exit 1 ;;
 *) exit 1 ;;
esac
(cd "$SEG_RUN_DIR" && sha256sum --check --strict "$RUN_ROOT/frozen-inputs.sha256") || exit 1
sha256sum --check --strict "$RUN_ROOT/selected-inputs.sha256" || exit 1
# Exclusive marker: even a failed invocation cannot be repeated in this state.
(set -o noclobber; date -u +%FT%TZ > "$RUN_ROOT/replay-started.txt") || exit 1
cd "$REPO/layer1/seg"
set -o pipefail
python3 seg.py --mode replay --config "$SEG_RUN_DIR/seg_config.json" \
  --input "$INPUT_EVENTS" --speed 1 2>&1 | tee "$RUN_ROOT/seg-replay.log"
replay_status=${PIPESTATUS[0]}
printf '%s\n' "$replay_status" > "$RUN_ROOT/seg-exit-status.txt"
date -u +%FT%TZ > "$RUN_ROOT/replay-ended.txt"
[[ "$replay_status" == 0 ]] || { echo 'FAILED replay: preserve state; never resume this run'; exit 1; }
```

Do not replay raw source events directly into anomaly.detected. Layer 1 produces
both Fusion incidents and Validator structural bypass incidents normally.

## Phase 9 — drain, human review and flush

On Node 1 observe ready/unacknowledged counts until all experiment queues drain;
use the frozen cutoff and preserve any failure rather than waiting indefinitely.
On gateway handle HITL according to the reviewed protocol. For exhaustive runs,
require zero pending and feedback drained. In the diagnostic exercise AUTO and
HITL, record human actions where valid; do not force outcomes. Check no DLQ,
worker failures, wrong ownership or unexplained duplicate IDs.

```bash
sudo rabbitmqctl list_queues -p fyp name consumers messages_ready messages_unacknowledged
# Gateway, bootstrapped pane:
cd "$REPO/layer3/dashboard"
python manage.py shell -c 'from hitl.models import HitlIncident; from collections import Counter; print(dict(Counter(HitlIncident.objects.values_list("status",flat=True)))); print("pending",HitlIncident.objects.filter(status="PENDING").count())'
```

Before shutdown, save final queue state on Node 1 and live metric/target evidence
on gateway (new bootstrapped panes):

```bash
# Node 1
sudo rabbitmqctl list_queues -p fyp name consumers messages_ready messages_unacknowledged > "$RUN_ROOT/transport/queues-after.txt"
sudo rabbitmqctl list_connections name peer_host peer_port user vhost > "$RUN_ROOT/transport/broker-peers-after.txt"
```

```bash
# Gateway
for target in 10.10.10.11:8002 10.10.10.11:8003 10.10.10.11:8004 10.10.10.11:8005 10.10.10.11:8006 10.10.10.11:8007 10.10.10.11:8008 10.10.10.12:8020 10.10.10.13:8014 10.10.10.13:8000; do
  curl -fsS "http://$target/metrics" > "$RUN_ROOT/metrics/$target-final.prom" || exit 1
done
curl -fsS http://localhost:9090/api/v1/targets > "$RUN_ROOT/transport/prometheus-targets-after.json" || exit 1
```

```bash
# Each node; select the table's interface again if this is a new pane.
ETH_IF=enp2s0
[[ "$NODE" != 3 ]] || ETH_IF=enx00e04c681057
ip -s link show "$ETH_IF" > "$RUN_ROOT/transport/counters-after.txt"
sudo ss -ntp > "$RUN_ROOT/transport/sockets-after.txt"
timedatectl status > "$RUN_ROOT/transport/clock-after.txt"
date -u +%FT%TZ > "$RUN_ROOT/completion-checked-at.txt"
```

Capture Grafana screenshots/time-window evidence while counters are live.
Snapshots alone are not complete latency/resource time series. Then Ctrl+C Threshold **after** feedback drain; its shutdown exports JSONL
from the journal. Stop gateway and Layer 1 applications gracefully. Infrastructure
may stay running. Do not reset any state until analysis and archival finish.

## Phase 10 — offline shared evaluation on Node 2

No agents or publication are started by this command. In a bootstrapped pane:

```bash
cd "$REPO"
case "$RUN_ID" in
 threshold-ethernet-full-*) LABELS_ROUTING="$SEG_RUN_DIR/labels_routing.csv" ;;
 threshold-ethernet-diagnostic-*) LABELS_ROUTING="$RUN_ROOT/offline_eval_inputs/labels_routing_50_diagnostic.csv" ;;
 *) exit 1 ;;
esac
python -B -m evaluation.baselines.shared.evaluate \
 --labels "$LABELS_ROUTING" --decisions "$RUN_BASE/controller/decision.jsonl" \
 --feedback "$RUN_BASE/controller/feedback.jsonl" --deliveries "$RUN_BASE/controller/delivery.jsonl" \
 --quarantine "$RUN_BASE/controller/quarantine.jsonl" --failures "$RUN_BASE/controller/failure.jsonl" \
 --attempts "$RUN_BASE/controller/attempt.jsonl" --controller threshold_only --run-id "$RUN_ID" \
 --output "$RUN_ROOT/offline_eval_inputs/analysis" --expect-hitl-feedback
```

Omit the HITL flag only if the frozen diagnostic review is sampled; explicitly
record retained pending cases. Inspect evaluation_summary.json, integrity_report,
verification_report, normalized_decisions.jsonl and manifest. Any review_required
status blocks a PASS until explained/resolved without deleting evidence.

Report FAR, routing FER, eligible coverage, missing-before-routing, independently
labeled risk accuracy where reported, and feedback completion. Report anomalies
observed in delivery IDs separately from routing decisions; use source-label
joins and preserve the supporting ID sets. Do not equate 1,950 corpus events
with controller incidents or invent missing-agent stage files. Calibration,
suppression and bypass explanations require preserved Layer 1 evidence.

Threshold processing_seconds measures callback work to decision construction,
not proposed control-plane or source-event E2E. Decision-ready and publish-confirmed
are different endpoints. Mode B lacks guaranteed replay_published_at headers;
queue wait/boundary E2E are unavailable when absent. Feedback recorder receipt
is not human decision time. **E2E decision latency is not directly comparable**;
do not rename controller processing time to E2E.

## Phase 11 — evidence archive and diagnostic decision

Node 1 saves Layer 1 baselines/final runtime/Fusion output, selected source and
labels, replay status/logs, queue state and reconciliation. Node 2 retains the
entire controller directory (including journal.sqlite3), analysis, run.json and
rules hashes. Gateway saves consistent stopped SQLite backup, state counts,
metrics snapshots, time-window Grafana observations and effective targets.
All nodes retain transport evidence, metadata, approved manifest, clock evidence
and before/after counters. For example, after services stop:

```bash
# Node 1
mkdir -p "$RUN_ROOT/layer1_runtime"
cp -a "$REPO/layer1/runtime_results/." "$RUN_ROOT/layer1_runtime/"
cp -p "$REPO/layer1/fusion_engine/fusion_results.jsonl" "$RUN_ROOT/layer1_runtime/"
# Record/investigate missing outputs; never fabricate empty replacements.
```

```bash
# Gateway: writers already stopped, bootstrap environment retained.
python - <<'PY'
import os,sqlite3
from pathlib import Path
src=Path(os.environ['REPO'])/'layer3/sqlite_logger/decisions.db'
dst=Path(os.environ['RUN_ROOT'])/'decisions-final.db'
assert src.exists() and not dst.exists()
with sqlite3.connect(f'file:{src}?mode=ro',uri=True) as a,sqlite3.connect(dst) as b:a.backup(b)
PY
```

```bash
# All nodes: copy baseline paths into an inventory rather than silently omitting them.
printf 'run_root=%s\nbaseline_results=%s\n' "$RUN_ROOT" "$RUN_BASE" > "$RUN_ROOT/artifact-paths.txt"
find "$RUN_ROOT" "$RUN_BASE" -type f ! -name artifact-sha256.txt -exec sha256sum {} \; > "$RUN_ROOT/artifact-sha256.txt"
```

For consolidation use the shared contract's new destination node-qualified bundle
procedure, including decision/feedback exports and their hashes. Do not overwrite
another node's metadata. Keep protected configs/journals private and archive
outside Git. Remove the non-secret pane bootstrap only after final evidence is
saved and no old pane needs it; unset credential variables in all application panes.

Diagnostic PASS requires: Ethernet sockets/peers proven; intended sole consumers;
50 selected source IDs and successful single replay; both AUTO and HITL gateway
paths observed with preserved IDs; corresponding feedback joins; exporter 8020
and required targets healthy; no unexplained DLQ/backlog/conflicts; chosen human
review scope reconciled; offline evaluator successful and evidence archived.
Missing route/path coverage is INCOMPLETE. Observed violations are FAIL. No
model-quality or timing threshold is invented for this diagnostic.

After a diagnostic, a full run uses a **new** RUN_ID and repeats every phase with
cold state and the complete frozen corpus. Never reuse diagnostic state.
