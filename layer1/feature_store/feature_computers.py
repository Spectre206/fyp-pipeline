"""
Feature Computers — Derived Feature Vector Calculation

This module contains the pure computation functions called by the Feature Store
on every event arrival. Each function takes the current window (list of recent
metric values) and returns a scalar feature.

Features computed:
  - rolling_mean, rolling_std, rolling_min, rolling_max over the window
  - rate_of_change: (current_value - previous_value) / elapsed_seconds
  - spike_count: number of events in window exceeding a per-metric threshold
  - short_ma (5-event) and long_ma (20-event) for Moving Average Deviation
  - silence_duration_s: seconds since last non-zero throughput reading
  - auth_failures_per_min: count over a 60-second sliding window
  - z_score: (x - rolling_mean) / rolling_std
  - psi_score: Population Stability Index vs. the calibration baseline

All functions are stateless — they receive only the window data they need.
The Feature Store is responsible for maintaining state between calls.
"""
