# Ethernet Mode B cross-system comparison

This is the canonical curated comparison for the four planned Ethernet
conditions. Only completed formal runs are populated. Pending means no formal
result is documented here; it is not zero. The resumed Threshold attempt
`threshold-ethernet-full-20261003-053739` is excluded, as recorded in
[historical runs](threshold_only/HISTORICAL_RUNS.md).

## Conditions and provenance

All conditions follow the [shared Ethernet contract](ETHERNET_SHARED_EXPERIMENT_CONTRACT.md):
the same frozen 1,950-event source, event IDs/order, configuration, final routing
labels, replay speed 1 and comparable cold-state procedure. This is Mode B
full-pipeline evaluation, not the primary Mode A identical-incident study in the
[experiment design](BASELINE_EXPERIMENT_DESIGN.md).

Threshold-only is a deterministic fixed-rule controller without model inference,
RAG or adaptive learning. Proposed Adaptive retains the proposed multi-agent
architecture and adaptive EMA. Single-Agent and Proposed Fixed await formal
Ethernet runs; their eventual evidence must preserve their distinct semantics.

Threshold executed at `c1cdbd70e66e8a70b68d22c2eec539e70515cfdb`.
Its [curated result](threshold_only/results/ETHERNET_RESULTS.md) distinguishes
locally corroborated gateway counts/state from operator-reported Node 1/2
reconciliation, routing cross-tab, risk accuracy and evaluator integrity. The
Threshold evaluator outputs were not present in the local gateway copy during
this audit; no independent recomputation of those scores is claimed.

Proposed Adaptive executed at `c595459ce64a479a2bf725df2fbffb7142d6f66b`,
Ethernet deployment base `c0ad6be9c84955240cf4499d586ad46b1d579ecc`.
Its preserved `offline_eval_inputs/evaluation_summary.json` and
`routing-independent-verification.json` under its node-local run root were
inspected. The local `labels_routing.csv`/`policy.jsonl` join confirms the
cross-tab below and nine NORMAL decisions (one AUTO, eight HITL). The summary
confirms risk accuracy and feedback completion. These checked values agree with
the supplied final Proposed figures; superseded FER summaries are not used.

## Results

| Measure | Threshold-only | Single-Agent | Proposed Adaptive | Proposed Fixed |
|---|---|---|---|---|
| Formal run ID | `threshold-ethernet-full-20261003-084252` | Pending formal run | `ethernet_cold_20261002_023108` | Pending formal run |
| Formal status | COMPLETED (`COMPLETED_UNINTERRUPTED`) | Pending formal run | COMPLETED | Pending formal run |
| Controller decisions | 639 | Pending formal run | 639 | Pending formal run |
| Anomaly decisions | 630 | Pending formal run | 630 | Pending formal run |
| Normal decisions | 9 | Pending formal run | 9 | Pending formal run |
| Actual AUTO | 168 | Pending formal run | 175 | Pending formal run |
| Actual HITL | 471 | Pending formal run | 464 | Pending formal run |
| Expected-AUTO total | 380 | Pending formal run | 380 | Pending formal run |
| Expected-AUTO with decision | 240 | Pending formal run | 240 | Pending formal run |
| Expected-AUTO missing before routing (count) | 140 | Pending formal run | 140 | Pending formal run |
| Expected AUTO → AUTO | 109 | Pending formal run | 136 | Pending formal run |
| Expected AUTO → HITL | 131 | Pending formal run | 104 | Pending formal run |
| Expected HITL → AUTO | 50 | Pending formal run | 38 | Pending formal run |
| Expected HITL → HITL | 340 | Pending formal run | 352 | Pending formal run |
| FAR | 50/159 = 31.4465408805% | Pending formal run | 38/174 = 21.8390804598% | Pending formal run |
| Routing FER | 131/240 = 54.5833333333% | Pending formal run | 104/240 = 43.3333333333% | Pending formal run |
| Expected-AUTO controller coverage | 240/380 = 63.1578947368% | Pending formal run | 240/380 = 63.1578947368% | Pending formal run |
| Expected-AUTO missing before routing (rate) | 140/380 = 36.8421052632% | Pending formal run | 140/380 = 36.8421052632% | Pending formal run |
| Risk accuracy | 449/630 = 71.2698412698% | Pending formal run | 513/630 = 81.4285714286% | Pending formal run |
| Feedback completion | 639/639 = 100% | Pending formal run | 639/639 = 100% | Pending formal run |

Fractions are authoritative; percentages are rounded. Actual AUTO/HITL totals
include NORMAL; anomaly cross-tabs and FAR/FER exclude NORMAL. Threshold has
nine NORMAL AUTO decisions, so its FAR denominator is 168 − 9 = 159. Proposed
has one NORMAL AUTO decision, so its FAR denominator is 175 − 1 = 174.

## Shared interpretation

FAR is benchmark-ineligible AUTO divided by labeled anomaly AUTO decisions.
Routing FER is expected AUTO routed HITL divided by expected AUTO with a valid
routing decision. Coverage divides expected AUTO with a valid decision by all
380 expected-AUTO corpus events; missing before routing reports the remainder
separately. Risk accuracy compares reported risk with ground truth on scoreable
anomalies. Feedback completion concerns observed decisions, not all source events.
These definitions and the source-only label translation remain unchanged.

Both completed conditions have 240/380 Expected-AUTO controller coverage and
140/380 missing before routing, while routing error rates differ. Equal aggregate
coverage does not by itself prove identical per-ID receipt or detector accuracy.
The 639 incidents are downstream of Layer 1 calibration/filtering and structural
schema bypass; they must not be equated with the 1,950 source events.

The [routing policy](../../layer2/evaluation/ROUTING_LABEL_POLICY.md) was finalized
retrospectively for Proposed Adaptive after its results were available, before
baseline scoring. No prospective blinding is claimed for that run. One completed
run per populated condition, differing human review, adaptive state and model
behavior do not support statistical significance, causal attribution or a system
ranking. Controller processing time is not end-to-end latency; no latency winner
is inferred. Benchmark eligibility and simulated AUTO execution do not establish
real-world safety or service restoration.

Formal completion additionally requires protocol evidence of uninterrupted
execution. Clean evaluator records or complete feedback alone cannot detect every
upstream restart or prove a clean experiment. Raw evidence remains local on the
three nodes; this comparison neither replaces the runbooks nor embeds their raw
incident streams, databases or protected configuration.
