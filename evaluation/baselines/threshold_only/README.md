# Threshold-only baseline

The Threshold-only baseline is a **deterministic fixed-rule controller** for
Distributed Multi-Agent Coordination for Self-Healing Data Pipelines. It provides
a non-LLM comparison condition: the detector and execution layers remain shared,
while fixed rules replace the proposed multi-agent control plane.

The completed formal Ethernet Mode B run is
`threshold-ethernet-full-20261003-084252`, execution commit
`c1cdbd70e66e8a70b68d22c2eec539e70515cfdb`, status
`COMPLETED_UNINTERRUPTED`. See the [permanent result record](results/ETHERNET_RESULTS.md)
for evidence provenance, [historical runs](HISTORICAL_RUNS.md) for the excluded
resumed attempt, and [cross-system comparison](../COMPARISON.md).

## Architecture and rules

Unchanged Layer 1 on stream-node validates SEG events, calibrates features,
runs detectors and publishes Fusion incidents; structural schema bypass also
reaches `anomaly.detected`. The Threshold controller on ai-brain-node consumes
that queue and publishes to `auto.execute` or `hitl.queue`. Shared Layer 3 on
gateway-node performs controlled simulated execution or human review and emits
`outcome.feedback`, which Threshold records for completion accounting.

There is **no LLM, model inference/retry stage, Chroma/RAG, EMA or adaptive
learning**. Feedback does not change rules. `attempt.jsonl` is not applicable;
no empty model-attempt sidecar should be created. Metrics use port 8020.

The first matching rule in [rules.py](rules.py), using the frozen action sets
and precedence in [rules.json](rules.json), determines the response:

| Input, in precedence order | Route and risk |
|---|---|
| Unidentifiable | Quarantine; no routing decision |
| Invalid identifiable input | HITL; no invented risk tier |
| Structural schema bypass | HITL, HIGH |
| Compound incident | HITL, HIGH |
| Schema drift | HITL, HIGH |
| CPU/memory, error, throughput or authentication incident; HIGH/CRITICAL severity | HITL, HIGH; family intervention action set |
| Same supported families; LOW/MEDIUM severity | AUTO, LOW; family bounded action set |
| Unsupported incident | HITL; no invented risk tier |

There is no confidence gate. These rules operate on detector incident fields;
they do not consume ground-truth labels. Architecture and implementation details
remain in [THRESHOLD_BASELINE_SYSTEM.md](THRESHOLD_BASELINE_SYSTEM.md).

## Formal Ethernet methodology

Use [ETHERNET_FULL_RUN.md](ETHERNET_FULL_RUN.md) with the
[shared Ethernet contract](../ETHERNET_SHARED_EXPERIMENT_CONTRACT.md) and
[experiment design](../BASELINE_EXPERIMENT_DESIGN.md). This README reports results;
it does not replace startup, freeze, cleanup, replay, review or archival steps.
[Run_Threshold_Baseline.md](Run_Threshold_Baseline.md) is the older procedure;
its legacy analysis definitions are not the final Ethernet scoring contract.

Mode B reuses the frozen 1,950-event source, IDs, order, configuration and labels,
verified against the approved manifest, on the same three Ethernet nodes at
replay speed 1. Start with cold Layer 1 and isolated controller/gateway state;
keep competing controllers and Learning inactive. Preserve controller exports
and all node-local protocol evidence after complete review and drain.

[Routing-label-policy-v2](../../../layer2/evaluation/ROUTING_LABEL_POLICY.md)
derives expected routes and autonomous eligibility only from original corpus
ground-truth fields. NORMAL is excluded from anomaly routing metrics. LOW plus
`AUTO_RESTART_CONSUMER` denotes expected AUTO; HIGH plus `ESCALATE_TO_HITL`
denotes expected HITL. This benchmark eligibility is not operational safety
certification. Use `evaluation.baselines.shared.evaluate` as documented in the
runbook, without `--attempts`; the older common analyzer has superseded FAR/FER
definitions for this comparison.

Any application-worker restart after replay begins invalidates a formal run.
Preserve it, record its status and begin a new cold run with a new RUN_ID.
Evaluator cleanliness does not prove uninterrupted execution.

## Final Layer 1 and controller results

| Stage | Count |
|---|---:|
| Source events | 1,950 |
| Structurally valid events | 1,850 |
| Structural schema bypass incidents | 100 |
| Cold-start/calibration withheld | 323 |
| Detector-evaluated events, per detector | 1,527 |
| Fusion-published incidents | 539 |
| Controller incidents: Fusion + structural bypass | 539 + 100 = 639 |

Of 639 controller decisions, 630 were anomalies and nine were NORMAL. Total
routes were **168 AUTO / 471 HITL**, with 639 delivery and 639 feedback records,
zero failure records and zero quarantine records. The nine NORMAL decisions
were AUTO and are excluded from the following anomaly cross-tab.

| Ground truth | Actual AUTO | Actual HITL | Observed anomaly decisions |
|---|---:|---:|---:|
| Expected AUTO | 109 | 131 | 240 |
| Expected HITL | 50 | 340 | 390 |
| Total | 159 | 471 | 630 |

## Final metrics and human review

| Metric | Numerator / denominator | Result |
|---|---:|---:|
| False autonomy rate (FAR) | 50 / 159 | 31.4465408805% |
| Routing FER | 131 / 240 | 54.5833333333% |
| Expected-AUTO controller coverage | 240 / 380 | 63.1578947368% |
| Expected-AUTO missing before routing | 140 / 380 | 36.8421052632% |
| Risk accuracy | 449 / 630 | 71.2698412698% |
| Feedback completion | 639 / 639 | 100% |

HITL finished with **469 APPROVED, 1 REJECTED, 1 MODIFIED and 0 PENDING**.
The reported final gates were SEG exit 0, drained queues, zero DLQ, 16 required
Prometheus targets UP, 1 Gbit/s full-duplex links, synchronized clocks, no worker
restart, `no_detected_record_errors`, and evaluator FAR/FER/coverage agreement.

Gateway metrics, labels, SQLite and protocol/transport records were inspected
locally. Threshold cross-tab, risk accuracy and final evaluator integrity are
operator-reported from preserved Node 1/2 evidence; those evaluator files were
not locally inspected. The [result record](results/ETHERNET_RESULTS.md) specifies
the scope of corroboration. Missing gateway copies do not mean missing evidence.

## Interpretation and limitations

Routing FER measures escalation among expected-AUTO incidents that reached a
valid controller decision: 131/240. Expected-AUTO controller coverage is
240/380; the 140 missing before routing are a separate upstream coverage result.
Neither 639/1,950 nor 100% feedback completion establishes full detector coverage.
FAR measures benchmark-ineligible autonomy among labeled anomaly AUTO decisions;
it does not measure actual service damage or restoration.

Threshold controller processing time is not end-to-end latency. Mode B source
timestamps do not establish fresh controller-boundary arrival times, and no
cross-system latency ranking is made here. AUTO actions remain controlled
simulated execution.

This is one completed run per populated condition, without repeated-run
uncertainty estimates or a causal attribution claim. Human review and adaptive
state differ between controllers. The routing translation was finalized
retrospectively for the completed Proposed Adaptive run, before baseline
scoring; no prospective blinding is claimed for Proposed. Mode B full-pipeline
results do not replace Mode A's identical-incident controller comparison.

## Tests and evidence storage

```bash
python -B -m unittest discover -s evaluation/baselines/shared/tests -v
python -B -m unittest discover -s evaluation/baselines/threshold_only/tests -v
```

The ignored `evaluation/baselines/results/` tree holds local controller evidence;
`experiment_runs/` contains node-local run evidence. The small tracked
[results document](results/ETHERNET_RESULTS.md) under this baseline is curated
separately. Raw JSONL streams, journals, SQLite backups and protected configuration
remain local; they are not copied into the published documentation.
