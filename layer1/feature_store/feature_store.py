"""
Feature Store — Stateful Rolling Window Manager

This module is the central stateful component of Layer 1. It maintains a
separate collections.deque per (node, affected_component) pair, with a
configurable maximum length (default: 30 events, max: 1,000 events).

On each incoming validated event, the Feature Store:
  1. Appends the event to the appropriate deque.
  2. Calls feature_computers.py to recompute the full feature vector for
     that component's current window.
  3. Attaches the feature vector to the event as a new "feature_vector" field.
  4. Forwards the enriched event to the ADM Runner.

During the first 100 events per component (calibration mode), the Feature Store
records the baseline distribution for PSI scoring but does not forward events to
the ADM — anomaly detection only begins after the baseline is established.
"""
