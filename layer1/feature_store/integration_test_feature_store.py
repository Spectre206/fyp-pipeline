import sys
import os
import tempfile

# Ensure imports work
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from feature_store import FeatureStore

# v1.1 CHANGELOG: this integration test now wires events through the real
# FeatureStore class (previously it manually assembled BaselineCalibrator +
# FeatureComputer + a deque itself, bypassing feature_store.py entirely --
# which meant it never actually exercised the calibration gate or
# persistence wiring that live in FeatureStore.process()).


def run_integration():
    print("--- Starting Feature Store Integration Test ---\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        fs = FeatureStore(calibration_n=3, baseline_dir=tmpdir)

        # Simulated stream of 5 events for one component
        test_events = [
            {"event_id": f"evt-00{i}", "node": "stream-node",
             "affected_component": "ADM runner",
             "metric_values": {"cpu_percent": float(40 + i * 10)},
             "timestamp": f"2026-04-01T10:00:0{i}+00:00"}
            for i in range(5)
        ]

        for evt in test_events:
            enriched = fs.process(evt)

            print(f"[{evt['event_id']}]")
            if enriched is None:
                print(f"  Still calibrating -- withheld from ADM fan-out (FIX #2 in action)")
            else:
                print(f"  Calibrated:   True")
                print(f"  Window Depth: {enriched['window_depth']}")
                print(f"  Mean CPU:     {enriched['feature_vector'].get('rolling_mean_cpu_percent', 0.0):.2f}")
                print(f"  PSI Score:    {enriched['feature_vector'].get('psi_score_cpu_percent', 0.0)}")
            print("-" * 30)

        print("\n--- Demonstrating persistence across a simulated restart ---\n")

        # A brand-new FeatureStore, same baseline_dir -- simulates a process
        # restart. This component's calibration (3 events, completed above)
        # should be restored from disk, not restarted from scratch (FIX #3).
        fs_after_restart = FeatureStore(calibration_n=3, baseline_dir=tmpdir)
        restart_evt = {
            "event_id": "evt-after-restart", "node": "stream-node",
            "affected_component": "ADM runner",
            "metric_values": {"cpu_percent": 77.0},
            "timestamp": "2026-04-01T10:00:10+00:00",
        }
        result = fs_after_restart.process(restart_evt)
        if result is not None:
            print("[evt-after-restart] Calibration restored from disk -- "
                  "event immediately forwarded, no recalibration needed. (FIX #3 working)")
        else:
            print("[evt-after-restart] UNEXPECTED: calibration was NOT restored -- FIX #3 not working")

    print("\n--- Integration Test Complete: System Ready for ADMRunner ---")
    print("Reminder for whoever builds ADMRunner: FeatureStore.process() can")
    print("return None while a component is still calibrating -- check for")
    print("this before fanning out to detection.fanout.")

if __name__ == "__main__":
    run_integration()