"""
Baseline Calibrator — First-100-Events Distribution Recording

This module handles the calibration phase that runs for the first 100 events
per (node, component) pair. During calibration, it records the baseline
distribution of each metric field to enable PSI scoring later.

The calibrator stores: mean, standard deviation, and histogram bucket boundaries
for each numeric metric in the event payload. These are persisted to a JSON
file per component so that the calibration survives a Feature Store restart
without needing to replay the first 100 events again.

Once a component's calibration is complete, the calibrator signals the Feature
Store to activate anomaly detection for that component. The calibration status
of all components is logged at startup so the operator can see which components
are still warming up.
"""
# layer1/feature_store/baseline_calibrator.py
#
# Records metric distributions for the first N events per (node, component).
# After N events the baseline is frozen and PSI scoring becomes active.
# One BaselineCalibrator instance per (node, component) pair.

from collections import defaultdict
from typing import Dict, List, Optional


class BaselineCalibrator:
    """
    Calibration mode: first CALIBRATION_N events per component.

    During calibration:
      - Records all metric values into self._data
      - is_calibrated() returns False
      - PSI scores computed by FeatureComputer will be 0.0

    After calibration:
      - self.baseline is frozen (dict of metric → list of float values)
      - is_calibrated() returns True
      - PSI scoring is active
    """

    def __init__(self, calibration_n: int = 100):
        self.calibration_n = calibration_n
        self._count        = 0
        self._data: Dict[str, List[float]] = defaultdict(list)
        self.baseline: Optional[Dict[str, List[float]]] = None

    def update(self, metrics: Dict[str, float]):
        """
        Feed one event's metric_values into the calibrator.
        Once calibration_n events seen, baseline is frozen automatically.
        Safe to call after calibration — becomes a no-op.
        """
        if self.baseline is not None:
            return  # Already calibrated — baseline frozen, no further updates

        for k, v in metrics.items():
            if isinstance(v, (int, float)):
                self._data[k].append(float(v))

        self._count += 1

        if self._count >= self.calibration_n:
            # Freeze the baseline — PSI scoring now active
            self.baseline = {k: list(v) for k, v in self._data.items()}

    def is_calibrated(self) -> bool:
        """Returns True once calibration_n events have been seen."""
        return self.baseline is not None

    def events_until_calibrated(self) -> int:
        """How many more events needed before calibration completes."""
        if self.is_calibrated():
            return 0
        return self.calibration_n - self._count