import sys
import os
import json
import tempfile
import numpy as np
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Ensure the parent directory is in the path so imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from baseline_calibrator import BaselineCalibrator
from feature_computers import FeatureComputer
from feature_store import FeatureStore

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

    # ── Test 8: Auth Rate Logic (v1.1: now AVERAGE, not SUM — FIX #4) ──
    now = datetime.now(timezone.utc)
    auth_window = [
        {"metrics": {"auth_failures_per_min": 10.0}, "timestamp": (now - timedelta(seconds=30)).isoformat()},
        {"metrics": {"auth_failures_per_min": 20.0}, "timestamp": now.isoformat()},
    ]
    result = fc.compute(auth_window, baseline=None)["auth_failures_per_min"]
    assert result == 15.0, f"Test 8 Failed: Expected average 15.0, got {result}"
    print("✓ Test 8 PASSED: Auth rate is now an AVERAGE (10.0, 20.0 -> 15.0), not a sum")

    # ── Test 9 (NEW): Rolling window truncation — FIX #1 ───────────
    # 40 events at baseline=10.0, then 10 events at a genuine step-change
    # to 100.0. With window_size=30 correctly enforced, rolling_mean must
    # reflect ONLY the last 30 entries (20 @ 10.0 + 10 @ 100.0 = 40.0),
    # NOT the full 50-event history (which would give 28.0).
    step_change_window = (
        [{"metrics": {"cpu_percent": 10.0}, "timestamp": f"2026-04-01T10:{i:02d}:00+00:00"} for i in range(40)] +
        [{"metrics": {"cpu_percent": 100.0}, "timestamp": f"2026-04-01T10:{40+i:02d}:00+00:00"} for i in range(10)]
    )
    result_30 = fc.compute(step_change_window, baseline=None, window_size=30)
    assert abs(result_30["rolling_mean_cpu_percent"] - 40.0) < 1e-6, (
        f"Test 9 Failed: window_size=30 should give mean=40.0 "
        f"(last 30 entries only), got {result_30['rolling_mean_cpu_percent']}"
    )
    # Sanity check: confirm the OLD (buggy) full-history behavior would have
    # given a different, wrong answer -- proves the fix actually changes behavior.
    result_full = fc.compute(step_change_window, baseline=None, window_size=len(step_change_window))
    assert abs(result_full["rolling_mean_cpu_percent"] - 28.0) < 1e-6
    assert result_30["rolling_mean_cpu_percent"] != result_full["rolling_mean_cpu_percent"]
    print(f"✓ Test 9 PASSED: window_size=30 correctly restricts to last 30 events "
          f"(mean=40.0, vs. full-history mean={result_full['rolling_mean_cpu_percent']})")

    # ── Test 10 (NEW): FeatureStore calibration gating — FIX #2 ────
    with tempfile.TemporaryDirectory() as tmpdir:
        fs = FeatureStore(calibration_n=3, baseline_dir=tmpdir)
        results = []
        for i in range(5):
            evt = {
                "node": "stream-node",
                "affected_component": "test-component",
                "metric_values": {"cpu_percent": float(40 + i * 5)},
                "timestamp": f"2026-04-01T10:00:0{i}+00:00",
            }
            results.append(fs.process(evt))

        assert results[0] is None, "Test 10 Failed: event 1 (calibrating) should return None"
        assert results[1] is None, "Test 10 Failed: event 2 (calibrating) should return None"
        assert results[2] is not None, "Test 10 Failed: event 3 (calibration completes here) should return an event"
        assert results[3] is not None and "feature_vector" in results[3]
        assert results[4] is not None and "feature_vector" in results[4]
    print("✓ Test 10 PASSED: FeatureStore withholds events during calibration, "
          "forwards once calibrated (events 1-2 -> None, events 3-5 -> enriched)")

    # ── Test 11 (NEW): Baseline persistence round-trip — FIX #3 ────
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test_baseline.json"
        original = BaselineCalibrator(calibration_n=3)
        for i in range(3):
            original.update({"cpu_percent": float(i * 10)})
        assert original.is_calibrated()
        original.save(path)
        assert path.exists(), "Test 11 Failed: save() did not create a file"

        restored = BaselineCalibrator.load(path)
        assert restored.is_calibrated(), "Test 11 Failed: restored calibrator should already be calibrated"
        assert restored.baseline == original.baseline, "Test 11 Failed: restored baseline doesn't match original"
    print("✓ Test 11 PASSED: BaselineCalibrator save()/load() round-trip preserves the baseline")

    # ── Test 12 (NEW): FeatureStore actually persists across a restart ──
    with tempfile.TemporaryDirectory() as tmpdir:
        fs1 = FeatureStore(calibration_n=3, baseline_dir=tmpdir)
        evt_template = {
            "node": "stream-node",
            "affected_component": "restart-test-component",
        }
        for i in range(3):
            fs1.process({**evt_template,
                         "metric_values": {"cpu_percent": float(50 + i)},
                         "timestamp": f"2026-04-01T11:00:0{i}+00:00"})

        # Simulate a restart: brand-new FeatureStore instance, same baseline_dir
        fs2 = FeatureStore(calibration_n=3, baseline_dir=tmpdir)
        result = fs2.process({**evt_template,
                               "metric_values": {"cpu_percent": 999.0},
                               "timestamp": "2026-04-01T11:00:05+00:00"})
        assert result is not None, (
            "Test 12 Failed: a fresh FeatureStore instance should have loaded the "
            "already-completed calibration from disk and immediately forwarded "
            "this event, not started calibrating from scratch"
        )
    print("✓ Test 12 PASSED: FeatureStore restores calibration state across a simulated restart")

    print("\n--- All 12 tests PASSED ✓ ---")

if __name__ == "__main__":
    run_tests()