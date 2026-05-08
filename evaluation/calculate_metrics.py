"""
Metrics Calculator — MTTA, MTTR, FER, FAR, RTA, SVR

This script computes all six primary research metrics by joining two sources:

  1. Pipeline decisions: read from the SQLite decision log produced by Layer 3
     during the evaluation run. Contains routing decisions, timestamps, and
     the Strategy Agent's risk_tier and confidence for every event.

  2. Ground truth labels: read from evaluation/labels.csv, containing the
     correct label (ANOMALY/NORMAL), correct risk_tier, and correct action
     for every event_id.

Metrics computed:
  - MTTA: median and mean time from anomaly_detected timestamp to routing
    decision timestamp, in seconds
  - MTTR: median and mean time from anomaly_detected to remediation_complete
  - FER: fraction of LOW ground-truth risk events routed to HITL
  - FAR: fraction of HIGH ground-truth risk events auto-executed (safety metric)
  - RTA: fraction of strategy_agent risk_tier outputs matching ground truth
  - SVR: fraction of strategy_agent responses that passed schema validation

Outputs a summary JSON and a per-event CSV to evaluation/results/.
"""
