# Threshold-only Ethernet Mode B — final result

## Run identity and evidence provenance

| Field | Value |
|---|---|
| Run ID | `threshold-ethernet-full-20261003-084252` |
| Branch | `experiment/threshold-baseline` |
| Execution commit | `c1cdbd70e66e8a70b68d22c2eec539e70515cfdb` |
| Formal status | `COMPLETED_UNINTERRUPTED` |
| Condition | Threshold-only, Ethernet, Mode B full pipeline |
| Replay speed | 1 |

Formal closeout verified the preserved node-local Node 1/2 reconciliation,
controller exports and evaluator results, including the cross-tab, risk score,
failure/quarantine counts and evaluator agreement. Those native artifacts are
not available in the local gateway copy for this documentation audit. This
gateway-only edit did not rerun or regenerate results, or independently reopen
all Node 1/2-native artifacts; it retains the completed formal closeout evidence.

Locally inspected gateway evidence corroborates the 1,950/1,850/100 Validator
counts, 539 Fusion publications, 639 controller deliveries/decisions, 168 AUTO,
471 HITL and 639 feedback. The final SQLite backup corroborates HITL outcomes;
the routing CSV contains 1,950 labels (1,000 NORMAL, 380 expected AUTO and 570
expected HITL). The gateway protocol log records `COMPLETED_UNINTERRUPTED` at the
execution revision. Its target snapshot shows all 16 required Threshold targets
UP; its link and clock records confirm gateway 1000 Mb/s full duplex and clock
synchronization. These local checks agree with the completed formal closeout
evidence. They do not independently prove uninterrupted execution on the other two nodes.

Raw evidence remains node-local under `experiment_runs/<run_id>/` and the
controller result directory specified by the [runbook](../ETHERNET_FULL_RUN.md).
This is a curated result record, not a replacement for those artifacts.

## Corpus and Layer 1 reconciliation

The frozen source contains 1,950 events: 1,000 NORMAL and 950 anomalies, of which
380 are expected AUTO and 570 expected HITL under
[routing-label-policy-v2](../../../../layer2/evaluation/ROUTING_LABEL_POLICY.md).

| Stage | Count |
|---|---:|
| Source events | 1,950 |
| Structurally valid events | 1,850 |
| Structural schema bypass incidents | 100 |
| Cold-start/calibration withheld | 323 |
| Detector-evaluated events, per detector | 1,527 |
| Fusion-published incidents | 539 |
| Controller incidents: Fusion + structural bypass | 539 + 100 = 639 |

The 1,950 source events are not 1,950 controller incidents. Calibration withholds
323 structurally valid events; Fusion filters the detector population. Structural
schema bypass incidents reach the controller without that detector/Fusion path.

## Controller and routing

| Record/population | Count |
|---|---:|
| Decision records | 639 |
| Anomaly decisions | 630 |
| NORMAL decisions | 9 |
| Actual AUTO, including NORMAL | 168 |
| Actual HITL, including NORMAL | 471 |
| Delivery records | 639 |
| Feedback records | 639 |
| Failure records | 0 |
| Quarantine records | 0 |

| Ground truth | Actual AUTO | Actual HITL | Observed anomaly decisions |
|---|---:|---:|---:|
| Expected AUTO | 109 | 131 | 240 |
| Expected HITL | 50 | 340 | 390 |
| Total | 159 | 471 | 630 |

All nine NORMAL decisions were AUTO; they are excluded from anomaly FAR/FER.
FAR is actual AUTO decisions on incidents labeled `safe_to_auto=false` divided
by actual AUTO decisions having an authoritative nonblank `safe_to_auto` label.
Of 168 total AUTO decisions, excluding the nine NORMAL AUTO decisions leaves
an authoritative anomaly AUTO denominator of 159. The unsafe/ineligible AUTO
numerator is 50, giving FAR = 50/159.

## Final metrics

| Metric | Numerator / denominator | Result |
|---|---:|---:|
| False autonomy rate (FAR) | 50 / 159 | 31.4465408805% |
| Routing FER | 131 / 240 | 54.5833333333% |
| Expected-AUTO controller coverage | 240 / 380 | 63.1578947368% |
| Expected-AUTO missing before routing | 140 / 380 | 36.8421052632% |
| Risk accuracy | 449 / 630 | 71.2698412698% |
| Feedback completion | 639 / 639 | 100% |

Fractions are authoritative; displayed percentages are rounded. Routing FER is
expected-AUTO incidents routed HITL divided by expected-AUTO incidents with a
valid AUTO/HITL controller decision: 131/240. Its denominator is the 240 such
incidents, not all 380 corpus-eligible anomalies. The remaining 140 are missing
before routing and are reported separately. Feedback completion covers the 639 observed decisions, not all source
events. Definitions follow the [shared contract](../../ETHERNET_SHARED_EXPERIMENT_CONTRACT.md).

## HITL and run integrity

| HITL outcome | Count |
|---|---:|
| APPROVED | 469 |
| REJECTED | 1 |
| MODIFIED | 1 |
| PENDING | 0 |

The completed formal closeout evidence records SEG exit 0; all experiment queues
at zero ready and zero unacknowledged; `dead.letters` zero; all three nodes at 1000 Mb/s full
duplex with synchronized clocks; and no application-worker restart after replay
began. It records evaluator `integrity_status=no_detected_record_errors` and
FAR/FER/coverage agreement `true`. Gateway checks are scoped above. Final snapshots
and clean controller exports alone cannot establish an uninterrupted run.

This run is included in the [formal comparison](../../COMPARISON.md) on the
verified formal closeout protocol evidence. The earlier resumed execution is
excluded and retained in [historical runs](../HISTORICAL_RUNS.md).
