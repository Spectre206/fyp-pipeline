"""
Schema Drift Detector — PSI Detector (Model 5)

This module is the statistical drift stage of schema drift detection. It handles
value distribution drift — cases where the event payload is structurally valid
(passes Pydantic validation) but the numeric values have shifted significantly
from the calibration baseline, suggesting a change in upstream data generation
behaviour.

The detector computes the Population Stability Index (PSI) for each numeric field
in the event using the baseline distribution recorded by baseline_calibrator.py
during the first 100 events per component. PSI > 0.2 triggers a MEDIUM severity
anomaly; PSI > 0.5 triggers HIGH severity. Structural violations (missing fields,
type mutations) are handled upstream by the Pydantic Validator and schema_drift_router
before events ever reach this detector.
"""
