# layer1/adm/detectors/train_auth_model.py
"""
Train Random Forest model for Auth Failure Flood detection (Stage 2).

Uses the KDD99 10% dataset to train a binary classifier that distinguishes
normal traffic from auth-related attacks (guess_passwd, ftp_write, imap, etc.).

The model is saved to models/auth_rf.pkl and will be loaded by auth_detector.py
as a secondary confirmation stage after the rate-gate flags an event.

Run once:
    cd ~/fyp-pipeline/layer1/adm
    python3 detectors/train_auth_model.py
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os

# ── Constants ─────────────────────────────────────────────────────────
KDD99_PATH = "../../datasets/KDD99/kddcup.data_10_percent"
MODEL_PATH = "../models/auth_rf.pkl"

# KDD99 column names (41 features + label)
COLUMNS = [
    "duration", "protocol_type", "service", "flag",
    "src_bytes", "dst_bytes", "land", "wrong_fragment", "urgent",
    "hot", "num_failed_logins", "logged_in", "num_compromised", "root_shell",
    "su_attempted", "num_root", "num_file_creations", "num_shells",
    "num_access_files", "num_outbound_cmds", "is_host_login", "is_guest_login",
    "count", "srv_count", "serror_rate", "srv_serror_rate",
    "rerror_rate", "srv_rerror_rate", "same_srv_rate", "diff_srv_rate",
    "srv_diff_host_rate", "dst_host_count", "dst_host_srv_count",
    "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate", "dst_host_srv_serror_rate",
    "dst_host_rerror_rate", "dst_host_srv_rerror_rate",
    "label"
]

# Attack types that are auth-related
AUTH_ATTACKS = {
    "guess_passwd.", "ftp_write.", "imap.", "spy.",
    "warezclient.", "warezmaster.", "multihop.", "phf.",
}

# Columns to use for training (numeric features most relevant to auth)
FEATURE_COLS = [
    "duration", "src_bytes", "dst_bytes",
    "num_failed_logins", "logged_in", "num_compromised",
    "root_shell", "su_attempted", "num_root",
    "count", "srv_count", "serror_rate", "rerror_rate",
    "same_srv_rate", "dst_host_count", "dst_host_srv_count",
    "dst_host_serror_rate", "dst_host_rerror_rate",
]


def load_and_prepare(data_path: str) -> pd.DataFrame:
    """Load KDD99 data and create binary labels (auth_attack=1, normal=0)."""
    print(f"Loading KDD99 data from {data_path}...")
    df = pd.read_csv(data_path, names=COLUMNS)

    # Create binary label: 1 for auth attacks, 0 for everything else
    df["is_auth_attack"] = df["label"].apply(
        lambda x: 1 if x in AUTH_ATTACKS else 0
    )

    # Keep only normal + auth attack rows (drop other attack types for cleaner training)
    df = df[df["label"].isin(AUTH_ATTACKS | {"normal."})]

    print(f"  Total rows: {len(df)}")
    print(f"  Auth attacks: {df['is_auth_attack'].sum()}")
    print(f"  Normal: {(df['is_auth_attack'] == 0).sum()}")

    return df


def train_model(df: pd.DataFrame) -> RandomForestClassifier:
    """Train Random Forest on the prepared data."""
    X = df[FEATURE_COLS].copy()

    # Handle non-numeric columns (protocol_type, service, flag are categorical)
    # For simplicity, drop rows with non-numeric values in feature columns
    X = X.apply(pd.to_numeric, errors="coerce").dropna()
    y = df.loc[X.index, "is_auth_attack"]

    print(f"\nTraining on {len(X)} samples, {len(FEATURE_COLS)} features...")
    print(f"  Class balance: {y.sum()} attacks, {(y == 0).sum()} normal")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=50,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    print("\nClassification Report (test set):")
    print(classification_report(y_test, y_pred, target_names=["normal", "auth_attack"]))

    return model


def save_model(model: RandomForestClassifier, path: str):
    """Save trained model to disk."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(model, path)
    print(f"\nModel saved to {path}")


if __name__ == "__main__":
    df = load_and_prepare(KDD99_PATH)
    model = train_model(df)
    save_model(model, MODEL_PATH)