"""
Auth Failure Flood Detector — Rate-Gate + Random Forest (Model 4)

This module uses a two-stage detection approach for authentication failure floods.
The first stage is a simple rate gate: if auth_failures_per_min (a 60-second
sliding window count maintained by the Feature Store) exceeds 20, the event is
immediately flagged without involving the ML model. This provides fast, low-latency
detection for the most obvious brute-force cases.

The second stage is a Random Forest classifier trained on the KDD99 dataset
(REJ connection records for ssh and ftp_data protocols). It uses features including
src_bytes, dst_bytes, serror_rate, and rerror_rate to classify more subtle
authentication anomalies that the rate gate may miss. The trained model is saved
to adm/models/random_forest_auth.pkl with n_estimators=50, max_depth=10,
and random_state=42.
"""
