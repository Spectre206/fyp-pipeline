# Run the Single-Agent Baseline

Authoritative operational procedure for the Single-Agent comparative baseline. Wi-Fi is the current formal condition; Ethernet reuses this procedure and application commit after changing connectivity/hostname resolution and network metadata. This runbook is readiness documentation, not evidence of a completed live or formal run.

## 1. Freeze and synchronize the revision

On each node, inspect modifications before checkout. Preserve local changes; do not discard them to synchronize. Once reviewed implementation commits are available on the branch:

```bash
export REPO="$HOME/fyp-pipeline"  # change to this node's actual checkout
cd "$REPO"
git status
git fetch origin
git checkout experiment/single-agent-baseline
git pull --ff-only origin experiment/single-agent-baseline
git branch --show-current
git rev-parse HEAD
git status
```

Record the same full commit hash and clean working tree on all three nodes. Freeze this revision for the matched conditions; do not pull between measurements.

| Node | Active responsibilities |
|---|---|
| stream-node | RabbitMQ; unchanged SEG/Layer 1 for Mode B or separate capture preparation; relevant exporters. |
| ai-brain-node | Ollama, Single-Agent controller, feedback worker, metrics 8030. |
| gateway-node | Django HITL, HITL consumer, Auto Executor 8014, Layer 3 SQLite state, Prometheus/Grafana. |

No Threshold controller or Proposed Triage/Strategy/Policy/Learning runs during a Single-Agent experiment.

## 2. Interpreter, configuration and run identity

Use each node's existing tested environment. This local checkout has `venv`; remote environment locations are not established by repository documentation. Set the actual path per node, in every runtime pane:

```bash
export EXPERIMENT_VENV="/absolute/path/to/existing/environment"
source "$EXPERIMENT_VENV/bin/activate"
python -c 'import sys; print(sys.executable)'
python -m pip freeze
export RABBITMQ_HOST=stream-node
export RABBITMQ_PORT=5672
read -r -p 'RabbitMQ user: ' RABBITMQ_USER
export RABBITMQ_USER
read -r -s -p 'RabbitMQ password: ' RABBITMQ_PASS
export RABBITMQ_PASS
printf '\n'
export OLLAMA_HOST=http://localhost:11434  # ai-brain-node local Ollama
```

Capture dependency versions separately, never passwords or complete environment dumps. Broker vhost is `fyp`. Explicit exports also override stale gateway `.env` values. Required baseline dependencies: requests, pika, prometheus-client; gateway/tests use existing Django dependencies. Do not upgrade packages during measurement.

Choose one unique ID, then copy that literal ID to all panes/nodes:

```bash
export NETWORK_MEDIUM=wifi
export RUN_ID="<same unique ID on all three nodes>"
export RUN_BASE="$REPO/evaluation/baselines/results/single_agent/$NETWORK_MEDIUM/$RUN_ID"
mkdir -p "$RUN_BASE"
```

Do not pre-create `$RUN_BASE/controller` or `$RUN_BASE/replay`; each CLI requires a new directory. Directory guards do not establish global run-ID uniqueness: maintain an experiment register. Keep node-qualified archives when collecting evidence from different hosts.

## 3. Network and runtime preflight

On all nodes:

```bash
getent hosts stream-node
getent hosts ai-brain-node
getent hosts gateway-node
nc -zv stream-node 5672
hostname
ip -br address
ip route
timedatectl status
```

Record active interface/link/routes and clock synchronization. Use `iw dev <actual-interface> link` for Wi-Fi or `ethtool <actual-interface>` for Ethernet where installed. DNS or `/etc/hosts` must resolve to the selected network. Do not hard-code current IP addresses or adapter names.

On ai-brain-node, verify the existing Ollama service and model without pulling/updating during measurement:

```bash
curl --fail "$OLLAMA_HOST/api/version"
curl --fail "$OLLAMA_HOST/api/tags"
ollama ps
```

Confirm `qwen3:1.7b`, record its digest/runtime version, and verify CPU-only execution on the intended hardware after loading. Stop competing inference requests. The Python client does not force GPU/thread/sampling options; record runtime defaults as unavailable if they cannot be established. No temperature or seed override is introduced.

## 4. Archive and isolate state

Stop old publishers/controllers/gateway processes before resetting anything. Preserve previous run directories, Layer 3 database and queue/monitoring snapshots. With writers stopped, use SQLite backup or preserve the database and WAL/SHM companions together into a new archive path; verify the copy is readable.

Reset gateway state using the gateway-only section of [Full_Rerun.md](../../../Full_Rerun.md#node-3--gateway-node-django-hitl-and-active-decision-log): run migrations, clear `HitlIncident` through Django, clear the separate `decisions` table, verify zero counts. Supply that section's node-local run variables as documented. Do not execute its Node 2 Chroma/EMA cleanup. Preserve original incident IDs; repeated IDs against old HITL rows suppress intake.

On stream-node:

```bash
sudo rabbitmqctl list_queues -p fyp name consumers messages_ready messages_unacknowledged
```

Preserve DLQ and failed-run messages before any explicit disposal. If a reviewed reset requires purge, the operator may run `sudo rabbitmqctl purge_queue -p fyp <reviewed-queue>`; the baseline never purges queues automatically.

Before measured input, relevant ready/unacknowledged counts must be zero and ownership must be:

| Queue | Consumers |
|---|---:|
| anomaly.detected | 1 Single-Agent, or 1 capture worker during separate capture preparation; never both |
| auto.execute | 1 Auto Executor |
| hitl.queue | 1 HITL consumer |
| outcome.feedback | 1 Single-Agent feedback worker |
| triage.result / strategy.result | 0 |
| dead.letters | 0; inspect count without hiding evidence |

Exclusive subscriptions reject competitors. Passive checks cannot prove stale publishers are absent or identify a consumer by architecture; verify process ownership manually. Keep Ollama active for Single-Agent, but no Chroma/RAG/EMA/Learning initialization is needed.

## 5. Start Layer 3 — gateway-node

Use separate terminal/tmux panes with section 2's environment. In both Django panes:

```bash
export PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}"
export DJANGO_SETTINGS_MODULE=evaluation.baselines.common.presentation_settings
cd "$REPO/layer3/dashboard"
```

Django pane:

```bash
python manage.py runserver 0.0.0.0:8000 --noreload
```

HITL intake pane:

```bash
python manage.py consume_hitl
```

Auto Executor pane:

```bash
cd "$REPO/layer3"
python auto_executor/executor.py
```

Verify `ss -ltnp | grep -E ':8000|:8014'`, queue consumers and empty pending UI. Access `http://gateway-node:8000` to use the existing host allowlist. Shared Layer 3 still contains legacy absolute imports; use its tested checkout/interpreter and verify module resolution if relocating. The overlay changes templates, not backend or database behavior.

## 6. Start Single-Agent and warmup — ai-brain-node

```bash
cd "$REPO"
ss -ltn '( sport = :8030 )'
python -m evaluation.baselines.single_agent.controller \
  --live --run-id "$RUN_ID" --output "$RUN_BASE/controller" \
  --network-medium "$NETWORK_MEDIUM" --evaluation-mode A \
  --dataset-sha256 <verified-capture-file-sha256>
```

For Mode B select `--evaluation-mode B` and the frozen SEG corpus digest. Optional `--capture-manifest-sha256` and `--replay-speed` record declared provenance; they do not drive replay or automatically verify live payloads. Match replay arguments and verify digests independently.

Startup binds 8030, retrieves available model/runtime identity, explicitly preloads the model, then performs exactly one fixed inference: `Return the JSON object {"ready":true}.` It is not a formal incident, produces no decision and increments no measured counters. `warmup.json` retains preload/inference telemetry. Warmup failure aborts before consumers. The measured-start timestamp is recorded after successful warmup, before worker startup. Begin input only after both workers are ready:

```bash
curl --fail -s http://localhost:8030/metrics | grep fyp_single_agent_worker_up
curl --fail http://ai-brain-node:8030/metrics
```

Both controller and feedback gauges must be 1. Use the same warmup/residency protocol for Proposed Strategy in the later matched comparison. Keep load-duration telemetry per attempt; a change may indicate reload overhead but is not a calibrated reload detector. Do not mix warm and cold runs silently.

## 7. Prometheus and Grafana

Reconcile `observability/prometheus.single_agent.yml` with the live gateway config; the historical tracked Prometheus file is empty. Preserve actual exporters/authentication and use comparable scrape intervals across conditions. The template uses 5 seconds and job `fyp-single-agent-baseline`, target `ai-brain-node:8030`.

After a reviewed configuration change:

```bash
promtool check config /etc/prometheus/prometheus.yml
sudo systemctl reload prometheus
curl --fail -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=up{job="fyp-single-agent-baseline"}'
```

Require UP=1. If the deployed unit lacks reload support, use its established reload mechanism before measurement. Do not expect Proposed 8010–8013 or Threshold 8020. Preserve shared Layer 1 (8002–8008), Layer 3 (8000/8014), RabbitMQ (15692), and Node Exporter (9100) targets where applicable.

Import `observability/FYP_Single_Agent_Baseline_Observability.json`, select the correct datasource and Mode A/B. Its six rows cover overview, Layer 1, Single-Agent, Layer 3, infrastructure, hardware. Layer 1 application panels are N/A when stopped for Mode A. Missing telemetry is not zero. Feedback ratios on a dashboard are operational indicators; ID-based offline reconciliation is authoritative. Do not modify the Proposed dashboard.

## 8. Mode A — primary frozen boundary replay

Prepare the capture separately with all controllers stopped. Run unchanged Layer 1, reconcile expected incident count independently (not SEG input count), and make capture the sole boundary consumer:

```bash
cd "$REPO"
python -m evaluation.baselines.common.capture_incidents \
  --live --capture-id <unique-capture-id> --count <reconciled-count> \
  --output <new-capture-directory>
```

Freeze `incidents.jsonl` and `incidents.manifest.json` after publication/queue reconciliation. An incomplete capture has no complete manifest. If count is unknown, reconcile completed Layer 1 output and queued population first; draining that backlog freezes observed drain timing, not original publication timing. Document that schedule meaning.

Set the location of the same frozen capture on the replay node and verify offline:

```bash
export CAPTURE_DIR="/absolute/path/to/frozen-capture"
python - <<'PY'
import os
from pathlib import Path
from evaluation.baselines.common.capture_incidents import load_capture
p = Path(os.environ['CAPTURE_DIR'])
records, manifest = load_capture(p/'incidents.jsonl', p/'incidents.manifest.json')
print(len(records), manifest['sha256'])
PY
```

Stop Layer 1 and other publishers; perform cold-state preparation, startup and ownership checks. Replay using the same controller run ID, from a configured node:

```bash
python -m evaluation.baselines.common.replay_incidents \
  --live --capture "$CAPTURE_DIR/incidents.jsonl" \
  --manifest "$CAPTURE_DIR/incidents.manifest.json" \
  --run-id "$RUN_ID" --output "$RUN_BASE/replay" --speed 1
```

Same bytes, IDs, order, routing keys and schedule across controllers. Replay refuses checksum mismatch, conflicting capture identity and existing output directories. It requires one input consumer and zero ready messages; manually verify selected ownership and zero unacknowledged messages. No ad-hoc smoke publisher is used for formal experiments. Never insert labels into incident payloads.

## 9. Mode B — secondary full pipeline

Use unchanged SEG → Layer 1 → Single-Agent → shared Layer 3. Follow only [Full_Rerun.md](../../../Full_Rerun.md)'s Phase 0 Node 1 Feature Store/output cleanup, Phase 1 Layer 1 startup and frozen SEG corpus/replay procedure. Do not start its Phase 2 Proposed agents or use its Layer 2 analyzer. Set the same logical RUN_ID and node-local Layer 1 run variables. Freeze corpus/checksum/configuration/arrival speed.

Start SEG after sections 4–7 pass. Record the actual Layer 1 incident population. Do not assume it matches Mode A or a historical total. Preserve Fusion and structural-publication evidence without adding a competing capture consumer. The common analyzer currently expects a verified boundary capture; conversion of independent Mode B population evidence is a separate required step before comparative quality scoring. Mode B can run and journal decisions now, but do not substitute controller-received IDs or an unrelated Mode A capture as its independent denominator.

## 10. Human review and completion

AUTO feedback is automatic. HITL requires approve/reject/modify. Finish all cases unless a frozen protocol defines a cutoff/sample. Invalid-output fallbacks have empty proposed actions and unavailable risk/confidence; operators may modify actions. Approval is not independent correctness ground truth.

Reconcile before shutdown:

- Expected input IDs against received IDs and confirmed decisions, with missing/duplicate/conflicting cases explicit.
- AUTO/HITL totals, accepted model decisions, fallbacks, attempts, retries and validity categories.
- Accepted terminal feedback per decision; duplicate/wrong-run feedback and persisted pending HITL separately.
- Ready/unacknowledged counts at zero; DLQ empty or documented failures.
- Failures/quarantine, replay completed marker/count, both worker gauges and Prometheus target health.

Keep incomplete/failed runs and exclusion reasons. Model invalidity is not a reason to rerun a condition selectively. During operation SQLite is authoritative; JSONL appears at shutdown. Inspect evidence read-only if needed.

## 11. Shutdown and archive

After input stops and agreed completion gates pass, save final metrics/queue snapshots. Ctrl-C the Single-Agent service and wait for current work/threads to close and export. Then stop Layer 3 and applicable Layer 1 cleanly. Do not use kill -9. Archive the final database after writers stop.

| Artifact | Meaning |
|---|---|
| run.json | Identity, model/prompt/schema/runtime/network provenance and start/end times. |
| warmup.json | Separate preload and fixed-inference evidence; live only. |
| journal.sqlite3 | Durable raw deliveries, attempts, prepared/confirmed decisions, feedback and failures. |
| delivery.jsonl | Base64 exact bodies, hashes and receipt timestamps. |
| attempt.jsonl | Every completed recorded attempt, including invalid/failed attempts before dispatch. |
| decision.jsonl | Confirmed native decisions with embedded attempts, raw route, accepted output and fallback status. |
| feedback.jsonl | Raw/parsed outcomes and accounting statuses. |
| failure.jsonl | Worker/publication/startup failures. |
| quarantine.jsonl | Unidentifiable input, wrong-run input or ID collision. |

Replay produces its own run manifest/publication log/completion marker; capture has exact dataset/manifest. Preserve per-node commit/dependencies, CPU/network/clock state, database, checksums and monitoring exports in backed-up experiment storage. Generated results are ignored by Git. Commit reviewed code/docs/templates only, not runtime dumps, secrets or databases.

## 12. Analyze Mode A

```bash
python -m evaluation.baselines.common.analyze_comparison \
  --capture "$CAPTURE_DIR/incidents.jsonl" \
  --manifest "$CAPTURE_DIR/incidents.manifest.json" \
  --decisions "$RUN_BASE/controller/decision.jsonl" \
  --feedback "$RUN_BASE/controller/feedback.jsonl" \
  --run-id "$RUN_ID" --controller single_agent \
  --labels <independently-adjudicated-labels.jsonl> --expect-hitl-feedback
```

Save output to a new analysis artifact. Labels are optional: omit them to inspect completeness/workload without fabricating quality scores. Zero denominators are not computable. Missing and ambiguous records remain visible; interpret raw recommendations separately from final fallback routes. Consult [common README](../common/README.md) for denominators, action scoring and evidence scope.

## 13. Wi-Fi versus Ethernet

Keep application/model revisions, prompts/schema, rules of validation/retry, Layer 3, action vocabulary, measured options and metrics identical. Mode A keeps the same captured bytes/order/schedule; Mode B keeps the same Layer 1 corpus/configuration. Change only medium and corresponding host/IP/route configuration, verify connectivity, choose a new RUN_ID/output path and use `--network-medium ethernet`. Network metadata never enters prompting or routing.

Before formal execution, freeze independent labels, dataset/subset, repetitions/order, review policy, cutoff/rerun rules and sampling/warmup controls. Live broker/Ollama/gateway/monitoring smoke validation is still required. This implementation task does not execute the formal workload or create labels.
