# Single-Agent Ethernet Mode B — frozen full run

Prepared procedure, not an execution record. No experiment has been run by this
migration. Follow the [shared contract](../ETHERNET_SHARED_EXPERIMENT_CONTRACT.md)
and its final routing metrics. The legacy Single-Agent runbook/analyzer remains
historical for final Ethernet scoring. Never launch proposed agents, Chroma,
EMA or Threshold alongside Single-Agent. Only Single-Agent uses local Ollama. No live incident capture consumer is used.

Use Bash. This is the formal full-run procedure; complete a separately identified,
approved integration smoke before it. No smoke state may carry into this run.
All application commands are foreground processes in separate panes. Do not paste
all blocks as one script. This preparation has not started services or inference.

| Node | Address/interface | Role |
|---|---|---|
| stream-node | 10.10.10.11 / enp2s0 | RabbitMQ, SEG, unchanged Layer 1 |
| ai-brain-node | 10.10.10.12 / enp2s0 | Single-Agent + accounting workers, :8030 |
| gateway-node | 10.10.10.13 / enx00e04c681057 | Auto Executor :8014, HITL/Django :8000, monitoring |

## Phase 0 — reviewed freeze, identity, inputs and revision

Before any reset, select a reviewed full controller commit on
`experiment/single-agent-baseline` on every node. The migration's starting commit
was `63584c7090b81e3f545f3634fd65d7d64c07734a`; it does **not** include these
uncommitted adaptations. Review/commit/distribute the adaptation first using the
normal process. No command here stages, commits, pushes, pulls or bypasses the
clean-tree requirement. Record the actual approved full commit, not that starting
hash. Freeze review scope, repetition/order, clocks, cutoff/drain timeout and
failure/rerun criteria in `protocol-freeze.txt` before publication. For formal
runs use exhaustive HITL completion unless the approved comparison says otherwise.

On Node 1 choose a unique full-run ID, then copy its literal value to Nodes 2 and 3:

```bash
RUN_ID="single-agent-ethernet-full-$(date -u +%Y%m%d-%H%M%S)"
printf '%s\n' "$RUN_ID"
```

On each node, in the setup pane (Nodes 2/3 first `read -r -p 'Exact RUN_ID: ' RUN_ID`):

```bash
export REPO="$HOME/fyp-pipeline"
cd "$REPO" || exit 1
[[ "$RUN_ID" =~ ^single-agent-ethernet-full-[0-9]{8}-[0-9]{6}$ ]] || exit 1
read -r -p 'Node number (1/2/3): ' NODE
[[ "$NODE" =~ ^[123]$ ]] || exit 1
read -r -p 'Absolute existing Python environment on THIS node: ' EXPERIMENT_VENV
[[ "$EXPERIMENT_VENV" == /* && -f "$EXPERIMENT_VENV/bin/activate" ]] || exit 1
export RUN_ID NODE EXPERIMENT_VENV
export RUN_ROOT="$REPO/experiment_runs/$RUN_ID"
export SEG_RUN_DIR="$RUN_ROOT/seg"
export RUN_BASE="$REPO/evaluation/baselines/results/single_agent/ethernet/$RUN_ID"
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
export RUN_BASE="$REPO/evaluation/baselines/results/single_agent/ethernet/$RUN_ID"
export NETWORK_MEDIUM=ethernet
protocol_event() {
  [[ "$1" =~ ^[A-Z_]+$ ]] || return 1
  printf '%s run_id=%s node=%s event=%s\n' "$(date -u +%FT%TZ)" "$RUN_ID" "$NODE" "$1" >> "$RUN_ROOT/protocol-events.log"
}
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
} > "$HOME/fyp-single-agent-pane.sh"
chmod 600 "$HOME/fyp-single-agent-pane.sh"
source "$HOME/fyp-single-agent-pane.sh"
protocol_event RUN_SETUP
```

Every new pane starts with `source "$HOME/fyp-single-agent-pane.sh"`; credential
entry is local to each pane and never written to disk. Node 2 uses the profile's
`OLLAMA_HOST=http://localhost:11434`; model inference starts only in Phase 4.
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
review_reference and the four shared file-inventory groups plus `files.controller`. Add these Single-Agent fields:

```json
{
  "controller": "single_agent",
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
and single_agent/ethernet_checks.py; review/include their tests and other
scaffolding too. `files.deployment` includes both node profiles, the Ethernet
Prometheus template, gateway settings and requirements, and the two gateway
HITL source files whose imports now resolve the node-local Layer 3 directory. `files.routing_policy`
includes the unchanged generator and policy specification. Each group records
hashes matching the declared full source revision. `files.controller` must include controller.py, feedback.py, llm_client.py,
metrics.py, prompt.py, schema.py, ethernet_checks.py, this runbook and the dedicated
dashboard under single_agent; common contracts.py, journal.py, rabbitmq.py,
layer3_adapter.py, presentation_settings.py and templates/hitl/detail.html; and
layer2/agents/schema_validator.py (the action vocabulary source). These hashes
are checked against controller_commit as well as the local files. Also inventory
relevant tests, Layer 1/3 sources and remaining run documents in that group.
The exact clean HEAD pins tracked files; a manifest alone does not prove external
approval or runtime identity. Record the semantic prompt/schema/action-vocabulary
hashes from run.json separately from whole-file hashes.
Do not make approved hashes from an unreviewed working tree. The manifest is an
operator-reviewed input; this document cannot preapprove a future commit.

On **every node**, copy that reviewed manifest to
`$RUN_ROOT/approved-revision.json`, then run:

```bash
cd "$REPO"
python -B -m evaluation.baselines.single_agent.ethernet_checks revision \
  --repo "$REPO" --manifest "$RUN_ROOT/approved-revision.json" \
  > "$RUN_ROOT/transport/revision-before.json" || exit 1
sha256sum "$RUN_ROOT/approved-revision.json" > "$RUN_ROOT/transport/revision-manifest.sha256"
```

This wraps the shared verifier, adds Single-Agent identity/inventory checks and
allows a reviewed controller commit instead of the obsolete proposed one-file
exception. It does not approve a manifest or certify installed external state.
Repeat before publication. Stop on a dirty tree, mismatched hash or missing file.

## Phase 1 — archive and cold reset (destructive, operator executed)

First stop all old publishers/application consumers gracefully, including
Single-Agent and gateway writers. No proposed agents or capture consumers may run.
Keep infrastructure services available. Archive old run roots and journals
separately; never reuse controller/replay/analysis directories. Choose a unique
protected archive **outside the checkout** on each node and record its path.

Node 1:

```bash
source "$HOME/fyp-single-agent-pane.sh"
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
directory do not exist. No Chroma or EMA reset applies. Do not retrain/reset the model; retain the
existing preload-and-fixed-inference warmup in Phase 4.

Gateway, with all database writers stopped:

```bash
source "$HOME/fyp-single-agent-pane.sh"
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
source "$HOME/fyp-single-agent-pane.sh"
cd "$REPO/layer3"
python auto_executor/executor.py
```

```bash
# Gateway HITL consumer pane
source "$HOME/fyp-single-agent-pane.sh"
cd "$REPO/layer3/dashboard"
python manage.py consume_hitl
```

```bash
# Gateway Django pane
source "$HOME/fyp-single-agent-pane.sh"
cd "$REPO/layer3/dashboard"
python manage.py runserver 0.0.0.0:8000 --noreload
```

Use `http://10.10.10.13:8000`. The presentation overlay retains neutral baseline
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
source "$HOME/fyp-single-agent-pane.sh"
cd "$REPO/layer1/validator"
python validator.py
```

## Phase 4 — Single-Agent on Node 2, identity and warmup

Before launch verify `qwen3:1.7b` is installed and no competing inference workload
is active. Do not download, upgrade, tune or retrain during the freeze. Record
`ollama --version`, `ollama list`, `ollama ps`, CPU/device information and the
existing service configuration with secrets redacted. Check the model digest
against the reviewed model freeze. Do not dump process environments.

In the controller pane:

```bash
source "$HOME/fyp-single-agent-pane.sh"
cd "$REPO"
read -r -p 'Approved events_1950.jsonl SHA-256 from manifest: ' DATASET_SHA256
[[ "$DATASET_SHA256" =~ ^[0-9a-f]{64}$ ]] || exit 1
python -B - "$RUN_ROOT/approved-revision.json" "$DATASET_SHA256" <<'PYHASH'
import json,sys
assert json.load(open(sys.argv[1]))['frozen_input_hashes']['events_1950.jsonl']==sys.argv[2]
PYHASH
[[ "$?" == 0 ]] || exit 1
python -B -m evaluation.baselines.single_agent.controller \
 --live --run-id "$RUN_ID" --output "$RUN_BASE/controller" \
 --network-medium ethernet --evaluation-mode B --dataset-sha256 "$DATASET_SHA256" \
 --replay-speed 1
```

This binds :8030, fetches available model identity, preloads, then performs one
fixed non-measured inference before starting controller/feedback workers. The
warmup has two HTTP requests (preload and fixed inference), separate from the
maximum two measured generation attempts per valid incident. A failed warmup
aborts startup. Do not add a second warmup invocation to the procedure.

In a second bootstrapped Node 2 pane, after warmup:

```bash
ollama ps > "$RUN_ROOT/transport/ollama-ps-before.txt"
python -B - "$RUN_BASE/controller/run.json" "$RUN_BASE/controller/warmup.json" <<'PYMODEL' || exit 1
import json,sys
r=json.load(open(sys.argv[1]));w=json.load(open(sys.argv[2]))
assert r['model_name']=='qwen3:1.7b' and r['model_digest'] and r['ollama_version']
assert r['ollama_host']=='http://localhost:11434'
assert r['evaluation_mode']=='B' and r['network_medium']=='ethernet' and r['working_tree_clean']
assert r['maximum_attempts']==2 and r['requested_options']=={'num_ctx':2048,'num_predict':512}
assert w['protocol']=='preload-and-fixed-inference-v1' and r['measured_start_at']
print('Recorded model identity and warmup present; compare digest/version to approved freeze.')
PYMODEL
```

Require CPU-only residency (e.g. `ollama ps` reports 100% CPU) on ai-brain-node;
record the actual evidence and absence of competing inference. Missing/ambiguous
identity or CPU evidence blocks replay. Preserve runtime version/digest, available
options and unavailable defaults honestly; the client does not resolve sampling
or thread defaults. Record external identity/dependency evidence references in
operator metadata; do not rewrite the controller's original run.json to conceal
null references. Save per-attempt load telemetry to assess later reloads.

**Warmup fairness:** retain the existing Single-Agent preload/fixed inference.
The completed Proposed Adaptive Ethernet run had no matching dedicated warmup,
as recorded in the shared contract. No historical evidence is altered. Routing
quality remains comparable under the shared routing-label contract, subject to
its other limitations; directly matched LLM latency/residency comparisons are
not established. Disclose this difference in protocol-freeze.txt and results.

## Phase 5 — readiness and Ethernet transport gate

Node 1, save and review:

```bash
source "$HOME/fyp-single-agent-pane.sh"
sudo rabbitmqctl list_queues -p fyp name consumers messages_ready messages_unacknowledged | tee "$RUN_ROOT/transport/queues-before.txt"
sudo rabbitmqctl list_consumers -p fyp | tee "$RUN_ROOT/transport/consumers-before.txt"
sudo rabbitmqctl list_queues -p fyp name consumers messages_ready messages_unacknowledged --formatter=json > "$RUN_ROOT/transport/queues-before.json"
python -B -m evaluation.baselines.single_agent.ethernet_checks queues \
 --input "$RUN_ROOT/transport/queues-before.json" || exit 1
sudo rabbitmqctl list_connections name peer_host peer_port user vhost | tee "$RUN_ROOT/transport/broker-peers-before.txt"
```

Require exactly one intended consumer per active input: Validator/raw.events,
ADM/validated.event, five detectors/detect.*, Fusion/fusion.results,
Single-Agent/anomaly.detected, Auto Executor/auto.execute, HITL/hitl.queue,
Single-Agent accounting/outcome.feedback. Require zero consumers on triage.result,
strategy.result and dead.letters, and all experiment queues empty before replay.
Verify process identities manually; counts alone do not prove controller identity.

Each node selects its actual table interface and peers, then records:

```bash
source "$HOME/fyp-single-agent-pane.sh"
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
source "$HOME/fyp-single-agent-pane.sh"
cd "$REPO"
curl -fsS http://10.10.10.12:8030/metrics > "$RUN_ROOT/metrics/single-agent-before.prom" || exit 1
grep '^fyp_single_agent_worker_up' "$RUN_ROOT/metrics/single-agent-before.prom"
# Both controller and feedback gauges must equal 1.
python -B -m evaluation.baselines.single_agent.ethernet_checks workers \
 --input "$RUN_ROOT/metrics/single-agent-before.prom" || exit 1
sudo promtool check config /etc/prometheus/prometheus.yml || exit 1
curl -fsS http://localhost:9090/api/v1/status/config > "$RUN_ROOT/transport/prometheus-effective.json" || exit 1
curl -fsS http://localhost:9090/api/v1/targets > "$RUN_ROOT/transport/prometheus-targets-before.json" || exit 1
python -B -m evaluation.baselines.single_agent.ethernet_checks targets \
 --input "$RUN_ROOT/transport/prometheus-targets-before.json" || exit 1
```

The reviewed template has 21 targets; 16 are required for Single-Agent Mode B:
Layer 1 seven, Single-Agent one, Layer 3 two, RabbitMQ one, cluster exporters three,
local Prometheus and node jobs two. Proposed agents four and Threshold one
are intentionally inactive. The checker validates exact identities/URLs/health,
not a blind count. It does not prove inactive processes are absent: check queues.

Load the dedicated `observability/FYP_Single_Agent_Baseline_Observability.json` in
Grafana using the existing datasource. Check Single-Agent, shared Layer 1/3, hardware,
NTP, backlog and DLQ panels. Select Mode B. Its job selectors now match the shared
Ethernet template; no proposed-agent panels are required. Do not install the
legacy prometheus.single_agent.yml over the Ethernet configuration.

## Phase 6 — verify the complete frozen source

Node 1, in the setup/replay pane:

```bash
source "$HOME/fyp-single-agent-pane.sh"
cd "$REPO"
python -B -m evaluation.baselines.single_agent.ethernet_checks corpus \
 --directory "$SEG_RUN_DIR" --manifest "$RUN_ROOT/approved-revision.json" \
 > "$RUN_ROOT/corpus-verification.json" || exit 1
export INPUT_EVENTS="$SEG_RUN_DIR/events_1950.jsonl"
export INPUT_LABELS="$SEG_RUN_DIR/labels_routing.csv"
export EXPECTED_EVENTS=1950
sha256sum "$INPUT_EVENTS" "$INPUT_LABELS" > "$RUN_ROOT/selected-inputs.sha256"
```

The checker verifies all four approved hashes, 1,950 unique event IDs matching
labels, unchanged original annotation fields, source/derived label order and
routing-label-policy-v2 distribution (NORMAL 1000, expected AUTO 380, expected
HITL 570). The approved events file hash pins event order and timestamps.
Labels remain offline. Do not generate fresh UUID/timestamp events, select a
subset or inject cases to manufacture AUTO/HITL coverage in a formal full run.

## Phase 7 — metadata and final source check

Every node reruns Phase 0's revision gate and saves fresh output before input.
Node 1 rechecks the frozen corpus command. Record metadata on every node:

```bash
cd "$REPO"
{
  printf 'timestamp=%s\nrun_id=%s\nnode=%s\n' "$(date -u +%FT%TZ)" "$RUN_ID" "$(hostname)"
  printf 'branch=%s\ncommit=%s\n' "$(git branch --show-current)" "$(git rev-parse HEAD)"
  printf 'controller=single_agent\nnetwork_medium=ethernet\nevaluation_mode=B\nreplay_speed=1\n'
  printf 'run_root=%s\ncontroller_path=%s\n' "$RUN_ROOT" "$RUN_BASE/controller"
  sha256sum "$RUN_ROOT/approved-revision.json" "$SEG_RUN_DIR/labels.csv" "$SEG_RUN_DIR/labels_routing.csv"
  sha256sum evaluation/baselines/single_agent/prompt.py evaluation/baselines/single_agent/schema.py layer2/agents/schema_validator.py
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
After confirming every gate on all nodes, each setup pane runs
`protocol_event PRE_REPLAY_GATE`. Do not log success before inspecting evidence.

## Phase 8 — single replay (operator execution only)

Node 1, same setup/replay pane with selected variables intact:

```bash
[[ "$RUN_ID" =~ ^single-agent-ethernet-full-[0-9]{8}-[0-9]{6}$ && "$EXPECTED_EVENTS" == 1950 && "$INPUT_EVENTS" == "$SEG_RUN_DIR/events_1950.jsonl" ]] || exit 1
(cd "$SEG_RUN_DIR" && sha256sum --check --strict "$RUN_ROOT/frozen-inputs.sha256") || exit 1
sha256sum --check --strict "$RUN_ROOT/selected-inputs.sha256" || exit 1
# Exclusive marker: even a failed invocation cannot be repeated in this state.
(set -o noclobber; date -u +%FT%TZ > "$RUN_ROOT/replay-started.txt") || exit 1
protocol_event REPLAY_STARTED
cd "$REPO/layer1/seg"
set -o pipefail
python3 seg.py --mode replay --config "$SEG_RUN_DIR/seg_config.json" \
  --input "$INPUT_EVENTS" --speed 1 2>&1 | tee "$RUN_ROOT/seg-replay.log"
replay_status=${PIPESTATUS[0]}
printf '%s\n' "$replay_status" > "$RUN_ROOT/seg-exit-status.txt"
date -u +%FT%TZ > "$RUN_ROOT/replay-ended.txt"
protocol_event REPLAY_ENDED
[[ "$replay_status" == 0 ]] || { protocol_event FAILED_INCOMPLETE; echo 'FAILED replay: preserve state; never resume this run'; exit 1; }
```

Do not replay raw source events directly into anomaly.detected. Layer 1 produces
both Fusion incidents and Validator structural bypass incidents normally.

## Worker failure and resumed execution — formal validity

From replay start through required drain/feedback completion, any application
worker death or restart invalidates the formal run. This includes Layer 1
workers even when SEG finishes successfully or Single-Agent exports appear clean.
Preserve evidence; do not restart/resume in the same RUN_ID. A replacement formal
attempt requires a new RUN_ID and the complete cold-reset procedure. Normal
shutdown after documented completion is not a worker restart.

Keep an operator-owned, append-only `protocol-events.log` beside metadata and
reference it in reconciliation. Each entry records RUN_ID, UTC recording time,
occurrence time (or unknown), node, worker, status, reason, evidence paths and
formal eligibility. Use these explicit classifications:

- `IN_PROGRESS`: not yet eligible for a completion claim.
- `FAILED_INCOMPLETE`: worker death, interruption or failed completion; excluded.
- `RESUMED_INVALID_FOR_FORMAL_COMPARISON`: a worker restarted after publication
  began and before completion; permanently excluded for this RUN_ID.
- `COMPLETED_UNINTERRUPTED`: only after all completion gates and process-history
  review; never use it to overwrite a failed/resumed classification.

If a restart already happened, append both failure and restart observations;
retain earlier evidence and distinguish retrospective recording from actual
occurrence time. Unknown times remain unknown. Record later clean exports as
post-resume evidence, not a replacement successful experiment. The historical Threshold run `threshold-ethernet-full-20261003-053739`
demonstrated this failure mode. It is not a Single-Agent run; its resumed status
and evidence remain unchanged.

The exclusive replay marker only prevents a second SEG invocation. It does not
prevent a detector restart. As a manual prelaunch check, confirm with Node 1
whether replay has begun before starting/restarting any application pane; a
missing local marker on Node 2/3 is not permission to restart. Do not add
automatic recovery under the same RUN_ID.

For future runs, preserve per-worker startup/exit logs and process identity
(node, boot ID, PID, process start time, command) before replay and before
shutdown, plus snapshots at any fault. Save queue consumer counts/backlogs,
service logs and Prometheus process-start/counter-reset history when available.
Before/after PID snapshots alone cannot prove uninterrupted execution: PIDs can
be reused, short-lived processes can be missed and metrics can have scrape gaps.
The current helpers do not automatically enforce or reconstruct this history.

Offline `no_detected_record_errors` and 100% feedback completion cover observed
controller records only. Neither overrides the protocol status, upstream worker
failure, a 286-message detector backlog, or an observed restart. Keep full source
labels for partial analysis; missing routing coverage cannot by itself assign
causes to individual events. Preserve pre/post-resume exports separately if both
exist and label any analysis accordingly.

## Phase 9 — drain, human review and flush

On Node 1 observe ready/unacknowledged counts until all experiment queues drain;
use the frozen cutoff and preserve any failure rather than waiting indefinitely.
On gateway handle HITL organically, using the neutral presentation overlay.
Reviewers must not consult expected_route, safe_to_auto, expected_risk or other
ground-truth fields. Approve sensible actions, modify when genuinely better
actions are needed, reject inappropriate proposals. Empty-action fallback can
legitimately require MODIFIED/REJECTED. Do not force approval percentages or
route coverage. Require zero pending and feedback drained for this full run. Check no DLQ,
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
for target in 10.10.10.11:8002 10.10.10.11:8003 10.10.10.11:8004 10.10.10.11:8005 10.10.10.11:8006 10.10.10.11:8007 10.10.10.11:8008 10.10.10.12:8030 10.10.10.13:8014 10.10.10.13:8000; do
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
Snapshots alone are not complete latency/resource time series. After all-node
drain/reconciliation is confirmed, run `protocol_event DRAINED` on each node.
Then Ctrl+C Single-Agent **after** feedback drain; its shutdown exports JSONL
from the journal. Stop gateway and Layer 1 applications gracefully. Infrastructure
may stay running. After local applications stop and exports flush, run
`protocol_event GRACEFUL_SHUTDOWN`. Do not reset any state until analysis and archival finish.

## Phase 10 — offline shared evaluation on Node 2

No agents or publication are started by this command. In a bootstrapped pane:

```bash
cd "$REPO"
LABELS_ROUTING="$SEG_RUN_DIR/labels_routing.csv"
python -B -m evaluation.baselines.shared.evaluate \
 --labels "$LABELS_ROUTING" --decisions "$RUN_BASE/controller/decision.jsonl" \
 --feedback "$RUN_BASE/controller/feedback.jsonl" --deliveries "$RUN_BASE/controller/delivery.jsonl" \
 --quarantine "$RUN_BASE/controller/quarantine.jsonl" --failures "$RUN_BASE/controller/failure.jsonl" \
 --attempts "$RUN_BASE/controller/attempt.jsonl" \
 --controller single_agent --run-id "$RUN_ID" \
 --output "$RUN_ROOT/offline_eval_inputs/analysis" --expect-hitl-feedback
```

`attempt.jsonl` is required native Single-Agent model evidence. Preserve it even
when publication failed; do not manufacture an empty file. Inspect
`evaluation_summary.json`, `integrity_report.json`, `verification_report.json`,
`normalized_decisions.jsonl` and `manifest.json`. A CLI exit 0 means outputs were
written; any review_required status needs investigation and may invalidate the
run. Never remove contradictory evidence to obtain a PASS. Record
`protocol_event OFFLINE_EVALUATION` after review and link the outputs in the log.

The shared evaluator includes the attempt sidecar's hash, record count and
malformed-line checks; it does not validate every attempt's run/ID/sequence or
compute model-validity rates. Separately reconcile native attempts with embedded
decision attempts by event_id/run_id/attempt_number, checking at most two calls,
retry eligibility, valid/invalid attempts, accepted output and fallback. Preserve
attempts without confirmed decisions and explain them from journal/failure
records. Distinguish `raw_routing_decision` (last extracted route, possibly invalid),
`accepted_model_output` (validated object or null), `final_routing_decision`
(dispatched route) and fallback HITL. Fallback is not valid model output.

Report FAR, routing FER, eligible coverage, missing-before-routing, independently
labeled risk accuracy where reported, and feedback completion. Report anomalies
observed in delivery IDs separately from routing decisions; use source-label
joins and preserve the supporting ID sets. Do not equate 1,950 corpus events
with controller incidents or invent missing-agent stage files. Calibration,
suppression and bypass explanations require preserved Layer 1 evidence.

Single-Agent processing_seconds includes model/retry work through decision construction,
not proposed control-plane or source-event E2E. Decision-ready and publish-confirmed
are different endpoints. Mode B lacks guaranteed replay_published_at headers;
queue wait/boundary E2E are unavailable when absent. Feedback recorder receipt
is not human decision time. **E2E decision latency is not directly comparable**;
do not rename controller processing time to E2E.

## Phase 11 — evidence archive and completion

Node 1 saves Layer 1 baselines/final runtime/Fusion output, selected source and
labels, replay status/logs, queue state and reconciliation. Node 2 retains the
entire controller directory (including journal.sqlite3), analysis, run.json, warmup.json and
prompt/schema/action-vocabulary hashes. Gateway saves consistent stopped SQLite backup, state counts,
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

Formal completion requires successful one-time replay, intended sole consumers,
uninterrupted worker history, full queue drain, zero pending HITL, reconciled
feedback, evaluator integrity/verification review, Layer 1 source-to-incident
reconciliation and archived evidence from all nodes. Only then record
`protocol_event COMPLETED_UNINTERRUPTED` on each node and regenerate the final
artifact inventory so it includes the completed log. Do not force the historical
639 incidents or any routing distribution. NORMAL is excluded from anomaly
FAR/FER; missing-before-routing is separate from routing FER. Controller-visible
cleanliness cannot prove completion upstream.

## Protocol lifecycle and process continuity

Record these events in the append-only protocol log with UTC time, RUN_ID, node,
evidence references and eligibility; never overwrite an earlier invalid status:

| Event | Record only after |
|---|---|
| RUN_SETUP | New local directories and literal common identity established |
| PRE_REPLAY_GATE | All-node revision, cold state, ownership, model and transport gates passed |
| REPLAY_STARTED | Exclusive Node 1 marker created, before publication |
| REPLAY_ENDED | SEG exit code and end timestamp recorded |
| DRAINED | Queues, HITL pending and required feedback reconciled on all nodes |
| GRACEFUL_SHUTDOWN | Application processes stopped after DRAINED, exports flushed |
| OFFLINE_EVALUATION | Outputs preserved and integrity/verification reviewed |
| COMPLETED_UNINTERRUPTED | All-node process history, reconciliation and archive review complete |

Use FAILED_INCOMPLETE on interruption; if any worker is restarted after replay,
record `protocol_event RESUMED_INVALID_FOR_FORMAL_COMPARISON` permanently for that RUN_ID. Later
clean exports never reverse it. Communicate Node 1's replay start to all nodes.
A local marker is not a distributed restart lock and missing Node 2/3 markers
are not permission to launch workers.

Save `cat /proc/sys/kernel/random/boot_id` and `ps -eo pid,lstart,args` before
replay and before shutdown on each node, plus per-worker launch/exit records,
queue snapshots and fault-time observations. Do not capture environments; redact
credentials if any application was improperly launched with secrets in arguments.
Before/after PIDs or Prometheus snapshots alone cannot prove continuity. Preserve
logs and operator observations, and exclude runs with unresolved history.

Readiness helpers are offline snapshot validators, not supervisors. They neither
start services nor automatically rerun/resume workloads. Integration smoke,
reviewed committed revision/manifests, freeze decisions and live gates remain
prerequisites; the uncommitted preparation itself authorizes no formal execution.
