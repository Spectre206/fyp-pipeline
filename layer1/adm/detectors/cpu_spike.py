"""
CPU / Memory Spike Detector — Isolation Forest (Model 1)

This module implements anomaly detection for CPU and memory spike events using
scikit-learn's IsolationForest. The model is trained on the NAB
cpu_utilization_asg_misconfiguration and machine_temperature_system_failure
datasets and saved to adm/models/isolation_forest_cpu.pkl.

At inference time, the detector receives a feature vector from the Feature Store
containing rolling_mean_cpu, rolling_std_cpu, rate_of_change_cpu, and
spike_count_cpu. It applies the pre-trained model and also evaluates a
hard-threshold rule (cpu_percent > 85% OR mem_percent > 90% for 3 consecutive
readings) as a secondary confirmation signal. The contamination parameter is
set to 0.05 (5% expected anomaly rate) with n_estimators=100 and
random_state=42 for reproducibility.
"""
