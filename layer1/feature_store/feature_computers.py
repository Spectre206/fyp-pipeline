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
  - psi_score: Population Stability Index vs. the calibration baseline

All functions are stateless — they receive only the window data they need.
The Feature Store is responsible for maintaining state between calls.

v1.1 CHANGELOG (Feature Store issues review):
  - FIX #1: compute() now actually truncates the incoming window to the last
    `window_size` entries before computing any rolling statistic. Previously
    `window_size` was accepted but never used, so every statistic silently
    used the entire deque (up to 1000 events) instead of a true rolling
    window. See LAYER1_COMPONENT_LOG.md Section 4 for the demonstrated bug.
  - FIX #4: `_auth_rate()` now returns the AVERAGE of auth_failures_per_min
    readings within the 60s window, not their SUM. Summing already-a-rate
    values inflated the feature far beyond Model 4's rate_threshold=20/min
    scale (demonstrated: 6 realistic HIGH-severity events summed to 310).
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
                         May be longer than window_size (e.g. the Feature Store's
                         deque can hold up to 1000 events) -- this function is
                         responsible for restricting itself to the most recent
                         window_size entries. See FIX #1.
            baseline:    Frozen calibration baseline (None during calibration period).
                         Dict of metric_name -> list of float values.
            window_size: Rolling window length. ALL rolling statistics
                         (rolling_mean/std/min/max, z_score, rate_of_change,
                         spike_count) are computed only over the last
                         `window_size` entries of `window` -- not the full
                         list passed in.

        Returns:
            Flat dict of feature_name -> float value.
        """
        if not window:
            return {}

        # ── FIX #1: actually restrict to the last window_size entries. ────
        # Previously this parameter was accepted but never used, so every
        # statistic below silently operated on the ENTIRE deque (up to 1000
        # events) rather than a true rolling window. short_ma/long_ma below
        # take their own smaller slices of THIS already-truncated window,
        # so they remain sub-windows of the rolling window as intended.
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

            # Rolling statistics (now correctly scoped to window_size)
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

            # Short MA (last 5 events) and long MA (last 20 events) --
            # sub-windows of the already-truncated `window`, so these
            # remain correctly nested inside the rolling window_size.
            features[f"short_ma_{metric}"] = float(np.mean(arr[-5:]))
            features[f"long_ma_{metric}"]  = float(np.mean(arr[-20:]))

            # PSI score vs calibration baseline
            # Returns 0.0 during calibration period (baseline is None)
            if baseline and metric in baseline:
                features[f"psi_score_{metric}"] = self._psi(
                    arr, np.array(baseline[metric], dtype=float)
                )
            else:
                features[f"psi_score_{metric}"] = 0.0

        # ── Global features (not per-metric) ─────────────────────────

        # silence_duration_s — seconds since last non-zero throughput
        # Used by Model 3 (Throughput Drop / Silent Crash detector)
        features["silence_duration_s"] = self._silence_duration(window)

        # auth_failures_per_min — AVERAGE rate over a 60-second sliding
        # window (v1.1 fix -- was a SUM, see module docstring FIX #4)
        # Used by Model 4 (Rate-gate + Random Forest)
        features["auth_failures_per_min"] = self._auth_rate(window)

        return features

    # ── PSI (Population Stability Index) ─────────────────────────────

    def _psi(
        self,
        actual: np.ndarray,
        expected: np.ndarray,
        bins: int = 10
    ) -> float:
        """
        Computes PSI between actual (current window) and expected (baseline).

        PSI interpretation:
          < 0.1  -> no significant change
          0.1-0.2 -> moderate change
          >= 0.2  -> significant shift (MEDIUM severity)
          >= 0.5  -> severe shift    (HIGH severity)

        Returns 0.0 on any computation error.
        """
        try:
            eps       = 1e-8
            all_vals  = np.concatenate([actual, expected])
            bin_edges = np.linspace(
                all_vals.min(), all_vals.max() + eps, bins + 1
            )

            a_counts = np.histogram(actual,   bins=bin_edges)[0].astype(float) + eps
            e_counts = np.histogram(expected, bins=bin_edges)[0].astype(float) + eps

            a_pct = a_counts / a_counts.sum()
            e_pct = e_counts / e_counts.sum()

            psi = float(np.sum((a_pct - e_pct) * np.log(a_pct / e_pct)))
            return round(max(0.0, psi), 6)

        except Exception as exc:
            log.debug(f"PSI computation error: {exc}")
            return 0.0

    # ── Silence duration ──────────────────────────────────────────────

    def _silence_duration(self, window: List[dict]) -> float:
        """
        Walks the window backwards to find the last event where
        messages_per_second > 0. Returns elapsed seconds since then.

        Returns 0.0  if current throughput is non-zero.
        Returns 9999.0 if no non-zero throughput seen in entire window
                       (full silent crash throughout window).
        """
        from datetime import datetime, timezone

        for entry in reversed(window):
            mps = entry.get("metrics", {}).get("messages_per_second")
            if mps is not None and float(mps) > 0:
                try:
                    last_active = dtparser.parse(entry["timestamp"])
                    now = datetime.now(
                        last_active.tzinfo or timezone.utc
                    )
                    return max(0.0, (now - last_active).total_seconds())
                except Exception:
                    return 0.0

        # Never saw non-zero throughput in window
        return 9999.0

    # ── Auth failure rate ─────────────────────────────────────────────

    def _auth_rate(self, window: List[dict]) -> float:
        """
        Returns the AVERAGE of auth_failures_per_min readings from events
        within the last 60 seconds of the window. Used by Model 4 as a
        fast rate gate.

        v1.1 FIX #4: this was previously a SUM of readings, which inflated
        the feature far beyond Model 4's rate_threshold=20/min scale (e.g.
        6 events at 45-60/min summed to 310). Each event's
        auth_failures_per_min is already an instantaneous rate reading, so
        averaging multiple readings within the window recovers a
        comparable rate rather than compounding them.

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