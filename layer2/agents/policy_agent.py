"""
Policy Agent — Tiered Routing (Pure Python, No LLM)

This module applies the deterministic four-rule routing table to every Strategy
Agent output. It consumes from strategy.result, reads the current confidence
threshold from config/threshold_config.json (reloaded on each decision so
Learning Agent updates take effect immediately), and evaluates rules in priority
order:

  P1: timed_out or parse_error → HITL (TIMEOUT / PARSE_ERROR)
  P2: risk_tier == HIGH        → HITL (HIGH_RISK)
  P3: confidence < threshold   → HITL (LOW_CONFIDENCE)
  P4: otherwise                → AUTO (LOW_RISK_HIGH_CONFIDENCE)

The full reasoning chain (triage result + strategy result) is attached to the
routed message so the downstream HITL dashboard or auto-executor has complete
context. The routing decision and reason code are also published as Prometheus
counters. Target latency: ≤ 500ms. Hard timeout: 2 seconds.
"""
