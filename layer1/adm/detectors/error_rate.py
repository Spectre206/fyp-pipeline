"""
Error Rate Surge Detector — Statistical Z-Score (Model 2)

This module detects escalating 5xx error rate surges using a rolling Z-score
calculation. The detector reads z_score_error_rate from the feature vector
(computed by feature_computers.py as (current_rate - rolling_mean) / rolling_std
over a 30-event window) and flags an anomaly when |Z| > 3.0.

A secondary threshold rule triggers immediately if error_rate_percent > 10%
over any rolling 30-second window, regardless of the Z-score, to catch sudden
step-change surges that the statistical model may lag on during the initial
window fill. The detector does not require a pre-trained model file — it
operates entirely from the rolling window statistics maintained by the Feature
Store.
"""
