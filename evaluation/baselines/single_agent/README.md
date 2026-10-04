# Single-Agent comparative baseline

The Single-Agent baseline combines remediation proposal generation, confidence,
risk assessment and AUTO/HITL routing in **one local qwen3:1.7b controller**. It
provides a monolithic LLM comparison condition alongside the Threshold-only
baseline and Proposed Adaptive system. These are the three formal Ethernet
conditions.

The formal Ethernet Mode B run
`single-agent-ethernet-full-20261004-035637` completed as
`COMPLETED_UNINTERRUPTED`. All 639 incidents received valid first-attempt
structured output, but 638 decisions went to HITL. Structured-output validity
and autonomous-routing quality are different properties: routing FER was
239/240 = **99.58%**, while FAR was 0/1 = **0.00%** on only one AUTO decision.

## Architecture and message flow

```text
Frozen SEG corpus → unchanged Layer 1
  → RabbitMQ anomaly.detected
  → one local LLM controller → generic output validation
  → accepted model route or invalid/unavailable-output HITL fallback
  → RabbitMQ auto.execute / hitl.queue → shared Layer 3
  → outcome.feedback → accounting-only worker and durable journal
```

There is no Triage Agent, Strategy Agent, deterministic Policy Agent, Learning
Agent, Chroma/RAG, EMA adaptive threshold or proposed-system multi-agent
coordination inside this baseline. There is no Threshold rule table or hidden
risk/confidence routing override. Feedback records completion and does not
change subsequent decisions. Legacy agent-named keys in the Layer 3 compatibility
envelope are serialization aliases, not executed agent stages.

The model returns exactly eight fields: `anomaly_type`, `severity`,
`affected_component`, `recommended_actions`, `confidence`, `risk_tier`,
`routing_decision` and `reasoning`. Validation requires exactly three distinct
allowlisted actions, finite confidence in [0,1], LOW/HIGH risk and AUTO/HITL
routing, with no extra fields. No severity-to-risk or risk-to-route binding and
no confidence threshold are imposed. A valid model route passes unchanged.

A valid incident permits at most **two measured model calls**: initial generation
plus one retry only for malformed JSON or schema-validation failure. Retry
feedback contains bounded validation codes, not a desired route or risk. Timeout,
connection, HTTP/transport and runtime-envelope failures do not retry. Exhausted
or unavailable output falls back to HITL with empty actions, null accepted
risk/confidence and an explicit reason. Identifiable invalid/unsupported inputs
can fall back without inference; unidentifiable inputs are quarantined.

Native evidence separates the last extracted raw model route, validated
`accepted_model_output`, final dispatched route and fallback status. Fallback is
not valid model output. See [SINGLE_AGENT_BASELINE_SYSTEM.md](SINGLE_AGENT_BASELINE_SYSTEM.md)
for normalization, durability, prompt/schema and adapter details.

## Evaluation modes and Ethernet protocol

**Mode A** is the primary control-plane study: replay identical captured incident
bytes at the controller boundary across conditions. **Mode B** reruns the same
frozen source corpus through unchanged Layer 1, the selected controller and
shared Layer 3. The completed result below is **Mode B**; it does not substitute
for an identical-incident Mode A experiment.

| Node | Ethernet address | Role |
|---|---|---|
| stream-node | 10.10.10.11 | RabbitMQ and unchanged SEG/Layer 1 |
| ai-brain-node | 10.10.10.12 | Local Ollama, Single-Agent and feedback workers; metrics :8030 |
| gateway-node | 10.10.10.13 | Django/HITL :8000, Auto Executor :8014, Prometheus/Grafana |

The formal procedure reuses the approved 1,950-event corpus, event IDs/order,
SEG configuration and frozen routing labels at replay speed 1. Ground truth is
used offline only and is withheld from runtime prompting and human review.
Start with cold Layer 1 calibration/runtime state, fresh controller output and
reset gateway experiment state; no Chroma/EMA reset applies to this baseline.
Verify reviewed revision/hashes, sole queue ownership, worker readiness,
Ethernet transport, clocks and monitoring before one replay. Then complete human
review, drain queues, shut down gracefully, evaluate and archive node-local
artifacts. Any worker failure/restart after replay begins invalidates that formal
RUN_ID; clean controller exports alone cannot certify uninterrupted execution.

Follow [ETHERNET_FULL_RUN.md](ETHERNET_FULL_RUN.md) for the complete procedure,
[shared Ethernet contract](../ETHERNET_SHARED_EXPERIMENT_CONTRACT.md) for scoring,
and [Baseline Experiment Design](../BASELINE_EXPERIMENT_DESIGN.md) for research
scope. [Run_Single_Agent_Baseline.md](Run_Single_Agent_Baseline.md) and the
[preparation audit](ETHERNET_PREPARATION_AUDIT.md) retain historical/Mode A and
pre-run context; they are not new result records.

Use the [Ethernet deployment profile](../../../deployment/ethernet/README.md)
and [shared Prometheus template](../../../deployment/ethernet/prometheus.ethernet.yml),
with the [Single-Agent dashboard](observability/FYP_Single_Agent_Baseline_Observability.json).
Do not replace the shared configuration with the legacy standalone template or
start competing controllers merely to make inactive targets green.

## Final Formal Ethernet Result

### Run identity and evidence scope

| Field | Recorded value |
|---|---|
| Run ID | `single-agent-ethernet-full-20261004-035637` |
| Branch | `experiment/single-agent-baseline` |
| Execution commit | `c09160c506686234d65041cbb83ea63a0ecd575c` |
| Formal status | `COMPLETED_UNINTERRUPTED` |
| Network / evaluation mode / replay speed | Ethernet / B / 1 |
| Routing policy | `routing-label-policy-v2` |
| Controller model | `qwen3:1.7b` |
| Ollama version | `0.18.0` |
| Model digest | `8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7` |

The results below come from completed formal run evidence. Formal closeout
verified the native decision.jsonl, feedback.jsonl, delivery.jsonl and
attempt.jsonl counts (639 each), quarantine.jsonl and failure.jsonl counts
(zero each), evaluation_summary.json, integrity_report.json and
verification_report.json, together with Layer 1 reconciliation, Layer 3 outcomes,
lifecycle/process evidence and node-local artifact inventories.

This documentation-only audit was performed from the gateway-node checkout.
It inspected local metrics, frozen labels, protocol-freeze and lifecycle records,
revision verification, HITL counts and process snapshots. Native Node 2 exports
and analysis were not locally available for independent reinspection in this
audit; their absence from gateway does not negate the formal closeout
verification. Model identity and Node 2 results are retained from the completed
formal run evidence. This documentation edit did not rerun the evaluator or
regenerate any experiment results.

### Layer 1 reconciliation

| Measure | Count |
|---|---:|
| Source events | 1,950 |
| Structurally valid | 1,850 |
| Structural schema bypass incidents | 100 |
| TYPE_MUTATION / MISSING_FIELD | 50 / 50 |
| Detector/Fusion-eligible after cold start, per detector | 1,527 |
| Fusion published | 539 |
| Fusion suppressed | 988 |
| Compound | 43 |
| Fast path | 83 |
| Fusion errors | 0 |
| Controller incidents: Fusion + structural bypass | 539 + 100 = 639 |

The source population is distinct from the controller population. Calibration
and Fusion filtering occur before controller routing; structural schema bypass
incidents reach the controller separately. Compound and fast-path counts are
Fusion characteristics, not extra incidents to add to the published total.

### Controller execution and human outcomes

| Measure | Count |
|---|---:|
| Controller incidents | 639 |
| Decision / feedback / delivery / attempt records | 639 / 639 / 639 / 639 |
| Initial model calls | 639 |
| Valid first-attempt outputs | 639 |
| Schema-valid first-attempt outputs | 639 |
| Quarantine / failure records | 0 / 0 |
| Actual AUTO / HITL | 1 / 638 |
| HITL APPROVED / MODIFIED / REJECTED / PENDING | 636 / 1 / 1 / 0 |
| AUTO_EXECUTE_SUCCESS | 1 |
| Feedback completion | 639/639 = 100% |

### Routing confusion matrix

This is the authoritative shared-evaluator cross-tab of **630 anomaly decisions**.
Nine NORMAL decisions are excluded from anomaly FAR/FER; they account for the
remaining HITL decisions in the overall route totals.

| Ground truth | Actual AUTO | Actual HITL | Scoreable anomaly decisions |
|---|---:|---:|---:|
| Expected AUTO | 1 | 239 | 240 |
| Expected HITL | 0 | 390 | 390 |
| Total | 1 | 629 | 630 |

The frozen labels contain 1,000 NORMAL events, 380 expected-AUTO anomalies and
570 expected-HITL anomalies. Of the 380 expected-AUTO corpus incidents, 240 have
a scoreable controller decision and 140 are missing before routing.

### Shared metrics

| Metric | Fraction | Result |
|---|---:|---:|
| False autonomy rate (FAR) | 0/1 | 0.00% |
| Routing FER | 239/240 | 99.58% |
| Expected-AUTO controller coverage | 240/380 | 63.157895% |
| Expected-AUTO missing before routing | 140/380 | 36.842105% |
| Risk accuracy | 443/630 | 70.317460% |
| Feedback completion | 639/639 | 100% |

Fractions are authoritative; percentages are rounded. FAR divides actual AUTO
decisions on incidents labeled `safe_to_auto=false` by actual AUTO decisions
having an authoritative nonblank eligibility label. For this run, the numerator
is 0 and denominator is 1, giving FAR = 0%. Routing FER divides expected-AUTO
incidents routed HITL by expected-AUTO incidents with a valid controller routing
decision; it does not use the entire eligible corpus as its denominator.
Coverage and missing before routing report that separate corpus boundary.
Risk accuracy compares reported LOW/HIGH risk with independent ground truth on
scoreable anomalies; unavailable fallback risk is not assigned an invented tier.
Feedback completion concerns observed decisions, not all 1,950 source events.

Labels follow [routing-label-policy-v2](../../../layer2/evaluation/ROUTING_LABEL_POLICY.md).
The authoritative Mode B scorer is `evaluation.baselines.shared.evaluate`, using
native journal exports and `--attempts` for real Single-Agent model evidence.
The legacy common analyzer is not the final Mode B scorer. Attempt-sidecar
parse/count checks do not themselves certify every attempt's semantic validity;
preserve native attempt/decision reconciliation as well as aggregate counters.

### Completion and integrity

The formal closeout evidence records all queues drained, zero pending HITL,
639/639 decision/feedback reconciliation and an uninterrupted lifecycle, with no
FAILED_INCOMPLETE or RESUMED_INVALID_FOR_FORMAL_COMPARISON event. Application
process identities remained unchanged from pre-replay to pre-shutdown.
The local gateway log and process snapshots corroborate these statements for
gateway applications; two snapshots alone do not prove continuous execution on
all nodes.

The evaluator checks verified during formal closeout contain zero duplicate decision IDs, conflicting
decisions, conflicting feedback, missing feedback IDs, unexpected decision IDs,
unexpected delivery IDs and malformed decision/feedback/delivery lines; failure
and quarantine counts are also zero. The verification report records
`far_fer_coverage_agreement=true`. These checks complement protocol evidence;
they do not independently establish upstream continuity.

## Interpretation

This run was technically reliable in producing structured output and completing
feedback, but extremely conservative in autonomous routing. All 639 incidents
received valid first-attempt outputs; 638/639 final routes were HITL, including
239 of the 240 scoreable expected-AUTO incidents. The resulting routing FER of
99.58% illustrates why schema compliance must be evaluated separately from
routing quality.

**Zero FAR does not establish that this is the best or safest controller.** Its
denominator is only one AUTO decision. Human approval of most HITL proposals
also does not establish independent routing correctness or verified service
restoration. The result supplies comparative evidence to analyze jointly with
Threshold-only and Proposed Adaptive; it does not by itself
prove the proposed architecture superior.

## Limitations and fairness

Single-Agent uses preload plus one fixed non-measured inference before measured
workers start. The completed Proposed Adaptive Ethernet run did not use an
equivalent dedicated warmup. Routing-quality comparisons remain usable under
the shared frozen routing contract, but directly matched LLM latency/residency
comparisons are not established. The historical routing-policy translation was
also finalized retrospectively for Proposed Adaptive, as disclosed in the policy.

`processing_seconds` measures controller work, including model/retry processing;
it is not source-event end-to-end latency. Mode B does not guarantee the common
replay boundary needed for directly comparable E2E timing. No latency figures or
cross-system latency ranking are inferred here.

This is one formal run, with no statistical-significance or general superiority
claim. Stochastic model behavior, reviewer decisions, differing architectural
state and the Mode B upstream population must remain explicit. AUTO handling is
controlled simulated execution, not demonstrated infrastructure recovery or MTTR.

## Evidence and reproducibility

Complete evidence remains local on the physical nodes, not embedded in this
README. Resolve these repository-relative paths on the node that owns them:

| Evidence location | Contents / ownership |
|---|---|
| `experiment_runs/single-agent-ethernet-full-20261004-035637/` | Node-local protocol, revision, transport, monitoring, reconciliation and archive records |
| `evaluation/baselines/results/single_agent/ethernet/single-agent-ethernet-full-20261004-035637/controller/` | Node 2 run.json, warmup.json, journal.sqlite3 and native JSONL exports |
| Run root `offline_eval_inputs/analysis/` | Shared evaluator summary, integrity, verification and input/output manifest; analysis node |
| `single-agent-final-result.txt` | Formal closeout result summary; retain its node-local provenance |
| Run root `artifact-sha256.txt` | Node-local artifact inventory and hashes |

The local audit used gateway `metrics/*-final.prom`, `seg/labels_routing.csv`,
`protocol-freeze.txt`, `protocol-events.log`, `transport/revision-pre-replay.json`,
`hitl-final-counts-stopped.txt` and pre-replay/pre-shutdown process snapshots.
Raw streams, protected configuration, journals and databases remain local.
No screenshots were added.

For future runs, retain the reviewed Python environment and follow the full
runbook rather than launching from this results summary. Existing offline tests
remain available through `python -B -m unittest discover -s
evaluation/baselines/single_agent/tests -v`; tests do not establish a formal
experiment result. Preserve historical documents and earlier evidence unchanged.
