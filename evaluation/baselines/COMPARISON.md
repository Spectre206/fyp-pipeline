# Final three-condition Ethernet comparison

## Experiment scope and evidence

The completed formal Ethernet comparison contains exactly **Proposed Adaptive,
Threshold-only and Single-Agent**. Each condition completed one formal Mode B full-pipeline run
on the same three laptops and Ethernet topology, using the frozen 1,950-event
source, configuration, event IDs/order, routing-label-policy-v2 and replay speed
1, with comparable applicable cold state. Mode B includes Layer 1 calibration,
detection/Fusion and structural bypass; it is distinct from the primary Mode A
identical-incident controller study in the [experiment design](BASELINE_EXPERIMENT_DESIGN.md).

| Condition | Completed run | Execution revision |
|---|---|---|
| Proposed Adaptive | `ethernet_cold_20261002_023108` | `c595459ce64a479a2bf725df2fbffb7142d6f66b` |
| Threshold-only | `threshold-ethernet-full-20261003-084252` | `c1cdbd70e66e8a70b68d22c2eec539e70515cfdb` |
| Single-Agent | `single-agent-ethernet-full-20261004-035637` | `c09160c506686234d65041cbb83ea63a0ecd575c` |

Both baseline closeouts record `COMPLETED_UNINTERRUPTED`. The earlier Threshold
run `threshold-ethernet-full-20261003-053739` remains
`RESUMED_INVALID_FOR_FORMAL_COMPARISON`, excluded even if its later downstream
exports were clean; see [historical runs](threshold_only/HISTORICAL_RUNS.md).

These are the completed formal closeout results, not a new analysis of raw data.
Preserved node-local controller/evaluator, lifecycle and reconciliation evidence
was verified during closeout. This gateway-based documentation integration does
not independently reopen every native Node 1/2 artifact or rerun any evaluator.
Evidence paths and inspection scope are retained in the detailed condition
records: [Proposed Ethernet results](../../README.md#final-ethernet-experiment-results),
[Threshold result](threshold_only/results/ETHERNET_RESULTS.md), and
[Single-Agent result](single_agent/README.md#final-formal-ethernet-result).
Raw artifacts remain under each node's `experiment_runs/<run_id>/`; baseline
controller exports also use `evaluation/baselines/results/<controller>/ethernet/<run_id>/controller/`.
Proposed uses its native agent/stage analysis; baselines use the shared evaluator.

## Architecture differences

| Condition | Decision-making and state |
|---|---|
| Proposed Adaptive | Deterministic Triage with retrieval, LLM Strategy proposals, deterministic Policy authorization, and Learning with Chroma memory/EMA adaptation |
| Threshold-only | Deterministic fixed-rule controller; no LLM, model attempts, RAG or adaptive learning; feedback accounting only |
| Single-Agent | One local qwen3:1.7b controller proposes actions, confidence, risk and route; generic schema validation retains valid model routes; no Policy override, RAG or EMA; feedback accounting only |

All use unchanged Layer 1 and shared Layer 3 controlled/simulated AUTO execution
and human approve/reject/modify handling. Single-Agent may retry JSON/schema
failure once and otherwise fall back to HITL; all 639 initial outputs in this
formal run were structured-valid and no validation retry was required.

## Final results

| Measure | Proposed Adaptive | Threshold-only | Single-Agent |
|---|---:|---:|---:|
| Controller decisions | 639 | 639 | 639 |
| Anomaly decisions | 630 | 630 | 630 |
| NORMAL decisions | 9 | 9 | 9 |
| Actual AUTO | 175 | 168 | 1 |
| Actual HITL | 464 | 471 | 638 |
| Expected-AUTO corpus incidents | 380 | 380 | 380 |
| Expected-AUTO with valid decision | 240 | 240 | 240 |
| Expected-AUTO missing before routing | 140 | 140 | 140 |
| Expected AUTO → AUTO | 136 | 109 | 1 |
| Expected AUTO → HITL | 104 | 131 | 239 |
| Expected HITL → AUTO | 38 | 50 | 0 |
| Expected HITL → HITL | 352 | 340 | 390 |
| FAR | 38/174 = 21.8390804598% | 50/159 = 31.4465408805% | 0/1 = 0% |
| Routing FER | 104/240 = 43.3333333333% | 131/240 = 54.5833333333% | 239/240 = 99.5833333333% |
| Expected-AUTO controller coverage | 240/380 = 63.1578947368% | 240/380 = 63.1578947368% | 240/380 = 63.1578947368% |
| Expected-AUTO missing before routing (rate) | 140/380 = 36.8421052632% | 140/380 = 36.8421052632% | 140/380 = 36.8421052632% |
| Risk accuracy | 513/630 = 81.4285714286% | 449/630 = 71.2698412698% | 443/630 = 70.3174603175% |
| Feedback completion | 639/639 = 100% | 639/639 = 100% | 639/639 = 100% |

Fractions are authoritative; displayed percentages are rounded. Actual route
totals include NORMAL. Anomaly cross-tabs contain 630 decisions; the nine NORMAL
decisions per condition are excluded from anomaly FAR/FER.

## Metric denominators

The [shared contract](ETHERNET_SHARED_EXPERIMENT_CONTRACT.md) and
[routing policy](../../layer2/evaluation/ROUTING_LABEL_POLICY.md) freeze:

- **FAR:** actual AUTO with `safe_to_auto=false` / actual AUTO having an
  authoritative nonblank `safe_to_auto` label.
- **Routing FER:** expected-AUTO incidents routed HITL / expected-AUTO incidents
  having a valid AUTO/HITL controller decision.
- **Expected-AUTO controller coverage:** expected-AUTO incidents with a valid
  controller decision / all 380 expected-AUTO corpus incidents.
- **Missing before routing:** expected-AUTO incidents without a scoreable
  controller decision / all 380 expected-AUTO corpus incidents.

Proposed has one NORMAL AUTO decision: 175 − 1 = 174 eligible-label AUTO cases,
of which 38 are labeled false. Threshold has nine NORMAL AUTO decisions:
168 − 9 = 159, of which 50 are labeled false. Single-Agent's one AUTO decision
has an authoritative true label, giving 0/1. Benchmark `safe_to_auto` means
benchmark autonomous eligibility, not real-world safety certification.

All three FER denominators are 240. The 140 missing-before-routing cases are
an upstream coverage property and must not dilute FER by using 380 instead.
Coverage equality alone does not prove per-ID equivalence or detector accuracy;
source-to-incident causes require Layer 1 reconciliation. On imperfect records,
invalid/conflicting routes must also be reported as integrity issues, not silently
classified as physical upstream loss. Risk accuracy compares reported risk with
independent ground truth on scoreable anomalies. Feedback completion covers
observed decisions, not all source events.

## Results and discussion

All three conditions completed 639 decisions and corresponding feedback, with
identical aggregate Expected-AUTO coverage. Proposed Adaptive's observed FAR and
routing FER were lower than Threshold-only's in these runs. This is descriptive
comparative evidence; it does not isolate architectural causation or establish
universal superiority.

Single-Agent was technically reliable at structured output yet extremely
conservative: 638/639 routes were HITL and 239/240 scoreable expected-AUTO cases
were escalated. Its 0% FAR rests on one AUTO decision and is not evidence that it
is the best or safest controller. Structured validity is distinct from routing
quality and action suitability.

HITL workload was 464 cases for Proposed Adaptive, 471 for Threshold-only and
638 for Single-Agent. Threshold closeout recorded 469 approvals, one rejection,
one modification and zero pending; Single-Agent recorded 636 approvals, one
rejection, one modification and zero pending. Review outcomes reflect human
choices and are not independent correctness labels. Complete feedback does not
measure restoration success or erase interruption history.

## Limitations and reproducibility

There is one completed formal run per condition, so repeated-run uncertainty
and statistical significance are not established. Synthetic workload, fixed
condition order, stochastic model outputs, reviewer differences, adaptive state
and the small physical deployment limit generalization. Mode B is not a
substitute for Mode A's identical-incident comparison.

Single-Agent preloads the model and performs one fixed non-measured inference;
the completed Proposed Adaptive run had no equivalent dedicated warmup. Shared
routing-quality comparisons remain usable, but directly matched LLM latency/
residency comparisons are not established. Controller `processing_seconds` is
not source-event E2E latency, and Mode B does not guarantee a common replay
boundary. No latency ranking or MTTR claim follows.

The routing translation was finalized retrospectively for Proposed Adaptive,
before baseline scoring; no prospective blinding is claimed for that run.
Retain protocol differences and source/config/label provenance rather than
retrofitting earlier evidence. AUTO is simulated, not verified service recovery.
Use each condition's [Threshold](threshold_only/ETHERNET_FULL_RUN.md),
[Single-Agent](single_agent/ETHERNET_FULL_RUN.md) or
[Proposed formal runbook](../../Ethernet_Full_Rerun.md) for reproduction.
A [separate demo guide](../../docs/ETHERNET_DEMO_RUNBOOK.md) is for demonstration
only and produces no formal experimental evidence.
