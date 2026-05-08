"""
Event Templates — Per-Category Payload Definitions

This module defines the template structure for each of the six event categories
produced by the SEG:

  - NORMAL: healthy baseline traffic across all components and nodes
  - cpu_memory_spike: sustained high CPU or memory utilisation events
  - error_rate_surge: escalating 5xx error windows on ingestion endpoints
  - throughput_drop: near-zero message throughput or silent consumer crash events
  - auth_failure_flood: high-frequency failed authentication bursts
  - schema_drift: three sub-types — missing required fields, type mutations
    (int → str), and value distribution shifts (PSI drift)

Each template specifies the metric_values structure, realistic value ranges per
severity level, and the affected_component pool for that category. The SEG
instantiates these templates with sampled values during corpus generation.
"""
