"""
Baseline System Runner — Static Threshold Comparator

This script runs the static threshold-only baseline system against the generated
evaluation corpus. The baseline applies the five hard-threshold rules specified
in System Design Section 7.3 — no LLM, no agents, no ChromaDB.

For each event in events.jsonl, the baseline checks the relevant threshold rule
(cpu_percent > 85%, error_rate > 10%, throughput < 5% of baseline, auth_failures
> 20/min, Pydantic validation failure) and records whether it would have detected
the anomaly. All detected anomalies are assigned a simulated fixed MTTR of 60
seconds (no automated action — manual intervention assumed). Normal events are
passed through without detection.

Outputs a baseline_results.csv in evaluation/results/ with the same schema as
the pipeline results CSV so calculate_metrics.py can compare them directly.
"""
