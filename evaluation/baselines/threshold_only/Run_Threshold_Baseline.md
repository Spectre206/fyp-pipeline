# Run the Threshold-Only Baseline

**Ethernet Mode B:** use [ETHERNET_FULL_RUN.md](ETHERNET_FULL_RUN.md) and the [shared contract](../ETHERNET_SHARED_EXPERIMENT_CONTRACT.md). The older network procedure and `common/analyze_comparison.py` FAR/FER definitions below are historical/superseded for the final four-system Ethernet comparison. Use `shared.evaluate` with frozen routing-label-policy-v2; no boundary capture consumer is required.

This is the authoritative operational runbook for Threshold comparative experiments. The current formal condition is **Wi-Fi**. Ethernet later uses the same application commit, rules and procedure, with different connectivity/hostname resolution and `--network-medium ethernet`. This document prepares execution; it does not report formal results.

## 1. Freeze the revision and node roles

| Node | Responsibilities |
|---|---|
| `stream-node` | RabbitMQ; unchanged Layer 1 and SEG in Mode B; Node Exporter and applicable Layer 1 metrics. No Threshold controller. |
| `ai-brain-node` | Threshold controller, independent feedback worker, metrics on 8020. |
| `gateway-node` | Django HITL, `consume_hitl`, Auto Executor on 8014, Prometheus, Grafana, Layer 3 database; Node Exporter. |

On **each node**, inspect local changes before checkout. Preserve any local modifications; do not discard them to synchronize. Set `REPO` to that node's actual checkout:

```bash
export REPO="$HOME/fyp-pipeline"
cd "$REPO"
git status
git fetch origin
git checkout experiment/threshold-baseline
git pull --ff-only origin experiment/threshold-baseline
git branch --show-current
git rev-parse HEAD
git status
```

Do this only once readiness changes have been reviewed and made available on the branch. Record the identical full commit hash on all three nodes, then freeze it throughout the comparison; do not pull between conditions. The implementation used for reported smoke validation was `08627521e930461a6ae02c954ac511ab00f89d6c`; that is not a substitute for recording the final experiment revision.

## 2. Environments and shared identity

The repository's main runbook assumes dependencies are installed and invokes `python3`; it does not establish one common venv location across nodes. This checkout has a root `venv`, but do not assume remote nodes do. In every pane, activate that node's existing tested environment:

```bash
# Set to the actual environment on this node, not another node's path.
export EXPERIMENT_VENV="/absolute/path/to/existing/environment"
source "$EXPERIMENT_VENV/bin/activate"
python -c 'import sys; print(sys.executable)'
python -m pip freeze
```

Save dependency versions with run evidence. Do not install or upgrade during measurement. Threshold/capture/replay require `pika`; Threshold additionally needs `prometheus_client`. Gateway uses its existing Layer 3 dependencies. Tests additionally require Django.

In every runtime pane set the same broker environment explicitly, including gateway panes (shared Layer 3 may load `.env`, so explicit exports avoid stale values):

```bash
export RABBITMQ_HOST=stream-node
export RABBITMQ_PORT=5672
read -r -p 'RabbitMQ user: ' RABBITMQ_USER
export RABBITMQ_USER
read -r -s -p 'RabbitMQ password: ' RABBITMQ_PASS
export RABBITMQ_PASS
printf '\n'
```

The existing vhost is `fyp`; exchange is `fyp.events`. Never archive passwords or full environment dumps.

Choose one unique `RUN_ID` and copy that literal value to the other nodes; do not generate three timestamps independently. Set on every node:

```bash
export NETWORK_MEDIUM=wifi
export RUN_ID="<same unique run ID on all nodes>"
export RUN_BASE="$REPO/evaluation/baselines/results/threshold_only/$NETWORK_MEDIUM/$RUN_ID"
mkdir -p "$RUN_BASE"
```

The controller creates `$RUN_BASE/controller` itself; **do not pre-create it**. Replay creates a separate `$RUN_BASE/replay`. Preserve all node-local evidence under the same logical run ID with node-qualified archives. Reusing an ID in another fresh directory is not globally prevented; the experiment register must enforce uniqueness.

## 3. Network preflight

On all nodes:

```bash
getent hosts stream-node
getent hosts ai-brain-node
getent hosts gateway-node
nc -zv stream-node 5672
hostname
ip -br address
ip route
```

DNS or `/etc/hosts` must resolve to addresses on the selected medium, with no unintended route through the other interface. Record the selected interface and routes; interface names are deployment-specific. For Wi-Fi record `iw dev` and `iw dev <actual-interface> link`; for Ethernet record `ip link show <actual-interface>` and `ethtool <actual-interface>` where installed. Preserve clock-synchronization status (for example `timedatectl status`) on all nodes. Cross-node wall-clock latency depends on synchronized clocks.

Use `http://gateway-node:8000` for Django: its existing host allowlist already permits `gateway-node`. No current Wi-Fi address is needed. Shared Layer 3 still contains legacy absolute import paths; use the tested gateway checkout and interpreter and verify their resolved modules before relocating it. Changing network medium does not require relocating the checkout.

Metrics connectivity is checked **after startup**, not as a prerequisite for a stopped service:

```bash
curl --fail http://ai-brain-node:8020/metrics
```

## 4. Preserve evidence and prepare cold state

Stop input publishers, proposed Triage/Strategy/Policy/Learning, competing baselines and old Layer 3 processes. Keep Ollama, Chroma and EMA inactive; do not reset them for Threshold. Archive previous controller/replay directories, Layer 3 database, queue/monitoring snapshots and applicable Layer 1 evidence before removing disposable state.

With gateway writers stopped, use SQLite backup for `layer3/sqlite_logger/decisions.db` into a **new** archive path, or preserve the stopped database and any WAL/SHM companions together. Verify the backup is readable. Then apply the gateway-only reset commands in [Full_Rerun.md, Phase 0, Node 3](../../../Full_Rerun.md#node-3--gateway-node-django-hitl-and-active-decision-log): run migrations, clear `HitlIncident` using Django, clear the separate `decisions` table, and verify zero counts. Supply that section's `REPO`, `RUN_ID` and `RUN_ROOT` environment as documented; do not execute its Node 2 resets. Original event IDs remain unchanged.

Reconcile all old RabbitMQ messages after preserving evidence. Do not silently purge a failed run to make its counts look complete. If disposal is explicitly selected after reconciliation, on stream-node use `sudo rabbitmqctl purge_queue -p fyp <queue-name>` for each reviewed queue; this is destructive and is never automated by Threshold.

For Mode B, use **only the Layer 1 portion** of [Full_Rerun.md](../../../Full_Rerun.md): Phase 0 Node 1 Feature Store/output cleanup and queue reconciliation, Phase 1 Layer 1 startup, and the frozen SEG replay procedure. Do not launch Phase 2 proposed agents or use its proposed Layer 2 analyzer. Freeze the Layer 1 configuration and source corpus; preserve their checksums. Use the main runbook's node-local Layer 1 run variables, with the same logical `RUN_ID`.

## 5. RabbitMQ ownership and drain checks

On stream-node, before startup and again before input:

```bash
sudo rabbitmqctl list_queues -p fyp name consumers messages_ready messages_unacknowledged
```

Inspect at least:

| Queue | Expected consumers after startup |
|---|---:|
| `anomaly.detected` | 1 Threshold (or 1 capture consumer during capture, never both) |
| `auto.execute` | 1 Auto Executor |
| `hitl.queue` | 1 `consume_hitl` |
| `outcome.feedback` | 1 Threshold feedback worker |
| `dead.letters` | 0; inspect count without consuming evidence |
| `triage.result`, `strategy.result` | 0 |

Before a fresh run, ready and unacknowledged counts must be zero for the relevant queues. Threshold checks consumer ownership and uses exclusive input/feedback subscriptions; it does not prove stale publishers are absent. Replay checks exactly one input consumer and zero ready messages, but cannot establish consumer identity or unacknowledged count through passive declaration. Verify both workers, gateway ownership and broker counts manually before replay.

## 6. Start shared Layer 3 — gateway-node

Use three separate terminals/tmux panes with the environment from section 2. Use the neutral presentation consistently for formal conditions. In both Django panes:

```bash
export PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}"
export DJANGO_SETTINGS_MODULE=evaluation.baselines.common.presentation_settings
cd "$REPO/layer3/dashboard"
```

Django pane:

```bash
python manage.py runserver 0.0.0.0:8000 --noreload
```

HITL consumer pane:

```bash
python manage.py consume_hitl
```

Auto Executor pane:

```bash
cd "$REPO/layer3"
python auto_executor/executor.py
```

Verify:

```bash
ss -ltnp | grep -E ':8000|:8014'
```

Confirm broker consumer counts and an empty HITL UI before input. The overlay changes presentation only, not database isolation or backend behavior.

## 7. Start Threshold — ai-brain-node

For Mode A set `DATASET_SHA256` to the verified capture file digest; for Mode B use the frozen SEG input corpus digest. Record which file the digest identifies in the experiment register. Copy/verify the input and manifest before startup; do not infer a digest from a filename.

```bash
cd "$REPO"
export DATASET_SHA256="<64-character lowercase SHA-256 digest>"
ss -ltn '( sport = :8020 )'
python -m evaluation.baselines.threshold_only.controller \
  --live --run-id "$RUN_ID" --output "$RUN_BASE/controller" \
  --network-medium "$NETWORK_MEDIUM" --dataset-sha256 "$DATASET_SHA256"
```

The output directory must not exist. The command binds 8020 before consumption and starts controller and feedback workers with separate AMQP connections. From another pane:

```bash
curl --fail -s http://localhost:8020/metrics | grep 'fyp_threshold_worker_up'
```

Both `worker="controller"` and `worker="feedback"` must equal **1**. A worker failure stops the service; preserve and reconcile the failed run rather than resuming it under the same identity.

## 8. Prometheus and Grafana — gateway-node

Reconcile `observability/prometheus.threshold.yml` with the deployed `/etc/prometheus/prometheus.yml`; preserve shared exporter settings, credentials and scrape intervals. Do not blindly overwrite deployed configuration. The Threshold job is `fyp-threshold-baseline`, target `ai-brain-node:8020`. Ports 8010–8013 are not required. Disable Layer 1 application scraping for Mode A when Layer 1 is stopped.

After an actual configuration change:

```bash
promtool check config /etc/prometheus/prometheus.yml
sudo systemctl reload prometheus
curl --fail -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=up{job="fyp-threshold-baseline"}'
```

Require value 1. If the deployed systemd unit has no reload action, use its configured reload procedure before the experiment; do not improvise a restart during measurement.

Use `observability/FYP_Threshold_Baseline_Observability.json` and the correct Prometheus datasource. Preserve the proposed dashboard. The six rows are SYSTEM OVERVIEW; LAYER 1 — REAL-TIME STATISTICAL DATA PLANE; THRESHOLD-ONLY CONTROL PLANE; LAYER 3 — EXECUTION, HUMAN OVERSIGHT & OBSERVABILITY LAYER; SYSTEM / INFRASTRUCTURE HEALTH; HARDWARE / NODE RESOURCES. Select Mode A/B appropriately. Missing series are **not zero**; verify exporters/labels and RabbitMQ per-queue metrics. Save time range and monitoring exports with evidence.

## 9. Mode A — frozen controller-boundary population

Create a capture as a separate preparation run, with every controller stopped. Use unchanged Layer 1 to produce the selected population and let capture be the sole `anomaly.detected` consumer. Determine and reconcile the expected incident count from this population; do not substitute a historical count or the SEG source-event count. If the full incident count is unknown, reconcile the completed Layer 1 output/queued population first, then capture it; that capture's drain-time schedule becomes the frozen schedule, not the original arrival timing. Record this distinction.

From a configured node with broker access, repository-root working directory and active environment:

```bash
python -m evaluation.baselines.common.capture_incidents \
  --live --capture-id "<unique-capture-id>" \
  --count <reconciled-incident-count> --output <new-capture-directory>
```

Freeze `incidents.jsonl` and `incidents.manifest.json`, reconcile publications and queue drain, and preserve capture provenance. No manifest means incomplete capture. Verify offline before the formal run:

```bash
export CAPTURE_DIR="/absolute/path/to/frozen-capture"
python - <<'PY'
import os
from pathlib import Path
from evaluation.baselines.common.capture_incidents import load_capture
p = Path(os.environ['CAPTURE_DIR'])
records, manifest = load_capture(p/'incidents.jsonl', p/'incidents.manifest.json')
print('Incidents:', len(records), 'SHA-256:', manifest['sha256'])
PY
```

Set the controller's `DATASET_SHA256` to this printed digest. Stop Layer 1 and all other publishers, prepare fresh Layer 3 state, start Threshold and verify sections 5–8. Replay on a configured node using the **same RUN_ID**:

```bash
python -m evaluation.baselines.common.replay_incidents \
  --live --capture "$CAPTURE_DIR/incidents.jsonl" \
  --manifest "$CAPTURE_DIR/incidents.manifest.json" \
  --run-id "$RUN_ID" --output "$RUN_BASE/replay" --speed 1
```

The utility verifies checksum, unique IDs, routing keys, order and schedule; preserves exact bytes; and logs confirmed publication. Long waits service AMQP heartbeats. Use identical capture/order/speed for all architectures and network conditions. Preserve actual publication times because scheduling and broker delays can vary. Do not use the ad-hoc smoke publisher, edit event IDs, or put ground truth into payloads. Annotate independently under [the rubric](../datasets/README.md), without seeing controller outputs.

## 10. Mode B — unchanged full pipeline

Flow: SEG → unchanged Layer 1 → Threshold → shared Layer 3. Use section 4's Layer 1 cold-state references and the frozen SEG corpus/configuration at speed 1. Keep proposed Layer 2 stopped. Start input only after gateway, Threshold and monitoring are healthy. Record actual incident IDs emitted by Layer 1; do not equate source-event totals with controller decisions. Mode B queue-wait/boundary timing remains unavailable without fresh boundary publication timestamps.

The common analyzer requires a verified boundary capture as its expected-ID population. Do not attach a competing capture consumer during a Mode B run. Reconcile Mode B against independent Layer 1 publication evidence and journals; do not feed it an unrelated Mode A capture. A canonical conversion of that Mode B evidence for comparative scoring is not implemented by this task.

## 11. HITL and completion gates

AUTO feedback is automatic. HITL requires approve/reject/modify; finish all incidents before declaring completion unless a frozen protocol explicitly defines a cutoff. Human approval is not independent correctness ground truth.

Before shutdown, reconcile:

- Unique expected incident IDs against confirmed decisions; deliveries may include duplicates.
- AUTO + HITL totals against decisions, and accepted terminal feedback IDs against all decisions.
- Duplicate/conflicting/unexpected/wrong-run feedback separately; raw feedback line count alone is insufficient.
- Queue ready/unacknowledged counts at zero; empty DLQ, or fully documented failures.
- Failure/quarantine evidence, both worker gauges, target health and saved monitoring interval.
- Layer 3 pending count, final database evidence, replay completion marker/count and checksums.

During runtime SQLite is authoritative; JSONL is exported on shutdown. Inspect it read-only if needed. Preserve incomplete runs and missing decisions; never remove them from analysis silently.

## 12. Shutdown and evidence

After input stops and completion gates pass, save final metrics/queue snapshots. Ctrl-C the Threshold foreground process and let both workers close and exports finish. Then stop Layer 3 and applicable Layer 1 processes cleanly. Do not use `kill -9`. Archive the final database after writers stop.

Controller directory:

| File | Meaning |
|---|---|
| `run.json` | Run ID, network medium, hostname, Git commit, controller/rule revision and checksum, declared dataset checksum, UTC creation time and mode. |
| `journal.sqlite3` | Durable deliveries, prepared/confirmed decisions and accounting; authoritative, including interrupted publication evidence. |
| `delivery.jsonl` | Exact raw deliveries encoded as base64 with receipt/hash provenance. |
| `decision.jsonl` | Confirmed native decisions. |
| `feedback.jsonl` | Outcomes and accounting statuses, including rejected/duplicate records. |
| `failure.jsonl` | Worker failure records. |
| `quarantine.jsonl` | Unidentifiable input, wrong-run messages or ID collisions. |

Replay evidence includes its own `run.json`, `replay.jsonl` and `completed.json`; capture has its own run metadata and frozen dataset/manifest. Archive network/link state, per-node revision/dependencies, input checksum, queue snapshots, database backup and monitoring exports alongside these artifacts. Generate checksums after writers finish. Existing `results/.gitignore` excludes generated evidence at any depth. Preserve it in backed-up experiment storage; commit reviewed source/configuration/docs, not databases, raw captures, secrets or generated run dumps. No evidence is automatically uploaded or committed.

## 13. Analyze Mode A

After exports exist, from repository root:

```bash
python -m evaluation.baselines.common.analyze_comparison \
  --capture "$CAPTURE_DIR/incidents.jsonl" \
  --manifest "$CAPTURE_DIR/incidents.manifest.json" \
  --decisions "$RUN_BASE/controller/decision.jsonl" \
  --feedback "$RUN_BASE/controller/feedback.jsonl" \
  --labels <independently-adjudicated-labels.jsonl> \
  --expect-hitl-feedback
```

Save stdout to a new analysis file without overwriting prior analysis. Omit `--labels` if unavailable: completeness/workload still work, but FAR/FER and correctness are not computable. Never fabricate labels. `--expect-hitl-feedback` includes HITL in the completion denominator; the default expects AUTO feedback only. Missing decisions remain visible, and ambiguous cases remain in coverage but outside quality denominators. Consult [common README](../common/README.md) for precise definitions.

## 14. Wi-Fi now, Ethernet later

Keep the same frozen application commit, Threshold rules/actions, action vocabulary, Layer 3, metric definitions and analysis. Mode A keeps identical captured bytes/order/schedule; Mode B keeps identical Layer 1 corpus/configuration. Change only the medium and corresponding host/IP/route configuration, then repeat network verification. Use a fresh ID/path and `--network-medium ethernet` for Ethernet; no separate controller or dashboard exists.

The network flag affects only `run.json`. It cannot alter decisions. The optional dataset digest is a provenance declaration, not automatic verification against live deliveries; reconcile it with the verified capture or frozen SEG file. Freeze repetitions, subset, human-review policy and failure/rerun criteria before input. No full run, final capture or ground-truth generation is performed by preparing this runbook.
