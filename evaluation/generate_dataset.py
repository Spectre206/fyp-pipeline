"""
Dataset Generator — 1,950-Event Evaluation Corpus

This script is a thin wrapper around the Synthetic Event Generator (SEG) that
produces the complete evaluation corpus in a single command. It configures the
SEG in corpus generation mode with seed=42, runs it for all 1,950 events across
the six categories specified in seg_config.json, and writes two output files:

  - evaluation/data/events.jsonl: the event stream with ground truth fields
    included (these are stripped by the Pydantic Validator before entering
    the pipeline, so the pipeline never sees them during evaluation)

  - evaluation/labels.csv: ground truth labels keyed by event_id, containing
    ground_truth_label, ground_truth_risk_tier, and ground_truth_action

The script prints a summary of the generated distribution so the operator can
confirm the counts match the specification before starting an evaluation run.
Re-running with the same seed always produces the identical corpus.
"""
