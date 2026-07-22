# feature_store.py — v1.2.1 (split window/calibration keys)

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
CALIBRATION_N     = 20          # final settled value
DEFAULT_BASELINE_DIR = "baselines"

_SANITIZE_RE = re.compile(r"[^A-Za-z0-9_-]+")


class FeatureStore:
    """
    Stateful in-memory rolling window store.
    Called directly by ADMRunner.

    ADMRunner flow:
        event = consume from validated.event
        enriched = feature_store.process(event)
        if enriched is None:   # still calibrating
            continue
        fan out enriched to detection.fanout
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
        self._calibrators: Dict[Tuple[str],     BaselineCalibrator]  = {}
        self._computers    = FeatureComputer()

    # ── Two separate keys ─────────────────────────────────────────────
    def _window_key(self, evt: dict) -> Tuple[str, str]:
        """Rolling window is per (node, component) – no cross-node mixing."""
        return (evt.get("node", "unknown"),
                evt.get("affected_component", "unknown"))

    def _calibration_key(self, evt: dict) -> Tuple[str]:
        """Calibrator is per component only – pools nodes to speed up baseline."""
        return (evt.get("affected_component", "unknown"),)

    # ── Window management (uses _window_key) ─────────────────────────
    def _get_window(self, key: Tuple[str, str]) -> deque:
        if key not in self._windows:
            self._windows[key] = deque(maxlen=MAX_DEQUE_SIZE)
        return self._windows[key]

    # ── Calibrator management (uses _calibration_key) ────────────────
    def _baseline_path(self, key: Tuple[str]) -> Path:
        """Builds a safe filename from a calibration key (component,)."""
        component = key[0]
        safe_component = _SANITIZE_RE.sub("_", component)
        return self.baseline_dir / f"{safe_component}.json"

    def _get_calibrator(self, key: Tuple[str]) -> BaselineCalibrator:
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

    # ── Main processing method ────────────────────────────────────────
    def process(self, evt: dict) -> Optional[dict]:
        """
        Called by ADMRunner for every validated event.

        Returns the same event dict with feature_vector appended, UNLESS
        this component is still in its calibration window -- in that case
        returns None.
        """
        # Separate keys
        window_key      = self._window_key(evt)
        calibration_key = self._calibration_key(evt)

        window     = self._get_window(window_key)
        calibrator = self._get_calibrator(calibration_key)
        metrics    = evt.get("metric_values", {})

        was_calibrated = calibrator.is_calibrated()

        # Update calibrator (per-component)
        if isinstance(metrics, dict):
            calibrator.update(metrics)

        # On calibration completion: persist baseline
        if not was_calibrated and calibrator.is_calibrated():
            path = self._baseline_path(calibration_key)
            try:
                calibrator.save(path)
                log.info(f"Calibration complete for {calibration_key} -- saved to {path}")
            except Exception as exc:
                log.error(f"Failed to save baseline to {path}: {exc}")

        # Push to rolling window (per node-component)
        window.append({
            "metrics":   metrics if isinstance(metrics, dict) else {},
            "timestamp": evt.get("timestamp", ""),
        })

        # Enforce calibration gate
        if not calibrator.is_calibrated():
            log.debug(f"{calibration_key} still calibrating "
                      f"({calibrator.events_until_calibrated()} events left) "
                      f"-- withholding from ADM fan-out")
            return None

        # Compute features (rolling window is per node-component)
        try:
            features = self._computers.compute(
                list(window), calibrator.baseline, self.window_size
            )
        except Exception as exc:
            log.error(f"Feature computation error: {exc}")
            features = {}

        enriched = dict(evt)
        enriched["feature_vector"]          = features
        enriched["calibrated"]              = True
        enriched["calibration_events_left"] = 0
        enriched["window_depth"]            = len(window)
        return enriched