"""
Feature Store — Stateful Rolling Window Manager

This module is the central stateful component of Layer 1. It maintains a
separate collections.deque per (node, affected_component) pair, with a
configurable maximum length (default: 30 events, max: 1,000 events).

On each incoming validated event, the Feature Store:
  1. Appends the event to the appropriate deque.
  2. Calls feature_computers.py to recompute the full feature vector for
     that component's current window (restricted to the most recent
     window_size events -- see FIX #1 in feature_computers.py).
  3. Attaches the feature vector to the event as a new "feature_vector" field.
  4. Forwards the enriched event to the ADM Runner.

During the first 100 events per component (calibration mode), the Feature Store
records the baseline distribution for PSI scoring and DOES NOT forward events
to the ADM — process() returns None for these events. Anomaly detection only
begins once process() starts returning a non-None enriched event, i.e. once
that component's baseline is established.

v1.1 CHANGELOG (Feature Store issues review):
  - FIX #2: process() now actually enforces the calibration gate described
    above. Previously it always returned the enriched event regardless of
    calibration state, contradicting this module's own docstring. Callers
    (ADM Runner) MUST check for a None return value and skip fan-out to
    detection.fanout when they see one.
  - FIX #3: baseline persistence wired in. FeatureStore now attempts to
    load a previously-saved baseline for a (node, component) key before
    creating a fresh BaselineCalibrator, and saves it to disk the moment
    calibration completes. See baseline_dir constructor argument.
"""
# layer1/feature_store/feature_store.py
# Feature Store — In-process library (NOT a standalone consumer in v1.2)
# Called by adm/adm_runner.py before fanning out to detection.fanout.

import logging
import re
from collections import deque
from pathlib import Path
from typing import Dict, Optional, Tuple

from feature_computers   import FeatureComputer
from baseline_calibrator import BaselineCalibrator

log = logging.getLogger(__name__)

WINDOW_SIZE       = 30
MAX_DEQUE_SIZE    = 1000
CALIBRATION_N     = 100
DEFAULT_BASELINE_DIR = "baselines"

_SANITIZE_RE = re.compile(r"[^A-Za-z0-9_-]+")


class FeatureStore:
    """
    Stateful in-memory rolling window store.
    Called directly by ADMRunner — NOT a RabbitMQ consumer.

    ADMRunner flow:
        event = consume from validated.event
        enriched = feature_store.process(event)
        if enriched is None:
            continue   # still calibrating -- do not fan out (FIX #2)
        fan out enriched to detection.fanout (all 5 detectors)
    """

    def __init__(
        self,
        window_size: int = WINDOW_SIZE,
        calibration_n: int = CALIBRATION_N,
        baseline_dir: str = DEFAULT_BASELINE_DIR,
    ):
        self.window_size    = window_size
        self.calibration_n  = calibration_n
        self.baseline_dir   = Path(baseline_dir)
        self._windows:     Dict[Tuple[str, str], deque]              = {}
        self._calibrators: Dict[Tuple[str, str], BaselineCalibrator] = {}
        self._computers    = FeatureComputer()

    def _key(self, evt: dict) -> Tuple[str, str]:
        return (evt.get("affected_component", "unknown"),)   # tuple with one element

    def _get_window(self, key: Tuple) -> deque:
        if key not in self._windows:
            self._windows[key] = deque(maxlen=MAX_DEQUE_SIZE)
        return self._windows[key]

    def _baseline_path(self, key: Tuple[str, ...]) -> Path:
    # key is now (component,) after calibration key coarsening
        component = key[0]
        safe_component = _SANITIZE_RE.sub("_", component)
        return self.baseline_dir / f"{safe_component}.json"

    def _get_calibrator(self, key: Tuple) -> BaselineCalibrator:
        if key not in self._calibrators:
            path = self._baseline_path(key)
            if path.exists():
                try:
                    self._calibrators[key] = BaselineCalibrator.load(
                        path, calibration_n=self.calibration_n
                    )
                    log.info(f"Restored baseline for {key} from {path}")
                except Exception as exc:
                    log.error(f"Failed to load baseline from {path}: {exc} "
                              f"-- starting fresh calibration for {key}")
                    self._calibrators[key] = BaselineCalibrator(self.calibration_n)
            else:
                self._calibrators[key] = BaselineCalibrator(self.calibration_n)
        return self._calibrators[key]

    def process(self, evt: dict) -> Optional[dict]:
        """
        Called by ADMRunner for every validated event.

        Returns the same event dict with feature_vector appended, UNLESS
        this component is still in its calibration window -- in that case
        returns None (FIX #2). ADMRunner must handle this by skipping
        fan-out for that event rather than treating None as an error.
        """
        key        = self._key(evt)
        window     = self._get_window(key)
        calibrator = self._get_calibrator(key)
        metrics    = evt.get("metric_values", {})

        was_calibrated = calibrator.is_calibrated()

        # Update calibrator
        if isinstance(metrics, dict):
            calibrator.update(metrics)

        # FIX #3: the instant calibration completes, persist it so a
        # restart doesn't lose this component's baseline.
        if not was_calibrated and calibrator.is_calibrated():
            path = self._baseline_path(key)
            try:
                calibrator.save(path)
                log.info(f"Calibration complete for {key} -- saved to {path}")
            except Exception as exc:
                log.error(f"Failed to save baseline to {path}: {exc}")

        # Push to rolling window
        window.append({
            "metrics":   metrics if isinstance(metrics, dict) else {},
            "timestamp": evt.get("timestamp", ""),
        })

        # FIX #2: enforce the calibration gate. Still-warming-up components
        # get their window/calibrator updated (above) so calibration
        # progresses, but no enriched event is returned for detection.
        if not calibrator.is_calibrated():
            log.debug(f"{key} still calibrating "
                      f"({calibrator.events_until_calibrated()} events left) "
                      f"-- withholding from ADM fan-out")
            return None

        # Compute features (restricted to the most recent window_size
        # entries -- see FIX #1 in feature_computers.py)
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
        enriched["calibrated"]              = True
        enriched["calibration_events_left"] = 0
        enriched["window_depth"]            = len(window)
        return enriched