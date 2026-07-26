# layer1/adm/detectors/train_cpu_model.py
"""
Train Isolation Forest model for CPU/Memory Spike detection (Model 1).

Uses NAB datasets (cpu_utilization_asg_misconfiguration + machine_temperature_system_failure)
to train an unsupervised Isolation Forest that learns normal CPU/memory behaviour.

The model is saved to models/isolation_forest_cpu.pkl and will be loaded by
cpu_detector.py for anomaly scoring.

Run once:
    cd ~/fyp-pipeline/layer1/adm
    python3 detectors/train_cpu_model.py
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import os

# ── Constants ─────────────────────────────────────────────────────────
NAB_CPU_PATH  = "../../datasets/NAB/realKnownCause/cpu_utilization_asg_misconfiguration.csv"
NAB_TEMP_PATH = "../../datasets/NAB/realKnownCause/machine_temperature_system_failure.csv"
MODEL_PATH    = os.path.join(os.path.dirname(__file__), "../models/isolation_forest_cpu.pkl")

# Isolation Forest parameters (from System Design v1.2)
CONTAMINATION = 0.05       # expect ~5% anomalies
N_ESTIMATORS  = 100        # number of trees
RANDOM_STATE  = 42


def load_nab_data(cpu_path: str, temp_path: str) -> np.ndarray:
    """
    Load NAB datasets and extract features for Isolation Forest training.
    NAB format: timestamp, value (cpu utilization % or temperature)
    We create rolling window features similar to what the Feature Store produces.
    """
    print(f"Loading NAB data...")
    
    cpu_df = pd.read_csv(cpu_path)
    temp_df = pd.read_csv(temp_path)
    
    print(f"  CPU dataset: {len(cpu_df)} rows, columns: {list(cpu_df.columns)}")
    print(f"  Temp dataset: {len(temp_df)} rows, columns: {list(temp_df.columns)}")
    
    # NAB format: "timestamp", "value"
    # Combine both datasets into one training set
    cpu_values = cpu_df["value"].values.astype(float)
    temp_values = temp_df["value"].values.astype(float)
    
    # Create features from each dataset independently, then stack
    cpu_features = _create_features(cpu_values, "cpu")
    temp_features = _create_features(temp_values, "temp")
    
    # Combine
    all_features = np.vstack([cpu_features, temp_features])
    
    print(f"  Total training samples: {len(all_features)}")
    print(f"  Feature columns: {all_features.shape[1]}")
    
    return all_features


def _create_features(values: np.ndarray, label: str) -> np.ndarray:
    """
    Create a feature matrix from a 1-D time series.
    Each row is a sliding window of the last 30 values with statistical features,
    mirroring what the Feature Store computes at runtime.
    """
    window_size = 30
    features = []
    
    for i in range(window_size, len(values)):
        window = values[i-window_size:i]
        current = values[i]
        
        row = [
            np.mean(window),           # rolling_mean
            np.std(window),            # rolling_std
            np.min(window),            # rolling_min
            np.max(window),            # rolling_max
            current,                    # current value
            current - values[i-1] if i > 0 else 0,  # rate_of_change
            np.sum(window > np.mean(window) + 2*np.std(window)),  # spike_count
            np.mean(window[-5:]),      # short_ma (5)
            np.mean(window[-20:]) if len(window) >= 20 else np.mean(window),  # long_ma (20)
            (current - np.mean(window)) / np.std(window) if np.std(window) > 0 else 0,  # z_score
        ]
        features.append(row)
    
    return np.array(features)


def train_model(features: np.ndarray) -> tuple:
    """Train Isolation Forest and scaler."""
    print(f"\nTraining Isolation Forest...")
    print(f"  Samples: {len(features)}")
    print(f"  Contamination: {CONTAMINATION}")
    print(f"  Estimators: {N_ESTIMATORS}")
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features)
    
    # Train Isolation Forest
    model = IsolationForest(
        contamination=CONTAMINATION,
        n_estimators=N_ESTIMATORS,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_scaled)
    
    # Quick sanity check
    scores = model.decision_function(X_scaled)
    predictions = model.predict(X_scaled)
    n_anomalies = np.sum(predictions == -1)
    
    print(f"\n  Training complete:")
    print(f"  Anomalies detected in training data: {n_anomalies} ({n_anomalies/len(predictions)*100:.1f}%)")
    print(f"  Decision score range: [{scores.min():.3f}, {scores.max():.3f}]")
    print(f"  Decision score mean: {scores.mean():.3f}")
    
    return model, scaler


def save_model(model, scaler, path: str):
    """Save model and scaler to disk."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump({"model": model, "scaler": scaler}, path)
    print(f"\nModel saved to {path}")


if __name__ == "__main__":
    features = load_nab_data(NAB_CPU_PATH, NAB_TEMP_PATH)
    model, scaler = train_model(features)
    save_model(model, scaler, MODEL_PATH)