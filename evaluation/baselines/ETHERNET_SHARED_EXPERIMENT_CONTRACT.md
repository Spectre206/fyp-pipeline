# Shared Ethernet experiment and offline evaluation contract

Status: final shared contract for the three completed formal Ethernet conditions.
This document does not itself authorize a new execution. Historical scaffolding
reference: branch `feature/ethernet-migration`, pre-change HEAD
`3212732f86c4b398453389d0abed2b016b59b4d6`; completed Proposed adaptive-EMA run
`ethernet_cold_20261002_023108` executed at
`c595459ce64a479a2bf725df2fbffb7142d6f66b`, deployment base
`c0ad6be9c84955240cf4499d586ad46b1d579ecc`.

Applies to exactly Proposed Adaptive, Threshold-only and Single-Agent. Preserve architectural differences. This Mode B contract is
not a substitute for the primary Mode A identical-incident comparison.

## Frozen inputs and metrics

Use the same physical nodes, Ethernet transport, frozen 1,950-event source,
configuration, event IDs and order, and replay speed **1**. Reuse byte-identical
approved files with manifest verification; do not regenerate timestamps/UUIDs
for a matched comparison. Runtime never receives ground-truth labels.

[Routing-label-policy-v2](../../layer2/evaluation/ROUTING_LABEL_POLICY.md) and its
source-only generator remain unchanged. NORMAL is blank/excluded; ANOMALY + LOW
+ AUTO_RESTART_CONSUMER is AUTO/true; ANOMALY + HIGH + ESCALATE_TO_HITL is
HITL/false; inconsistent anomaly combinations fail. `true` means benchmark
autonomous eligibility, not operational safety certification. The shared reader
checks this translation, unique IDs and CSV structure; it does not infer labels
from controller outcomes or invent acceptable-action annotations.

Final shared definitions (join by event_id; exclude NORMAL/unlabeled routing):

- FAR = actual AUTO with `safe_to_auto=false` / actual AUTO with an authoritative
  nonblank `safe_to_auto` label.
- Routing FER = expected AUTO routed HITL / expected AUTO with a valid AUTO/HITL
  controller decision.
- Expected-AUTO Controller Coverage = expected AUTO with a valid decision / all
  380 authoritative expected-AUTO corpus IDs.
- Expected-AUTO Missing Before Routing = expected AUTO without a scoreable
  decision / all authoritative expected-AUTO corpus IDs.

Policy Coverage is the Proposed-system name for Controller Coverage. Missing
upstream cases must not dilute routing FER. Zero denominators are
`not_computable`, with null values. A conflict or invalid record is not an actual
scoreable routing decision: it reduces scoreable coverage but must be reported
as an integrity issue, not silently called a physical upstream miss. On a clean
run these sets coincide. Preserve missing-record, conflict, malformed and
received-without-decision evidence when interpreting coverage.

Risk accuracy uses `ground_truth_risk_tier` versus the controller's reported
LOW/HIGH tier, excluding NORMAL and absent reported risks. It does not invent a
risk value for fallback decisions. No action-quality labels are inferred.

## Existing branch audit and new evaluation entrypoint

Audited Threshold `931450a6ac82e280134e1b5145d1c104608b15df` and Single-Agent
`85ef940825f7aac81e6aeff98a94151f63795b7d`:

- Existing `common/analyze_comparison.py` expects JSONL `incident_id`,
  `expected_route`, boolean `safe_to_auto`, `expected_risk`, `acceptable_actions`.
  FAR uses the unsafe population; FER uses the complete eligible label set.
  Those definitions are superseded for this three-condition Ethernet comparison.
  Do not use that CLI for the frozen routing CSV or Mode B final routing scores.
- Both `decision.jsonl` exports contain `event_id`, `run_id`, `controller`,
  `routing_decision`, `risk_tier`, actions and timing. `event_id` is preserved from
  the Mode B source incident. Single-Agent additionally records raw/final route,
  validation/fallback state and attempts. Threshold is deterministic.
- Journal prepare precedes publish; confirmed decisions enter exported decision
  records. `journal.sqlite3` and its consistent backup remain evidence of
  prepared/unconfirmed state. Stop/flush before using final JSONL exports.
- `feedback.jsonl` wraps payloads with `status`, run/controller identity,
  event ID and outcome. Accepted outcomes must match the decision route and
  embedded Layer 3 envelope. Duplicates/conflicts/rejected feedback stay visible.
- `delivery.jsonl` contains base64 raw message bytes; quarantine/failure exports
  retain rejected input and errors; Single-Agent `attempt.jsonl` retains each
  model attempt and telemetry. These are separate from routing decisions.

The new module is independent of controller runtime imports:

```bash
python -B -m evaluation.baselines.shared.evaluate \
  --labels "$LABELS_ROUTING" \
  --decisions "$CONTROLLER_DIR/decision.jsonl" \
  --feedback "$CONTROLLER_DIR/feedback.jsonl" \
  --deliveries "$CONTROLLER_DIR/delivery.jsonl" \
  --quarantine "$CONTROLLER_DIR/quarantine.jsonl" \
  --failures "$CONTROLLER_DIR/failure.jsonl" \
  --controller threshold_only --run-id "$RUN_ID" \
  --output "$ANALYSIS_DIR" --expect-hitl-feedback
```

Threshold has no model-attempt sidecar. For Single-Agent select `single_agent`
and include `--attempts "$CONTROLLER_DIR/attempt.jsonl"` for its real attempt
export; do not manufacture an empty placeholder for Threshold. Proposed retains
its native agent/stage evidence and evaluator under the shared metric definitions.
Explicit paths are node-local;
`ANALYSIS_DIR` must not exist. Omit the exhaustive HITL flag only under a frozen
sampled-review protocol; AUTO feedback is always expected. Optional missing
artifact arguments are omitted, never replaced by fabricated empty evidence.
A formal baseline run should provide all journal exports and explain omissions.
No proposed triage/strategy/policy/learning files or live capture are required.
No experiments are triggered by this evaluator.

Canonical normalized decision fields:

| Field | Meaning |
|---|---|
| event_id | Original join identity |
| actual_route | AUTO or HITL |
| reported_risk | LOW/HIGH or null |
| decision_timestamp | publish_confirmed_at, else decision_ready_at; source field semantics retained |
| controller_name / run_id | Explicit selected identity |
| source_record | Input path and line number |
| validation_metadata | Existing attempts, validation, fallback and raw route, where present |

Identical semantic duplicates are counted once but flagged. Route/risk/action/
validation conflicts exclude that ID from scoring, even if a later row repeats
an earlier value. Wrong-run, unknown IDs and malformed input remain explicit.
Feedback is deduplicated by ID/payload; conflicting feedback is not completion.
All JSON rejects nonfinite values. Artifact errors yield `review_required` in
the summary, not automatic success. The CLI's normal exit means analysis was
written; operators must inspect integrity status and completion evidence.

## Mode B offline reconciliation and completion

Never attach a second capture consumer to `anomaly.detected` during a real run.
Use frozen source labels plus controller journal exports offline. Distinguish:

1. All source corpus IDs and anomaly IDs.
2. Observed receipt IDs from delivery payloads, when available.
3. Unique, valid routing decisions.
4. Accepted feedback and missing required feedback.
5. Expected-AUTO IDs without scoreable routing decisions.

Delivery records lack an independent run tag, so their provenance must come
from the fresh run directory, `run.json` and manifest. They establish observed
receipt, not necessarily accepted normalization. If delivery evidence is absent,
received count is null; do not equate decisions with receipts.

Source-to-decision absence is not automatically failed delivery. Preserve
Layer 1 baseline/calibration, detector and Fusion outputs, structural bypass,
queue and replay evidence. Explain calibration withholding, Fusion suppression,
structural bypass, failures and unresolved IDs separately in reconciliation.txt.
The evaluator reports sets; it does not infer causal reasons from labels or
fabricate detector TP/FP performance. Receipt without decision is an integrity
review item. Corpus coverage alone does not establish experimental completion.

A clean controller journal is not proof of an uninterrupted experiment. Any
application-worker death or restart after replay begins and before required
completion invalidates the formal run, including upstream Layer 1 workers.
Preserve failures and classify a same-RUN_ID restart as
`RESUMED_INVALID_FOR_FORMAL_COMPARISON`; never rehabilitate it based on later
clean exports. Use a new RUN_ID and cold state for the replacement experiment.

Keep an append-only protocol-event record with occurrence/recording UTC times,
node/worker identity, evidence references and eligibility, distinguishing
`IN_PROGRESS`, `FAILED_INCOMPLETE`, resumed-invalid, and reviewed
`COMPLETED_UNINTERRUPTED`. Unknown event times must not be invented. The offline
evaluator does not by itself certify process continuity; replay markers guard
publication, not worker launches. Process-start/exit logs, boot ID/PID/start-time
evidence, queue state and metrics history support that review. Final snapshots
alone cannot prove absence of restarts.

Freeze cutoff duration, drain timeout, review scope and rerun criteria before
publication; this contract does not invent numeric cutoffs. Completion requires:

- One successful replay; partial/failed publication is archived as failed and
  never reused as a fresh run.
- Intended sole controller ownership and drained ready/unacknowledged queues,
  including feedback; no unexplained DLQ.
- Required human review complete (zero pending for exhaustive review).
- Flushed journal exports; no unresolved duplicates, conflicts or unexpected IDs.
- Offline reconciliation complete, input/output hashes saved, monitoring and
  transport evidence preserved. Archive state before any later reset.

## Topology, environment and applicable cold state

| Node | Ethernet | Role |
|---|---|---|
| stream-node | 10.10.10.11, enp2s0 | RabbitMQ, unchanged SEG/Layer 1 for Mode B, exporter |
| ai-brain-node | 10.10.10.12, enp2s0 | Exactly one controller; local model only where applicable |
| gateway-node | 10.10.10.13, enx00e04c681057 | Shared Auto Executor, HITL/Django/SQLite, monitoring |

Source the reviewed deployment Node 2/3 profiles in every application pane.
RabbitMQ host 10.10.10.11, port 5672, vhost fyp; supply user/password securely.
Local Ollama remains localhost:11434. Wi-Fi stays the Internet/default route;
do not rewrite hostname resolution merely to change transport. Verify actual
routes, established sockets and broker peers; save before/after counters.

Each node sets its own `REPO=$HOME/fyp-pipeline`, the same literal RUN_ID, and
`RUN_ROOT=$REPO/experiment_runs/$RUN_ID`. Node 1 also sets SEG_RUN_DIR. Baselines
use required `--run-id`, `--output`, `--network-medium ethernet`, verified dataset
hash and controller-specific CLI metadata; they do not need Proposed
LAYER2_EVALUATION_* variables. Source pane environments explicitly, not through
undocumented .bashrc assumptions. Preserve virtual environments and dependencies.

Before replay: stop stale publishers/consumers; archive prior evidence; purge
experiment queue messages without deleting topology; verify zero ready/unacked;
reset applicable Layer 1 calibration/runtime outputs and restart processes;
reset gateway HITL and decisions tables after consistent database backup;
create fresh output directories. Preserve old runs, source files and history.

| Condition | Additional cold-state semantics |
|---|---|
| Threshold | Fresh journal; no LLM, Chroma, EMA or confidence/learning additions |
| Single-Agent | Fresh journal; existing local model protocol; no Chroma/EMA |
| Proposed adaptive | Chroma empty; EMA 0.65, update_count 0, alpha 0.9 |

Start infrastructure/topology, applicable Layer 1, selected controller and shared
Layer 3; verify ownership, worker readiness, endpoints and transport before input.
Only the selected controller owns anomaly.detected and its feedback path.

## Evidence inventory and paths

Keep existing baseline internal layout:
`evaluation/baselines/results/<controller>/ethernet/<RUN_ID>/{controller,replay}/`.
Do not pre-create controller/replay directories that their CLIs create exclusively.
Map them into a node-qualified inventory under the common RUN_ROOT; recording
paths is sufficient, and copying into an archive must preserve hashes.

| Evidence | Logical common destination/reference |
|---|---|
| Frozen events/config/source and routing labels | seg/ or offline_eval_inputs/; labels offline only |
| Controller run.json, SQLite journal, all JSONL exports | Existing baseline controller/ directory reference |
| Replay start/end/status/log and publication evidence | replay/ reference; Mode B SEG logs may be in RUN_ROOT |
| Normalized decisions, evaluation_summary.json | offline_eval_inputs/analysis/ |
| integrity_report.json, verification_report.json, manifest.json | Same new analysis directory |
| Revision contract/output, corpus/config/label hashes | metadata.txt and reviewed revision manifest |
| Routes, links, sockets, peers, queue state, clock evidence | transport/ |
| Metrics snapshots and time-window observations | metrics/ |
| Layer 1 outputs/calibration/suppression reconciliation | layer1_runtime/ and reconciliation.txt |
| Shared gateway state | decisions-final.db and final state counts |

Record RUN_ID, condition/controller, medium, per-node branch/full commit,
working-tree cleanliness, evaluation/deployment/policy revisions and hashes,
corpus/config/source-label/routing-label hashes, replay speed, timestamps,
hardware/dependencies/model settings where applicable, review/warmup/cutoff
protocol and deviations. Keep node names in collection paths to prevent collision.
The evaluator hashes supplied inputs, its code/policy generator and outputs;
its manifest is analysis provenance, not a complete deployment approval.
Retain superseded outputs under unique historical names before recalculation.

## Cross-node copy procedure

Use destination HOME-relative paths; never expand a source node's absolute home
into the remote destination. Analysis may occur on any approved node. The
following pattern copies a prepared immutable bundle; build it from only needed
non-secret files (labels.csv, labels_routing.csv, decision.jsonl, feedback.jsonl,
optional journal exports and provenance). Preserve source-node-qualified paths.

```bash
# Source node: approved immutable bundle already assembled and reviewed.
cd "$BUNDLE_DIR"
sha256sum labels.csv labels_routing.csv decision.jsonl feedback.jsonl > transfer.sha256
# Set a validated run identity and actual destination account/address.
[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]] || exit 1
DEST_REL="fyp-pipeline/experiment_runs/$RUN_ID/offline_eval_inputs/from-ai-brain-node"
ssh "$DEST_HOST" "umask 077; mkdir -p \"\$HOME/fyp-pipeline/experiment_runs/$RUN_ID/offline_eval_inputs\" && mkdir \"\$HOME/$DEST_REL\"" || exit 1
scp labels.csv labels_routing.csv decision.jsonl feedback.jsonl transfer.sha256 \
  "$DEST_HOST:$DEST_REL/"
ssh "$DEST_HOST" "cd \"\$HOME/$DEST_REL\" && sha256sum --check --strict transfer.sha256 && sha256sum labels.csv labels_routing.csv decision.jsonl feedback.jsonl" \
  > destination-hashes.txt
```

Use a new destination bundle path; do not overwrite prior evidence. For extra
exports or corpus/config files, include their exact bare filenames in both hash
and transfer lists. Check the transferred manifest's own hash against the source
copy through the provenance record. Archive source transfer.sha256 and destination
verification output. Existing source SEG config may contain credentials: use
protected storage; do not publish unredacted copies. A labels-only transfer needs
only the two CSVs and their manifest. Never copy labels into runtime queues.

## Reviewed revision manifest and gate

The historical runbook gate is retained for reproducing its old reference; it
allows only the runbook difference from c0ad6be and therefore cannot authorize
current evaluation files or baseline branches. Do not disable or broaden it
implicitly. Future baseline runbooks must explicitly select this new reviewed
manifest gate with their own controller reference.

A reviewed JSON manifest contains these keys (no placeholder is an approval):

```json
{
  "controller_branch": "experiment/threshold-baseline",
  "controller_commit": "FULL_APPROVED_COMMIT",
  "shared_evaluation_revision": "FULL_APPROVED_COMMIT",
  "deployment_profile_revision": "FULL_APPROVED_COMMIT",
  "routing_policy_revision": "FULL_APPROVED_COMMIT",
  "review_reference": "external reviewed freeze record",
  "files": {
    "shared_evaluation": [{"path": "evaluation/baselines/shared/evaluate.py", "sha256": "APPROVED_HASH"}],
    "deployment": [{"path": "deployment/ethernet/node2.env.sh", "sha256": "APPROVED_HASH"}],
    "routing_policy": [{"path": "layer2/evaluation/generate_routing_labels.py", "sha256": "APPROVED_HASH"}],
    "corpus": [{"path": "experiment_runs/RUN/seg/events_1950.jsonl", "sha256": "APPROVED_HASH"}]
  }
}
```

This is a schema illustration, not a complete inventory. Review must enumerate
all shared evaluator/tests/dependencies, deployment profiles/Prometheus/gateway
settings/dependencies, policy specification/generator, and all four frozen
corpus/config/source-label/routing-label files. Use per-node copies with each
node's local paths and applicable files; no absolute home paths. All nodes use
the approved controller commit; distinct source revision fields document shared
component provenance. Require reviewed manifests to agree on common hashes.
Do not derive approved expected hashes from the candidate immediately before
checking and call that independent review.

```bash
python -B -m evaluation.baselines.shared.verify_revision \
  --repo "$REPO" --manifest "$APPROVED_REVISION_MANIFEST" \
  > "$RUN_ROOT/transport/revision-before.json"
```

The verifier requires exact branch/HEAD, full resolvable revision IDs, clean
tracked/untracked state, no assume-unchanged/skip-worktree flags, and reviewed
file hash matches, including each shared/deployment/policy file against its
recorded source revision. It verifies the supplied inventory, not its completeness or
human approval. Installed models, secrets, external Prometheus config and process
state require separate evidence. Runtime-only excludes may cover a specific run
folder, never source changes. Record the manifest hash and repeat before replay.
Completed runs retain their actual reviewed execution revisions. Any new run
requires its own reviewed freeze; integration HEAD is not a replacement for
historical execution identities.

## Monitoring compatibility plan

Keep the Ethernet template's logical labels and job names:

| Condition, full Mode B | Required application targets |
|---|---|
| All | fyp-layer1: 8002–8008 on .11; fyp-layer3-autoexec: .13:8014; fyp-layer3-hitl: .13:8000 |
| Threshold | fyp-threshold-baseline: .12:8020 |
| Single-Agent | fyp-single-agent-baseline: .12:8030 |
| Proposed Adaptive | fyp-agent-pipeline: .12:8010–8013 |

Also require fyp-cluster's three :9100 targets and rabbitmq .11:15692. When
retaining the template, local prometheus:9090 and node:9100 are expected healthy.
Thus 21 configured targets remain: Proposed expects 19 UP/2 intentionally
inactive; either baseline expects 16 UP/5 intentionally inactive. Inspect target
identities, not just counts. This gate is Mode B; Mode A does not require Layer 1.

For later baseline dashboard migration, replace `job="layer1-application"` with
`job="fyp-layer1"`; replace `job="layer3-application"` with
`job=~"fyp-layer3-autoexec|fyp-layer3-hitl"`. Update combined regex selectors too.
Retain baseline exporter names `fyp_threshold_*`/`fyp_single_agent_*`, job names,
and logical instance labels. Check each query/panel after adaptation. Do not
install old baseline Prometheus templates wholesale: they use different jobs
and global intervals. Preserve the reviewed Ethernet 15s global/selected 5s
intervals. The Single-Agent Ethernet preparation includes this selector migration and the
shared deployment template; installed configuration still needs live verification.

Inactive controllers need not be UP; never start them to turn a panel green.
Preserve queue backlog/DLQ, CPU/memory/disk/network and NTP-offset evidence.
Verify actual sockets/routes, because combined Wi-Fi/Ethernet network charts do
not prove transport. A dashboard NTP panel is not by itself a clock-sync gate.

## Timing and Single-Agent warmup disclosure

| Existing baseline field | Boundary and limitation |
|---|---|
| processing_seconds | Monotonic callback entry through decision construction, before journal prepare/publish; Threshold rules vs Single-Agent model/retry work |
| publish_seconds | AMQP publish/confirmation operation |
| received_at → decision_ready_at | Controller receipt to decision readiness, not source-event E2E |
| publish_confirmed_at | Recorded after confirmed publication; differs from decision-ready endpoint |
| input_queue_wait_seconds | replay_published_at header to received_at |
| boundary_to_decision_seconds | replay_published_at header to publish_confirmed_at |
| feedback received_at | Baseline recorder receipt, not human decision time or necessarily gateway outcome timestamp |

Mode B does not guarantee the replay_published_at boundary header required by
the two baseline boundary metrics. Missing timestamps are unavailable, never
zero or replaced with processing time. This shared evaluator intentionally
reports no inferred latency; preserve source timing for separately validated
comparisons. Proposed control-plane, source-ingestion-to-decision E2E and
policy-to-feedback timing must be compared only after matching definitions and
clock synchronization. Feedback completion counts do not establish latency.

Single-Agent currently uses qwen3:1.7b, structured output, one eligible validation
retry and fallback, and performs preload plus a fixed warmup inference before
measurement. The completed adaptive-EMA run had no dedicated matching warmup.
The Single-Agent Ethernet preparation retains and discloses this difference.
Routing-quality metrics remain comparable under the common routing contract;
directly matched LLM latency/residency comparisons are not established. Record
this in the reviewed protocol before execution. Do not remove its warmup, add one to Threshold or
retroactively claim the completed Proposed run was warmed.

## Migration boundaries

Controller branches retain their own runtime semantics. Single-Agent preparation
uses the shared Ethernet deployment profile, dedicated dashboard selectors,
revision checks and full runbook, while retaining its model/warmup protocol.
Offline preparation does not certify installed state or authorize workload
execution. Complete isolated integration checks and the reviewed freeze before
formal use. No Chroma, EMA, proposed Triage/Policy/Learning or fake stage metrics
are introduced into either baseline.

## Single-Agent formal run lifecycle

The [Single-Agent Ethernet runbook](single_agent/ETHERNET_FULL_RUN.md) records
RUN_SETUP, PRE_REPLAY_GATE, REPLAY_STARTED, REPLAY_ENDED, DRAINED,
GRACEFUL_SHUTDOWN, OFFLINE_EVALUATION and COMPLETED_UNINTERRUPTED. Any worker
failure after replay begins makes the run FAILED_INCOMPLETE; a same-ID restart
makes it RESUMED_INVALID_FOR_FORMAL_COMPARISON. Preserve evidence and start a
new cold run under a new ID. Replay markers prevent repeat publication, not
worker restarts. Clean controller records/complete feedback do not certify
upstream continuity. Review process and protocol history across all nodes.
