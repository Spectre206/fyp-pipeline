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
                         Ordered oldest → newest. Last item is the current event.
            baseline:    Frozen calibration baseline (None during calibration period).
                         Dict of metric_name → list of float values.
            window_size: Default rolling window size (used for long_ma fallback).

        Returns:
            Flat dict of feature_name → float value.
        """
        if not window:
            return {}

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

            # Rate of change: current − previous value
            if len(arr) >= 2:
                features[f"rate_of_change_{metric}"] = float(arr[-1] - arr[-2])
            else:
                features[f"rate_of_change_{metric}"] = 0.0

            # Spike count: events in window exceeding mean + 2σ
            threshold = float(np.mean(arr)) + 2.0 * float(np.std(arr))
            features[f"spike_count_{metric}"] = int(np.sum(arr > threshold))

            # Short MA (last 5 events) and long MA (last 20 events)
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

        # auth_failures_per_min — sliding 60-second window sum
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
          < 0.1  → no significant change
          0.1–0.2 → moderate change
          >= 0.2  → significant shift (MEDIUM severity)
          >= 0.5  → severe shift    (HIGH severity)

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
        Sums auth_failures_per_min values from events within the last
        60 seconds of the window. Used by Model 4 as a fast rate gate.

        Returns 0.0 if no auth_failures_per_min metric present.
        """
        from datetime import timedelta

        if not window:
            return 0.0

        try:
            now    = dtparser.parse(window[-1]["timestamp"])
            cutoff = now - timedelta(seconds=60)
            total  = 0.0

            for entry in window:
                ts = dtparser.parse(entry["timestamp"])
                if ts >= cutoff:
                    val = entry.get("metrics", {}).get(
                        "auth_failures_per_min", 0.0
                    )
                    total += float(val)

            return round(total, 4)

        except Exception as exc:
            log.debug(f"auth_rate computation error: {exc}")
            return 0.0