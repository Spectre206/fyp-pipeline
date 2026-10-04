# Wi-Fi vs Ethernet Full-System Comparison

## 1. Purpose

This comparison examines network medium for the **proposed heterogeneous
multi-agent system only**, keeping its architecture, physical three-node setup,
workload, replay speed and cold-state procedure as close as the available
evidence permits. Threshold-Only and Single-Agent results are not included;
those controller comparisons are planned separately.

Evidence provenance: Wi-Fi figures are transcribed from the historical
[README results](../README.md#final-wi-fi-experiment-results) and
[System Design and Methodology](System_Design_and_Methodology.md). Ethernet
operational counters, gateway state, revision gate, gateway link/socket evidence,
Prometheus targets and all seven screenshots were inspected locally. Ethernet
Node 1/2 protocol, corpus, offline latency/integrity, risk accuracy, completion
and Chroma results are attributed to the operator-supplied summary of preserved
node-local evidence; those files were not independently inspected on gateway.
No missing gateway copy is interpreted as missing experiment evidence.

The common node-local run root is
`~/fyp-pipeline/experiment_runs/ethernet_cold_20261002_023108/`:

| Node | Preserved evidence and inspection scope |
|---|---|
| stream-node | Operator-reported `metadata.txt`, `protocol-freeze.txt`, `reconciliation.txt`, `completion_utc.txt`, `corpus.sha256`, `frozen-source.txt`, `frozen-manifest.sha256`, `seg/`, `layer1_runtime/`, `transport/queues-after.txt`, `transport/rabbitmq-peers-after.txt` and revision records |
| ai-brain-node | Operator-reported `threshold-final.json`, `.diff`, `.sha256`, `chroma-final.txt`, `seg/labels.csv`, and `layer2_evaluation/ethernet_cold_20261002_023108/evaluation_summary.json` with per-event/stage records |
| gateway-node | Locally inspected `layer3-final-state.txt`, `metrics/`, `transport/revision-before.txt`, `revision-after.txt`, `link.txt`, `rabbitmq-sockets-before.txt`, and `prometheus-targets-after.json`; final SQLite backup is present |

## 2. Compared runs

| Condition | Run ID | Network medium | Implementation commit | Corpus | Replay speed | Cold-state status | Completion status |
|---|---|---|---|---|---:|---|---|
| Proposed Wi-Fi | `wifi_cold_20260913_041045` | Wi-Fi | `377250945c253b9c9da233d84391d1458d181fc9` | Authoritative 1,950-event SEG corpus | 1 | Recorded cold calibration, Chroma, EMA, queues and HITL state | 639 feedback; 0 pending |
| Proposed Ethernet | `ethernet_cold_20261002_023108` | Ethernet | `c595459ce64a479a2bf725df2fbffb7142d6f66b` | Same preserved Wi-Fi files, IDs and order (operator-reported) | 1 | Same cold reset reported | 639 feedback; 0 pending; reported completion `2026-10-02T06:45:49Z` |

Ethernet deployment base: `c0ad6be9c84955240cf4499d586ad46b1d579ecc`.
The gateway revision record reports `REVISION_GATE=PASS`, a clean working tree,
and no changes outside `Ethernet_Full_Rerun.md` relative to that base. Thus
application/deployment implementation outside the runbook was gated against
the frozen Ethernet base. This is not a claim that the two experiment commits
are identical, nor a separate audit of all changes since the Wi-Fi commit.

## 3. Comparability and limitations

The operator reports reuse of the exact preserved authoritative Wi-Fi corpus,
final labels and SEG configuration: same event IDs, line order, file hashes and
replay speed 1. The reported source hashes are:

| File | SHA-256 |
|---|---|
| `events_1950.jsonl` | `427d64f93caf78d2ae58ae916e74e034ce3e17681f3580d04972263faa7594a3` |
| `labels.csv` | `da596042f35e2983b83414a7bbed84925fde2b734a7ea96255fa24454de8d936` |
| `seg_config.json` | `36910a5208a09724010f3e5d1fae359227c2f37daa47a3de0eb6626731446418` |

Both runs use the same physical three-node architecture, the qwen3:1.7b Strategy
model family and a cold-state reset, with learning/EMA evolving during each run.
Model family alone does not certify identical stochastic generation or runtime
model state. There is one matched pair: Wi-Fi happened first, Ethernet second;
condition order was not randomized and no repeated-run uncertainty estimate is
available. The historical Wi-Fi run had no explicit dedicated warmup protocol;
Ethernet intentionally did not add an Ethernet-only dedicated warmup.

As reported in Node 1's `protocol-freeze.txt`, the corpus manifest was created
retrospectively from preserved authoritative Wi-Fi files before Ethernet replay.
It supports reported file matching at that point, not a historically
pre-existing independently approved freeze. This departure from the prospective
runbook requirement is disclosed rather than treated as fully satisfied.
Human outcomes and feedback timing also differed, potentially affecting adaptive
state. These limitations preclude attributing observed differences solely to
network medium. FAR and FER remain not computable in either run.

## 4. Cross-layer comparison

| Measure | Wi-Fi | Ethernet |
|---|---:|---:|
| Input events | 1,950 | 1,950 |
| Validator valid | 1,850 | 1,850 |
| Structural violations | 100 | 100 |
| Fusion eligible | 1,527 | 1,527 |
| Fusion published | 539 | 539 |
| Structural bypass | 100 | 100 |
| Layer 2 incidents | 639 | 639 |
| AUTO | 170 | 175 |
| HITL | 469 | 464 |
| Feedback | 639 | 639 |
| Final Chroma documents | 639 | 639 |

The recorded total incident population is stable: 539 fused plus 100 structural
bypass incidents. Matching totals are distinct from per-ID integrity checks;
Ethernet's supplied analyzer summary reports zero missing, duplicate, malformed
or unknown-feedback records across the reported checks.

## 5. Layer 1 comparison

| Measure | Wi-Fi | Ethernet |
|---|---:|---:|
| Evaluations per detector | 1,527 | 1,527 |
| CPU / error / auth / schema / throughput detections | 197 / 150 / 124 / 31 / 141 | 197 / 150 / 124 / 31 / 141 |
| Fusion published / suppressed | 539 / 988 | 539 / 988 |
| Compound | 43 | 43 |
| Fast Path | 83 | 83 |
| Late recovery | 0 | 0 |

Layer 1 operational counts were identical in these recorded runs. This does not
prove universal network independence or establish detector true-positive rates.

## 6. Layer 2 comparison

| Measure | Wi-Fi | Ethernet |
|---|---:|---:|
| Strategy responses | 639 | 639 |
| Valid / invalid JSON | 639 / 0 | 639 / 0 |
| SVR (non-timeout denominator) | 493/639 = 77.15% | 639/639 = 100% |
| Schema-valid / schema-invalid | 493 / 146 | 639 / 0 |
| Timeouts | 0 | 0 |
| AUTO / HITL | 170 / 469 | 175 / 464 |
| HIGH_RISK | 258 | 399 |
| LOW_CONFIDENCE | 65 | 65 |
| LOW_RISK_HIGH_CONFIDENCE | 170 | 175 |
| SCHEMA_INVALID | 146 | 0 |
| Risk-tier accuracy | 513/630 = 81.43% | 513/630 = 81.43% |
| Final EMA threshold | 0.7291 | 0.7681 |
| EMA updates | 639 | 639 |
| FAR / FER | Not computable | Not computable |

The observed SVR difference is approximately **+22.85 percentage points**; it
must not be described as caused by Ethernet. The model is stochastic and the
runs were neither repeated nor randomized. Schema validity measures contract
compliance, not action quality; equal risk accuracy does not imply equal routing.
Five more incidents entered AUTO in Ethernet, but adaptive feedback and realized
model/reviewer behaviour prevent a network-only explanation.

## 7. Latency comparison

The offline Layer 2 analyzer is authoritative for aggregate latency. Ethernet
values below are supplied from its node-local summary; Wi-Fi values retain the
precision published in README. Grafana's Ethernet E2E panel visually clipped
around 30 minutes and cannot replace the offline p95 of 7866.067336 seconds
(approximately 131.10 minutes).

The observed relative difference is `100 × (Ethernet − Wi-Fi) / Wi-Fi`.
Positive means a higher duration on Ethernet; negative means a lower duration.
Percentages are approximate, especially where Wi-Fi was published only in
rounded minutes. They are descriptive differences, not effect estimates from
repeated trials.

| Measure | Statistic | Wi-Fi | Ethernet | Observed relative difference |
|---|---|---:|---:|---:|
| Strategy | Mean | 13.0546 s | 16.00097 s | +22.57% |
| Strategy | Median | 11.142 s | 15.855 s | +42.30% |
| Strategy | p95 | 19.409 s | 17.828 s | -8.15% |
| Strategy | Maximum | 22.084 s | 27.633 s | +25.13% |
| Control-plane | Mean | 13.0606 s | 16.07202 s | +23.06% |
| Control-plane | Median | 11.17 s | 15.924 s | +42.56% |
| Control-plane | p95 | 19.41 s | 17.873 s | -7.92% |
| Control-plane | Maximum | 22.085 s | 28.171 s | +27.56% |
| E2E decision | Mean | 68.4 min | 66.14 min | -3.30% |
| E2E decision | Median | 68.5 min | 65.24 min | -4.77% |
| E2E decision | p95 | 131.7 min | 131.10 min | -0.45% |
| E2E decision | Maximum | 139.2 min | 138.46 min | -0.53% |
| Feedback completion | Mean | 37.611 s | 31.92572 s | -15.12% |
| Feedback completion | Median | 23.107 s | 24.64676 s | +6.66% |
| Feedback completion | p95 | 126.545 s | 90.89649 s | -28.17% |
| Feedback completion | Maximum | 367.597 s | 162.57428 s | -55.77% |
| Learning processing | Mean | 58.97 ms | 54.86 ms | -6.97% |
| Learning processing | Median | 46.09 ms | 36.48 ms | -20.85% |
| Learning processing | p95 | 77.73 ms | 76.30 ms | -1.84% |
| Learning processing | Maximum | Not reported | 5832.44 ms | Not computable |

Strategy mean was higher on Ethernet, while Strategy p95 was lower. E2E p95
remained very similar. Feedback mean and p95 were lower, but human decisions and
feedback timing differ between conditions. The serial CPU-only Strategy stage
remained the dominant processing bottleneck and source of overall queueing.
The large Ethernet Learning maximum is retained rather than hidden; no matching
Wi-Fi maximum is published here, so no percentage is calculated for it. These
mixed observations do not justify an overall “Ethernet is faster” conclusion.

## 8. Layer 3 and feedback comparison

| Measure | Wi-Fi | Ethernet |
|---|---:|---:|
| AUTO attempts / outcomes / feedback | 170 / 170 / 170 | 175 / 175 / 175 |
| HITL total | 469 | 464 |
| Approved | 325 | 463 |
| Rejected | 143 | 0 |
| Modified | 1 | 1 |
| Total feedback | 639 | 639 |
| Pending at completion | 0 | 0 |

Human decision distributions are strongly affected by reviewer choices. The
operator reports that Wi-Fi intentionally included many rejections; Ethernet
had a different realized reviewer outcome distribution. These are not
network-medium effects or evidence that Ethernet changed human decision quality.
They also limit comparisons of feedback latency and adaptive EMA state. AUTO
remains controlled simulated execution, not verified service restoration; no
MTTR claim follows from these timings.

## 9. Infrastructure observations

The [Ethernet screenshots](../README.md#final-ethernet-observability-screenshots)
and preserved gateway target list show **19 UP / 2 DOWN**. The two DOWN targets
are intentionally inactive Threshold-Only and Single-Agent exporters; all
required proposed-system remote scrape destinations use `10.10.10.x` with
hostname-based logical labels. They are not proposed-system failures.

The reported Ethernet links negotiated at **1 Gbit/s, full duplex**; gateway's
preserved `link.txt` locally corroborates `1000Mb/s`, `Full`, and link detected.
Gateway's socket record shows `.13 → 10.10.10.11:5672`. Node 1's operator-reported
broker-peer evidence also identifies remote peers `10.10.10.12` and
`10.10.10.13`; Node 1 same-host RabbitMQ connections remained local. The latter
peer record is not copied onto gateway and was not independently checked here.

The final queue screenshot shows zero ready/unacknowledged messages in all
listed experiment queues, including DLQ; the infrastructure screenshot also
shows DLQ zero. These observations and the reported reconciliation support zero
recorded DLQ, not continuous proof from a final snapshot. Backlogs accumulated
and drained. Hardware panels and the processing profile are consistent with
CPU-only Strategy remaining the dominant processing bottleneck; neither link
speed nor aggregate network throughput directly explains the observed latency
differences.

## 10. Interpretation

Layer 1 operational counts and the total incident population were stable across
these recorded matched runs. End-to-end p95 remained nearly unchanged; some
downstream timing measures were lower while Strategy mean was higher. The
CPU-only local LLM remained the dominant processing bottleneck. A single matched
pair with fixed order, stochastic model outputs and different reviewer outcomes
does not establish that Ethernet universally improves or does not improve this
system. Repeated, balanced Wi-Fi/Ethernet runs with frozen review, warmup and
runtime settings would be needed for stronger causal inference. No overall
winner is assigned.

## 11. Completed Ethernet controller comparison

The final formal Ethernet Mode B comparison now contains exactly Proposed
Adaptive, Threshold-only and Single-Agent. See the
[authoritative comparison](../evaluation/baselines/COMPARISON.md) for completed
results. The earlier plan to combine Wi-Fi and controller conditions in one
future comparison is superseded; this document retains the historical
Proposed-only transport comparison and its original numerical results.

Architecture comparisons and network-medium observations must remain distinct.
Mode B results do not replace the primary Mode A identical-incident study in the
[Baseline Experiment Design](../evaluation/baselines/BASELINE_EXPERIMENT_DESIGN.md).
