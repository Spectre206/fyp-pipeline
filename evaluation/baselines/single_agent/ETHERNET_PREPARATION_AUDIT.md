# Single-Agent Ethernet preparation audit — 2026-10-04

Audited branch: `experiment/single-agent-baseline`.
Starting HEAD: `63584c7090b81e3f545f3634fd65d7d64c07734a`; initial tree clean.
Original Single-Agent implementation: `85ef940`.
Threshold procedural/deployment reference inspected with Git, without switching
or merging branches: `5bfee84af75e4ea79dbe62550d2e368fdb7437ce`.
These preparation changes require a new reviewed execution revision; the starting
HEAD does not contain them. No formal workload, consumers or inference were run.

## Ranked findings and disposition

| Severity | Finding and source | Disposition |
|---|---|---|
| CRITICAL | No new critical controller algorithm defect demonstrated by source audit and offline tests. | No algorithm change. Offline tests do not certify deployed state. |
| HIGH | Ethernet profiles/template absent; gateway `ALLOWED_HOSTS` rejected direct `.13` access. Gateway imports embedded a particular home directory; declared Layer 3 dependencies omitted `structlog`, imported by Auto Executor. | Ported the existing reviewed Ethernet files, host allowlist, node-relative import paths and dependency declaration. No package installation or Layer 3 decision/action change. |
| HIGH | Existing Single-Agent runbook lacked the formal all-node revision/corpus/ownership gates and explicit invalidation after a Layer 1 restart. | Added the full Ethernet procedure, offline snapshot validators and process/protocol evidence requirements. No auto-resume/supervisor added. |
| MEDIUM | Single-Agent `Client.warmup` preloads and makes a fixed inference; completed Proposed Adaptive had no matching dedicated warmup according to the shared contract. | Preserve Single-Agent warmup and disclose mismatch. Routing-quality scoring uses the common contract; directly matched LLM latency/residency claims are unsupported. Node 1's historical protocol file is not present locally; this audit relies on preserved shared documentation for that history. |
| MEDIUM | `Client.identity` can leave model digest/version/defaults unavailable; runtime does not enforce CPU-only residency or a clean reviewed HEAD. | Formal pre-replay gates require version/digest/freeze agreement, CPU evidence, no competing inference, exact clean revision and external inventory. Unknown effective defaults stay unknown. No model options changed. |
| MEDIUM | Shared evaluator attempt sidecar handling checks parseability/count/hash, not semantic attempt identity, sequence or validity rates. Its completion claim covers controller records only. | Require native attempt-to-decision reconciliation and all-node process history. Retain partial/failure evidence; no metric semantics changed. |
| LOW | Dedicated dashboard selected old `layer1-application` / `layer3-application` jobs. Legacy template would replace shared intervals/jobs if installed wholesale. | Migrated dashboard selectors; retained and marked standalone template legacy. Shared template preserves 21 targets with 16 active-condition targets required. |
| DOCUMENTATION | Wi-Fi described as current formal condition; Mode B required capture/conversion and legacy FAR/FER scoring. Shared Threshold example incorrectly supplied attempts. | Corrected scope, authoritative Mode B evaluator, condition-specific evidence and warmup disclosure. Historical Mode A analyzer remains explicitly legacy for final Ethernet scoring. |

## Frozen controller behavior verified

- `controller.Controller.decide`, `schema.validate`, `prompt.build`: one local
  qwen3:1.7b controller. No agent chain, Chroma/RAG, EMA, Threshold table or Policy
  override. Eight required fields; exactly three distinct allowlisted actions;
  finite confidence [0,1]; LOW/HIGH risk; AUTO/HITL route. No risk/route,
  severity/risk or confidence-threshold binding. Valid routes pass unchanged.
- `Controller.decide`: at most two generation calls for a valid incident;
  initial plus one JSON/schema-only retry. Bounded issue codes contain no desired
  route/risk. Timeout, connection, HTTP, transport and runtime-envelope errors
  do not retry. Invalid/unsupported identifiable inputs fall back without a call;
  unidentifiable input is quarantined without a fabricated decision.
- `llm_client.Client.generate`: structured output, num_ctx 2048, num_predict 512,
  35-second Requests timeout, no new seed/temperature/thread/GPU controls. HTTP
  timeout is not a hard total incident deadline.
- `Client.warmup` and `controller.main`: preload request then one fixed
  non-measured inference. Workers start only afterward. Warmup goes to warmup.json
  and does not increment measured attempt/decision counters. Failure aborts startup.
- Fallback has HITL, empty actions, null accepted risk/confidence, explicit reason,
  null accepted_model_output and fallback flag. Raw extracted route can exist
  even for invalid output; it is not the accepted or final route. Boundary
  classifications remain top-level; model classifications remain in accepted output.
- `prompt.build` whitelists incident evidence and excludes top-level labels/run/
  network metadata. Context remains untrusted; there is no claim of prompt-injection
  immunity. Approved runtime corpus must contain no ground-truth routing fields.

## Durability, replay and evaluation boundaries

`Controller.process` records delivery before normalization, completed attempts
before publication, then prepares the decision before confirmed AMQP publish.
`Journal` uses SQLite WAL/synchronous FULL and a lock shared by controller and
feedback threads. `callback` acknowledges only after durable processing. Journal
errors propagate, leaving delivery unacknowledged. A process death during an
in-flight model call can prevent a completed attempt record; preserve process
logs/failure evidence and invalidate that formal run.

Confirmed duplicate deliveries do not re-infer/republish. Unconfirmed prepared
decisions can be republished by the object without re-inference; this is not a
formal resume policy. CLI `new_run` rejects an existing directory. ID/body
collisions and wrong-run headers are quarantined. Mode B payloads do not carry
a guaranteed run header, so fresh state and sole ownership remain essential.

Feedback matches nested run/controller/event identity and route, stores evidence
before ACK, and flags duplicate/conflicting/unexpected records. Accounting does
not affect future decisions. Broker and SQLite commits are not atomic; shared
Layer 3 is not globally exactly-once. These preserved architecture limitations
are not hidden by a clean evaluator summary.

Mode B uses `shared.evaluate` with labels_routing.csv and native six JSONL
exports, including real attempt.jsonl. No boundary capture or fabricated
Triage/Strategy/Policy stages are needed. Final dispatched routes are scored;
NORMAL is excluded from anomaly FAR/FER. Expected-AUTO coverage and missing
before routing use the complete eligible corpus, separately from routing FER.
Fallback null risk is excluded from scoreable risk accuracy, not assigned an
invented tier. Feedback completion refers to observed decisions.

The native-export regression invokes the actual CLI with attempt evidence and an
unobserved eligible label: feedback can be complete while coverage is partial.
An explicitly supplied missing attempt file fails. Publication-failure testing
confirms retained attempts and no additional inference on object redelivery.
The shared evaluator, label policy/generator and all controller algorithm files
remain unchanged.

## Files and preparation scope

Added [ETHERNET_FULL_RUN.md](ETHERNET_FULL_RUN.md),
[ethernet_checks.py](ethernet_checks.py), this audit and
[tests/test_ethernet.py](tests/test_ethernet.py); imported the four existing
`deployment/ethernet/` files. Updated the three Single-Agent entry/reference
documents, shared contract, dashboard/legacy-template notice and four gateway
deployment compatibility files.

`ethernet_checks` starts nothing. It validates exact required target identities,
15 queue ownership/backlog records, two ready worker gauges, the complete frozen
corpus/label distribution and a reviewed per-node revision inventory. It wraps
the shared branch/HEAD/clean-tree/index-flag gate and additionally verifies
controller files against the execution commit. Hashes pin event order as well
as contents. Helpers do not grant approval, certify installed settings, prove
process identity from counts, or reconstruct uninterrupted history.

The runbook records RUN_SETUP → PRE_REPLAY_GATE → REPLAY_STARTED → REPLAY_ENDED
→ DRAINED → GRACEFUL_SHUTDOWN → OFFLINE_EVALUATION → COMPLETED_UNINTERRUPTED.
Failure makes the run FAILED_INCOMPLETE; restarting after replay makes it
RESUMED_INVALID_FOR_FORMAL_COMPARISON. Preserve all evidence and use a new cold
RUN_ID. A Node 1 replay marker is not a distributed restart lock.

Reviewers use neutral presentation and must not consult routing/safety/risk
labels. Approve sensible proposals, modify when needed, reject inappropriate
ones. Empty-action fallback can legitimately require modification or rejection.
No target approval fraction is specified.

## Remaining formal-run prerequisites

Review, commit and distribute a new exact execution revision through the normal
process; prepare externally reviewed per-node manifests and approved corpus/
label hashes. Freeze clock tolerance, deadlines/drain criteria, repetitions,
review/monitoring policy and warmup disclosure. Verify dependencies, model digest/
version and CPU-only runtime, actual Ethernet links/routes/sockets, process
ownership, installed Prometheus configuration and Grafana panels on the nodes.
Complete a separately identified integration smoke and archive/reset its state.
No offline test or document preparation substitutes for these live gates.

## Offline validation results

- `venv/bin/python -B -m unittest discover -s evaluation/baselines/shared/tests -p 'test_*.py' -v`: 26 passed.
- `venv/bin/python -B -m unittest discover -s evaluation/baselines/single_agent/tests -p 'test_*.py' -v`: 99 passed, including 11 new Ethernet tests.
- `promtool check config deployment/ethernet/prometheus.ethernet.yml`: passed.
- All 28 Bash blocks in the full Ethernet runbook passed `bash -n`; local
  Single-Agent Markdown links resolved and dashboard JSON parsed.
- Byte/diff checks confirmed Single-Agent controller, feedback, LLM client,
  metrics, prompt and schema unchanged, as well as Layer 1, common runtime,
  routing policy/generator and shared evaluator code.
- `git diff --check`: passed. No services, workload, inference, installation,
  staging, commit or push occurred. Live deployed checks remain outstanding.
