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
  - auth_failures_per_min: AVERAGE rate over a 60-second sliding window
    (v1.1: changed from sum-of-rates to average-of-rates -- see fix #4 below)
  - z_score: (x - rolling_mean) / rolling_std

All functions are stateless — they receive only the window data they need.
The Feature Store is responsible for maintaining state between calls.

v1.3 CHANGELOG:
  - FIX #1: compute() now actually truncates the incoming window to the last
    `window_size` entries before computing any rolling statistic.
  - FIX #4: `_auth_rate()` now returns the AVERAGE of auth_failures_per_min
    readings within the 60s window, not their SUM.
  - PSI was removed from the active vector. It was neither a decision signal
    nor a reliable diagnostic for the small, mixed synthetic windows, while it
    added work and could produce undefined bin proportions out of range.
"""
# layer1/feature_store/feature_computers.py
#
# Computes all 10 feature types from a rolling window of metric dicts.
# Called by FeatureStore.process() on every validated event.
# All features returned as a single flat dict with descriptive keys.

import logging
from typing import Dict, List, Optional

import numpy as np
from dateutil import parser as dtparser

log = logging.getLogger(__name__)


class FeatureComputer:
    """
    Stateless feature computation engine.
    Takes a window (list of dicts with 'metrics' and 'timestamp' keys)
    and an optional baseline dict, returns a flat feature_vector dict.
    """

    def compute(
        self,
        window: List[dict],
        baseline: Optional[Dict[str, List[float]]],
        window_size: int = 30,
    ) -> dict:
        """
        Main entry point. Called once per validated event.

        Args:
            window:      List of dicts: [{"metrics": {...}, "timestamp": "ISO8601"}, ...]
                         Ordered oldest -> newest. Last item is the current event.
            baseline:    Frozen calibration baseline (None during calibration period).
            window_size: Rolling window length. ALL rolling statistics are computed
                         only over the last `window_size` entries of `window`.

        Returns:
            Flat dict of feature_name -> float value.
        """
        if not window:
            return {}

        if window_size and len(window) > window_size:
            window = window[-window_size:]

        features = {}

        # ── Collect all metric keys present in the window ─────────────
        all_keys: set = set()
        for entry in window:
            if isinstance(entry.get("metrics"), dict):
                all_keys.update(entry["metrics"].keys())

        # ── Per-metric features ───────────────────────────────────────
        for metric in all_keys:
            values = [
                float(entry["metrics"].get(metric, 0.0))
                for entry in window
                if isinstance(entry.get("metrics"), dict)
            ]
            if not values:
                continue

            arr = np.array(values, dtype=float)

            # Rolling statistics
            features[f"rolling_mean_{metric}"] = float(np.mean(arr))
            features[f"rolling_std_{metric}"]  = float(np.std(arr))
            features[f"rolling_min_{metric}"]  = float(np.min(arr))
            features[f"rolling_max_{metric}"]  = float(np.max(arr))

            # Z-score of the latest value vs rolling window
            std = float(np.std(arr))
            if std > 1e-9:
                features[f"z_score_{metric}"] = float(
                    (arr[-1] - np.mean(arr)) / std
                )
            else:
                features[f"z_score_{metric}"] = 0.0

            # Rate of change: current - previous value
            if len(arr) >= 2:
                features[f"rate_of_change_{metric}"] = float(arr[-1] - arr[-2])
            else:
                features[f"rate_of_change_{metric}"] = 0.0

            # Spike count: events in window exceeding mean + 2 sigma
            threshold = float(np.mean(arr)) + 2.0 * float(np.std(arr))
            features[f"spike_count_{metric}"] = int(np.sum(arr > threshold))

            # Short MA (last 5 events) and long MA (last 20 events)
            features[f"short_ma_{metric}"] = float(np.mean(arr[-5:]))
            features[f"long_ma_{metric}"]  = float(np.mean(arr[-20:]))

        # ── Global features ─────────────────────────────────────────

        features["silence_duration_s"] = self._silence_duration(window)
        features["auth_failures_per_min"] = self._auth_rate(window)

        return features

    # ── Silence duration ──────────────────────────────────────────────

    def _silence_duration(self, window: List[dict]) -> float:
        """
        Uses event timestamps to find the last non-zero throughput reading.
        This represents stream-time silence and is deterministic in replay.

        Returns 0.0  if current throughput is non-zero.
        Returns 9999.0 if no non-zero throughput seen in entire window.
        """
        if not window:
            return 0.0
        current_mps = window[-1].get("metrics", {}).get("messages_per_second")
        if current_mps is not None and float(current_mps) > 0:
            return 0.0
        try:
            current_time = dtparser.parse(window[-1]["timestamp"])
        except Exception:
            return 0.0

        for entry in reversed(window[:-1]):
            mps = entry.get("metrics", {}).get("messages_per_second")
            if mps is not None and float(mps) > 0:
                try:
                    last_active = dtparser.parse(entry["timestamp"])
                    return max(0.0, (current_time - last_active).total_seconds())
                except Exception:
                    return 0.0

        return 9999.0

    # ── Auth failure rate ─────────────────────────────────────────────

    def _auth_rate(self, window: List[dict]) -> float:
        """
        Returns the AVERAGE of auth_failures_per_min readings from events
        within the last 60 seconds of the window. Used by Model 4.

        Returns 0.0 if no auth_failures_per_min metric present in-window.
        """
        from datetime import timedelta

        if not window:
            return 0.0

        try:
            now    = dtparser.parse(window[-1]["timestamp"])
            cutoff = now - timedelta(seconds=60)
            total  = 0.0
            count  = 0

            for entry in window:
                ts = dtparser.parse(entry["timestamp"])
                if ts >= cutoff:
                    val = entry.get("metrics", {}).get("auth_failures_per_min")
                    if val is not None:
                        total += float(val)
                        count += 1

            if count == 0:
                return 0.0

            return round(total / count, 4)

        except Exception as exc:
            log.debug(f"auth_rate computation error: {exc}")
            return 0.0
