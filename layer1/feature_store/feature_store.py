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
# layer1/feature_store/feature_store.py
# Feature Store — In-process library (NOT a standalone consumer in v1.2)
# Called by adm/adm_runner.py before fanning out to detection.fanout.

import logging
from collections import deque
from typing import Dict, Tuple

from feature_computers   import FeatureComputer
from baseline_calibrator import BaselineCalibrator

log = logging.getLogger(__name__)

WINDOW_SIZE    = 30
MAX_DEQUE_SIZE = 1000
CALIBRATION_N  = 100


class FeatureStore:
    """
    Stateful in-memory rolling window store.
    Called directly by ADMRunner — NOT a RabbitMQ consumer.

    ADMRunner flow:
        event = consume from validated.event
        enriched = feature_store.process(event)
        fan out enriched to detection.fanout (all 5 detectors)
    """

    def __init__(self, window_size: int = WINDOW_SIZE):
        self.window_size   = window_size
        self._windows:     Dict[Tuple[str, str], deque]              = {}
        self._calibrators: Dict[Tuple[str, str], BaselineCalibrator] = {}
        self._computers    = FeatureComputer()

    def _key(self, evt: dict) -> Tuple[str, str]:
        return (evt.get("node", "unknown"),
                evt.get("affected_component", "unknown"))

    def _get_window(self, key: Tuple) -> deque:
        if key not in self._windows:
            self._windows[key] = deque(maxlen=MAX_DEQUE_SIZE)
        return self._windows[key]

    def _get_calibrator(self, key: Tuple) -> BaselineCalibrator:
        if key not in self._calibrators:
            self._calibrators[key] = BaselineCalibrator(CALIBRATION_N)
        return self._calibrators[key]

    def process(self, evt: dict) -> dict:
        """
        Called by ADMRunner for every validated event.
        Returns the same event dict with feature_vector appended.
        """
        key        = self._key(evt)
        window     = self._get_window(key)
        calibrator = self._get_calibrator(key)
        metrics    = evt.get("metric_values", {})

        # Update calibrator
        if isinstance(metrics, dict):
            calibrator.update(metrics)

        # Push to rolling window
        window.append({
            "metrics":   metrics if isinstance(metrics, dict) else {},
            "timestamp": evt.get("timestamp", ""),
        })

        # Compute features
        try:
            features = self._computers.compute(
                list(window), calibrator.baseline, self.window_size
            )
        except Exception as exc:
            log.error(f"Feature computation error: {exc}")
            features = {}

        # Return enriched event
        enriched = dict(evt)
        enriched["feature_vector"]          = features
        enriched["calibrated"]              = calibrator.is_calibrated()
        enriched["calibration_events_left"] = calibrator.events_until_calibrated()
        enriched["window_depth"]            = len(window)
        return enriched