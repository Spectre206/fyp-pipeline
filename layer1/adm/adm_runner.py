"""
ADM Runner — Anomaly Detection Module Orchestrator

This module is the top-level orchestrator for all five anomaly detectors. It
consumes enriched events from the Feature Store, fans each event out to the
appropriate detector(s) based on anomaly type and component metadata, and
collects detection results.

When any detector flags an anomaly, the runner attaches the detection metadata
(detector name, model confidence, threshold value, feature values that triggered
the detection) to the event and forwards it to the RabbitMQ producer for
publishing to anomaly.detected.

Normal events (no detector triggered) are silently discarded — they are not
published to RabbitMQ. The ADM runner also maintains per-detector counters for
Prometheus metrics (total events processed, anomalies detected, false positive
estimates based on known-normal events).
"""
