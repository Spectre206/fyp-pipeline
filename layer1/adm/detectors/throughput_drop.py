"""
Throughput Drop / Silent Crash Detector — Moving Average Deviation (Model 3)

This module detects throughput drop and silent crash events by comparing a
short-term moving average (5 events) against a long-term moving average
(20 events). A drop is flagged when the short MA falls below 40% of the long
MA, indicating a sustained throughput reduction rather than a momentary dip.

A silent crash is detected separately when silence_duration_s (time since last
non-zero throughput reading, maintained by the Feature Store) exceeds 30 seconds.
Silent crashes are given severity CRITICAL regardless of the moving average
calculation, since zero throughput for 30+ seconds on a production consumer
always represents a critical failure requiring immediate investigation.
"""
