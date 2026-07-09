import sys
import os
import numpy as np
from datetime import datetime, timezone, timedelta

# Ensure the parent directory is in the path so imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from baseline_calibrator import BaselineCalibrator
from feature_computers import FeatureComputer

def run_tests():
    print("--- Starting Feature Store Unit Tests ---\n")
    
    # ── Test 1: Calibrator Initialization ──────────────────────────
    cal = BaselineCalibrator(calibration_n=5)
    assert not cal.is_calibrated(), "Test 1 Failed: Calibrator should start uncalibrated"
    assert cal.events_until_calibrated() == 5
    print("✓ Test 1 PASSED: Calibrator starts uncalibrated")

    # ── Test 2: Baseline Freezing ────────────────────────────────
    for i in range(5):
        cal.update({"cpu_percent": float(i * 10)})
    assert cal.is_calibrated(), "Test 2 Failed: Calibrator should be calibrated after 5 events"
    assert "cpu_percent" in cal.baseline
    print("✓ Test 2 PASSED: Baseline frozen after 5 events")

    # ── Test 3: No-op After Freeze ──────────────────────────────
    cal.update({"cpu_percent": 999.0})
    assert len(cal.baseline["cpu_percent"]) == 5, "Test 3 Failed: Baseline should not change after freeze"
    print("✓ Test 3 PASSED: Calibrator ignores updates after freeze")

    # ── Test 4: Basic Feature Keys ───────────────────────────────
    fc = FeatureComputer()
    window = [
        {"metrics": {"cpu_percent": float(v), "mem_percent": float(v + 10)},
         "timestamp": f"2026-04-01T10:00:{i:02d}+00:00"}
        for i, v in enumerate([20, 30, 40, 50, 60, 70, 80, 90])
    ]
    features = fc.compute(window, baseline=None)
    
    required_features = ["rolling_mean_cpu_percent", "z_score_cpu_percent", "psi_score_cpu_percent"]
    for feat in required_features:
        assert feat in features, f"Test 4 Failed: {feat} missing"
    print(f"✓ Test 4 PASSED: All feature keys present")

    # ── Test 5: PSI Activation ───────────────────────────────────
    baseline = {"cpu_percent": [20.0, 30.0, 40.0, 50.0, 60.0]}
    features_with_psi = fc.compute(window, baseline=baseline)
    assert features_with_psi["psi_score_cpu_percent"] >= 0.0
    print("✓ Test 5 PASSED: PSI active after calibration")

    # ── Test 6: Z-score Spike Detection ──────────────────────────
    spike_window = [{"metrics": {"cpu_percent": 30.0}, "timestamp": "2026-04-01T10:00:00+00:00"} for _ in range(9)]
    spike_window.append({"metrics": {"cpu_percent": 99.0}, "timestamp": "2026-04-01T10:00:09+00:00"})
    z = fc.compute(spike_window, baseline=None)["z_score_cpu_percent"]
    assert z > 2.0, f"Test 6 Failed: Expected Z > 2.0, got {z:.2f}"
    print(f"✓ Test 6 PASSED: Z-score spike detected (z={z:.2f})")

    # ── Test 7: Silence Duration ─────────────────────────────────
    silent_window = [{"metrics": {"messages_per_second": 0.0}, "timestamp": "2026-04-01T10:00:01+00:00"}]
    assert fc.compute(silent_window, baseline=None)["silence_duration_s"] == 9999.0
    print("✓ Test 7 PASSED: Silence detection working")

    # ── Test 8: Auth Rate Logic ──────────────────────────────────
    now = datetime.now(timezone.utc)
    auth_window = [
        {"metrics": {"auth_failures_per_min": 10.0}, "timestamp": (now - timedelta(seconds=30)).isoformat()},
        {"metrics": {"auth_failures_per_min": 20.0}, "timestamp": now.isoformat()},
    ]
    assert fc.compute(auth_window, baseline=None)["auth_failures_per_min"] == 30.0
    print("✓ Test 8 PASSED: Auth rate calculation correct")

    print("\n--- All 8 tests PASSED ✓ ---")

if __name__ == "__main__":
    run_tests()