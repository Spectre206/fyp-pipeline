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
