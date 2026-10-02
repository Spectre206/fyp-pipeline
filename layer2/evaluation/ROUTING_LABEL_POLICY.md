# Routing ground truth — routing-label-policy-v2

## Background and audit evidence

The original corpus assigned risk and action categories but deliberately left
`expected_route` and `safe_to_auto` blank. In
`layer1/seg/event_templates.py`, `RISK_TIER_MAP`, `GROUND_TRUTH_ACTIONS` and
`EventTemplateFactory` deterministically assign LOW anomalies to
`AUTO_RESTART_CONSUMER`, HIGH anomalies to `ESCALATE_TO_HITL`, and NORMAL to no
action. `layer1/seg/seg.py` separates these annotations from runtime events via
`_strip_ground_truth` and writes the offline CSV in `save_corpus`.
The mapping exists in the initial SEG commit `0a9e1b2` (2026-05-24), and in both
experiment revisions (`377250945c253b9c9da233d84391d1458d181fc9` Wi-Fi and
`c595459ce64a479a2bf725df2fbffb7142d6f66b` Ethernet).
Later evaluation tests deliberately treated blank routing labels as unavailable;
the legacy categories were not an existing formal operational safety contract.

The first retrospective policy, v1, compared corpus actions against runtime
Strategy identifiers from a different vocabulary (see
`layer2/agents/schema_validator.py`). That mismatch labeled all 950 anomalies
HITL and produced FAR 174/174 and non-computable FER 0/0.
`AUTO_RESTART_CONSUMER` is not an alias of `RESTART_FAILED_CONSUMER`.
V2 supersedes that membership rule by an explicit offline benchmark translation,
based on original workload intent rather than comparative outcome optimization.

## Final frozen policy

Adopted on 2026-10-02 for Threshold-Only, Single-Agent, Proposed adaptive EMA,
and Proposed fixed EMA/history-only learning, all over Ethernet.

| Source annotation | expected_route | safe_to_auto |
|---|---|---|
| NORMAL | blank | blank |
| ANOMALY + LOW + AUTO_RESTART_CONSUMER | AUTO | true |
| ANOMALY + HIGH + ESCALATE_TO_HITL | HITL | false |

`safe_to_auto=true` means **benchmark autonomous eligibility**, not formal
real-world operational safety certification. NORMAL is excluded from routing
evaluation. Any other anomaly combination or unknown label is a hard annotation
failure, never a fallback route. No runtime action membership is consulted.

The generator reads only original CSV ground-truth fields, never Strategy,
Policy, confidence, EMA or evaluation outputs. It validates required/unique
headers, nonempty unique IDs, row shape and source values, rejects nonblank
existing routing annotations, and validates all rows before creating output.
Original fields, extra columns, row order and IDs are preserved. Existing blank
routing columns are populated in the separate output without duplicate headers;
absent columns are appended. Output is deterministic and exclusively created.
Counts below are measured from the corpus, not hardcoded in the generator.

## Timing and comparative freeze

The source risk/action mapping predates all runs. This explicit translation was
finalized retrospectively for the already completed adaptive-EMA Ethernet run,
after its results were available; no prospective blinding is claimed. V2 is
frozen before Threshold-Only, Single-Agent and fixed-EMA/history-only experiments.
Use the same source labels, derived labels, annotation script, NORMAL exclusion,
metric formulas and benchmark semantics unchanged for all four conditions.
Do not modify the policy based on comparative results. Any later amendment must
be versioned and disclosed, not silently substituted into this comparison.
No runtime implementation is changed by the annotation policy.

## FAR and FER

Join by `event_id`, excluding NORMAL and missing routing labels.

- **False Autonomy Rate (FAR)** = number of actual AUTO decisions with
  `safe_to_auto=false` / number of actual AUTO decisions with an authoritative
  nonblank `safe_to_auto` label (true or false).
- **False Escalation Rate (FER)** = number of actual HITL decisions with
  `expected_route=AUTO` / number of expected-AUTO incidents with an actual
  AUTO/HITL Policy routing decision.
- **Expected-AUTO Policy Coverage** = expected AUTO with a Policy decision /
  all authoritative expected-AUTO corpus incidents.
- **Expected-AUTO Missing Before Policy** = expected AUTO without a Policy
  record / all authoritative expected-AUTO corpus incidents.

Lower FAR/FER and missing-before-Policy rates are better; higher coverage is
better. Missing Policy decisions are not
successful routing and not counted as escalations; they are upstream coverage
attrition and excluded from the FER denominator. FER is not computable when no
eligible incident has a Policy decision; coverage is not computable only when
there are no expected-AUTO corpus labels. Invalid/missing route values on an
existing Policy record are excluded from routing decisions and reported as
`expected_auto_invalid_policy`, separately from absent records.
Zero denominator means `not_computable` and null, never zero error. Blank safety
is not false. Existing JSON keys such as `false_automation_rate` and
`auto_eligible_decisions` remain for compatibility, with explicit numerator and
denominator. The historical unsafe-population FAR definition in the baseline
design is superseded for these four Ethernet conditions.

The metric correction on 2026-10-02 supersedes the initial v2 corpus-denominator
FER (104/380 = 27.37%). Review identified dilution by 140 missing Policy cases;
final routing FER is 104/240 = 43.33%. The v2 label translation and FAR are
unchanged. These routing FER and coverage semantics are frozen for all four
Ethernet systems before remaining comparisons. Previous summaries, verification
and analyzer/policy snapshots are retained in `routing-v2-corpus-fer-superseded/`.
No AHMR is introduced.

## Authoritative artifacts and results

Repository-relative root:
`experiment_runs/ethernet_cold_20261002_023108/offline_eval_inputs/`.

| File | SHA-256 |
|---|---|
| Original labels.csv | `da596042f35e2983b83414a7bbed84925fde2b734a7ea96255fa24454de8d936` |
| Final labels_routing.csv | `f57a7cf80f72c60a915286fa40ea93064cb9053e9e2272bffc765131ecee129c` |

All 1,950 IDs are unique. Original fields/order/IDs are unchanged; six source
columns remain six. The source and five stage JSONLs are hash-verified unchanged.

| Original category | Rows | Final routing |
|---|---:|---|
| NORMAL / N/A / blank | 1,000 | excluded |
| ANOMALY / LOW / AUTO_RESTART_CONSUMER | 380 | AUTO / true |
| ANOMALY / HIGH / ESCALATE_TO_HITL | 570 | HITL / false |

| Completed proposed adaptive-EMA Ethernet metric | Result |
|---|---:|
| Policy incidents | 639 |
| Joined expected AUTO / HITL / excluded NORMAL | 240 / 390 / 9 |
| Actual AUTO / HITL, before exclusions | 175 / 464 |
| Excluded NORMAL actual AUTO / HITL | 1 / 8 |
| FAR | 38 / 174 = 21.84% |
| FER | 104 / 240 = 43.33% |
| Expected-AUTO Policy Coverage | 240 / 380 = 63.16% |
| Expected-AUTO Missing Before Policy | 140 / 380 = 36.84% |
| Risk accuracy | 513 / 630 = 81.43% |
| SVR | 639 / 639 = 100% |
| Invalid JSON / schema-invalid / timeouts | 0 / 0 / 0 |
| Feedback overall / AUTO / HITL | 639/639; 175/175; 464/464 |

All reported missing-stage, missing-feedback, unknown-feedback, pending-HITL,
missing-Learning, malformed and duplicate checks are zero. Stage completeness
is measured within the 639 observed incidents; it does not mean all corpus
records reach Policy. Of 240 eligible incidents with Policy decisions, 136
routed AUTO and 104 routed HITL. The 140 eligible corpus records without Policy
are upstream coverage attrition and do not dilute routing FER. Non-routing metrics remain unchanged (floating-point comparisons use
1e-12 tolerance). No baseline or fixed-EMA results are claimed.

`evaluation_summary.json` and `per_event.csv` are final v2 outputs.
`routing-label-report.json` includes distributions by label, risk, action,
expected route and eligibility. `routing-independent-verification.py` and its
JSON result preserve the separate ID-join check, which agrees exactly with the
analyzer. `routing-evaluation-manifest.json` records input/output and tool hashes.
`routing-policy-v1-superseded/` preserves v1 labels, reports, results and code/
policy snapshots; its CSV hash is
`ba86ba9996e3167f9d3e4be980439a1ee15eb0b1bbf4915746f5e5f392918901`.
`evaluation_summary.before-routing.json` remains a reconstruction using the
then-HEAD analyzer with original blank labels, not an original historical Node 2
summary. No historical summary was overwritten without archival.

## Reproduction and branch reuse

```bash
python3 -m layer2.evaluation.generate_routing_labels \
  --input /path/to/labels.csv --output /path/to/labels_routing.csv
sha256sum /path/to/labels.csv /path/to/labels_routing.csv
python3 -m layer2.evaluation.analyze_run \
  --run-dir /path/to/completed/stage-jsonl-directory \
  --ground-truth /path/to/labels_routing.csv --expect-hitl-feedback
```

Archive existing analyzer outputs before running. The feedback flag is for
exhaustive review. Reuse the exact final derived CSV and verify both hashes for
this corpus. Carry the generator, analyzer semantics, tests and shared policy
unchanged into upcoming branches. Controller-specific analyzers must use these
same denominators without inventing Proposed-system stages. Record revisions
and hashes; review other experimental freeze requirements separately. This
routing freeze alone does not resolve repetition, human-review, warmup or
other protocol limitations, nor replace the primary identical-incident study.

## Reusable methodology paragraph

The synthetic workload generator assigned LOW-risk anomalies to an autonomous
handling category (`AUTO_RESTART_CONSUMER`) and HIGH-risk anomalies to a human
escalation category (`ESCALATE_TO_HITL`). Because these legacy labels differ from
the runtime remediation vocabulary, an offline benchmark annotation policy
translated them into `expected_route` and `safe_to_auto`: LOW/autonomous cases
were AUTO/eligible, HIGH/escalation cases HITL/not eligible, and NORMAL excluded.
This translation used only pre-existing corpus annotations, independently of
system outputs. Eligibility denotes benchmark autonomous eligibility, not
operational safety certification. The translation was finalized retrospectively
for the completed adaptive-EMA run and frozen before the remaining comparative
runs; prospective blinding is not claimed for the completed run.
