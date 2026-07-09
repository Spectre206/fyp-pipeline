import sys
import os
from collections import deque
from baseline_calibrator import BaselineCalibrator
from feature_computers import FeatureComputer

# Ensure imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def run_integration():
    fc = FeatureComputer()
    cal = BaselineCalibrator(calibration_n=3)
    win = deque(maxlen=1000)

    # Simulated stream of 5 events
    test_events = [
        {"event_id": f"evt-00{i}", "node": "stream-node",
         "affected_component": "ADM runner",
         "metric_values": {"cpu_percent": float(40 + i*10)},
         "timestamp": f"2026-04-01T10:00:0{i}+00:00"}
        for i in range(5)
    ]

    print("--- Starting Feature Store Integration Test ---\n")

    for evt in test_events:
        metrics = evt["metric_values"]
        
        # 1. Update Calibrator state
        cal.update(metrics)
        
        # 2. Update Window state
        win.append({"metrics": metrics, "timestamp": evt["timestamp"]})

        # 3. Compute Features (this combines both states)
        features = fc.compute(list(win), cal.baseline)

        # Output results for inspection
        print(f"[{evt['event_id']}]")
        print(f"  Calibrated:   {cal.is_calibrated()}")
        print(f"  Window Depth: {len(win)}")
        print(f"  Mean CPU:     {features.get('rolling_mean_cpu_percent', 0.0):.2f}")
        print(f"  PSI Score:    {features.get('psi_score_cpu_percent', 0.0)}")
        print("-" * 30)

    print("\n--- Integration Test Complete: System Ready for ADMRunner ---")

if __name__ == "__main__":
    run_integration()