# Evaluation — Historical Planning Archive

**Project:** Distributed Multi-Agent Coordination for Self-Healing Data Pipelines: A Human-in-the-Loop Approach on Commodity Hardware

> **Historical plan, not an implemented evaluation guide.** The scripts listed
> below (`generate_dataset.py`, `run_baseline.py`, `calculate_metrics.py`, and
> `kappa.py`) are not present in this directory. Their descriptions, old metric
> targets, and reproduction steps record planned work, not completed experiments.
> Threshold-only and Single-Agent comparisons remain planned; FAR/FER are not
> computable for the final run, and no verified service-recovery time was measured.
> Current evaluation uses SEG corpus generation and
> [the Layer 2 offline analyzer](../layer2/evaluation/analyze_run.py). See
> [Full_Rerun.md](../Full_Rerun.md), [Layer 2](../layer2/README.md), and the
> [methodology](../docs/System_Design_and_Methodology.md).

The original planning outline is retained below. The referenced v1.1 document
is an older external planning artifact, not a current repository dependency.

---

## Evaluation Flow

```
1. generate_dataset.py   — generates events.jsonl + labels.csv via the SEG
2. Run the full pipeline against events.jsonl (replay mode)
3. Run baseline against events.jsonl (run_baseline.py)
4. calculate_metrics.py  — compares pipeline decisions to ground truth labels
5. kappa.py              — calculates Cohen's Kappa for risk tier agreement
```

---

## Files

| File | Purpose |
|:-----|:--------|
| `generate_dataset.py` | Wrapper around the SEG that produces the 1,950-event corpus with ground truth labels. Uses seed=42 for reproducibility. |
| `run_baseline.py` | Runs the static threshold-only baseline system against the generated corpus. Produces baseline MTTA/MTTR/FER/FAR for comparison. |
| `calculate_metrics.py` | Computes MTTA, MTTR, FER, FAR, RTA, and SVR by comparing pipeline decisions (from SQLite decision log) against ground truth labels (from labels.csv). |
| `kappa.py` | Calculates Cohen's Kappa between Strategy Agent risk_tier outputs and ground truth risk tier labels. |
| `results/` | Output directory for metric CSVs and summary JSON files. Git-ignored (generated at runtime). |

---

## Reproducing the Evaluation

All scripts are deterministic given the same seed and the same pipeline outputs.
To reproduce the Phase 5 evaluation results from the paper:
1. Ensure seed=42 is set in `layer1/seg/config/seg_config.json`
2. Run `python generate_dataset.py` to regenerate the corpus
3. Run the full pipeline in replay mode against the corpus
4. Run `python calculate_metrics.py` with the path to the SQLite decision log

---

## Metric Definitions

See `docs/System_Design_Methodology_v1.1.docx` Section 7.4 for full definitions
of MTTA, MTTR, FER, FAR, RTA, SVR, and Cohen's Kappa.
