"""
Synthetic Event Generator (SEG) — Main Entry Point

This module is the main controller for the SEG. It reads configuration from
seg_config.json (seed, replay speed, event counts per anomaly category) and
operates in one of two modes:

  1. Corpus generation mode: generates the full 1,950-event evaluation dataset,
     writes events to a JSONL file, and stores ground truth labels separately
     in labels.csv. The same seed (42) always produces the identical dataset.

  2. Live replay mode: replays a pre-generated JSONL corpus into the pipeline
     by publishing events to the Pydantic Validator input at the configured
     replay speed (1x, 5x, 10x). Timestamps are adjusted to wall-clock time
     during replay to preserve realistic inter-arrival jitter.

Ground truth fields (ground_truth_label, ground_truth_risk_tier,
ground_truth_action) are stripped from every event before it enters the
pipeline and are stored only in labels.csv, keyed by event_id.
"""
