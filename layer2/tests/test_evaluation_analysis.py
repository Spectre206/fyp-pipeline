import json
import tempfile
import unittest
import csv
import os
from pathlib import Path
from layer2.evaluation.analyze_run import analyze
from layer2.evaluation.artifacts import record


class EvaluationAnalysisTests(unittest.TestCase):
    def write(self, directory, stage, rows):
        (directory / f"{stage}.jsonl").write_text("\n".join(json.dumps(row) for row in rows))

    def write_labels(self, directory, rows):
        with (directory / "labels.csv").open("w", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    def test_svr_duplicates_feedback_and_unavailable_ground_truth(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            self.write(path, "strategy", [
                {"event_id": "a", "timed_out": False, "valid_json": True, "schema_valid": True, "strategy_latency_s": .2},
                {"event_id": "b", "timed_out": False, "valid_json": True, "schema_valid": False},
                {"event_id": "c", "timed_out": True},
                {"event_id": "a", "timed_out": False, "valid_json": True, "schema_valid": True},
            ])
            self.write(path, "policy", [
                {"event_id": "a", "routing_decision": "AUTO", "routing_reason": "OK", "policy_latency_s": .1, "control_plane_latency_s": .5},
                {"event_id": "b", "routing_decision": "HITL", "routing_reason": "SCHEMA_INVALID"},
            ])
            self.write(path, "feedback", [{"event_id": "a", "outcome_type": "AUTO_EXECUTE_SUCCESS"}])
            summary, _ = analyze(path, expect_hitl_feedback=True)
            self.assertEqual(summary["svr"]["value"], .5)
            self.assertEqual(summary["routing"]["counts"]["AUTO"]["count"], 1)
            self.assertEqual(summary["feedback"]["overall"]["value"], .5)
            self.assertEqual(summary["counts"]["duplicates"]["strategy"], 1)
            self.assertEqual(summary["risk_tier_accuracy"]["status"], "not_computable")

    def test_missing_stages_do_not_crash(self):
        with tempfile.TemporaryDirectory() as temp:
            summary, _ = analyze(Path(temp))
            self.assertEqual(summary["svr"]["total_requests"], 0)
            self.assertEqual(summary["latency_seconds"]["triage_to_policy_wall_clock"]["count"], 0)

    def test_ground_truth_metrics_and_latency_distribution(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            self.write(path, "triage", [
                {"event_id": "a", "triage_latency_s": .1},
                {"event_id": "b", "triage_latency_s": .3},
            ])
            self.write(path, "strategy", [
                {"event_id": "a", "timed_out": False, "valid_json": True, "schema_valid": True, "risk_tier": "LOW", "strategy_latency_s": .2},
                {"event_id": "b", "timed_out": False, "valid_json": True, "schema_valid": True, "risk_tier": "HIGH", "strategy_latency_s": .4},
            ])
            self.write(path, "policy", [
                {"event_id": "a", "routing_decision": "AUTO", "policy_latency_s": .1},
                {"event_id": "b", "routing_decision": "HITL", "policy_latency_s": .2},
            ])
            self.write_labels(path, [
                {"event_id": "a", "ground_truth_risk_tier": "LOW", "expected_route": "AUTO", "safe_to_auto": "true", "expected_action_family": "restart"},
                {"event_id": "b", "ground_truth_risk_tier": "LOW", "expected_route": "AUTO", "safe_to_auto": "false", "expected_action_family": "restart"},
            ])
            summary, _ = analyze(path, path / "labels.csv")
            self.assertEqual(summary["risk_tier_accuracy"]["value"], .5)
            self.assertEqual(summary["false_automation_rate"]["value"], 0.0)
            self.assertEqual(summary["false_escalation_rate"]["value"], .5)
            self.assertEqual(summary["latency_seconds"]["component_processing_sum"]["count"], 2)
            self.assertEqual(summary["latency_seconds"]["stages"]["strategy"]["max"], .4)

    def test_malformed_artifacts_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / "strategy.jsonl").write_text("not json\n[\"not an object\"]\n")
            summary, _ = analyze(path)
            self.assertEqual(summary["counts"]["malformed_records"], 2)

    def test_opt_in_artifacts_and_invalid_run_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            old_run_id = os.environ.get("LAYER2_EVALUATION_RUN_ID")
            old_directory = os.environ.get("LAYER2_EVALUATION_DIR")
            try:
                os.environ["LAYER2_EVALUATION_RUN_ID"] = "evaluation-01"
                os.environ["LAYER2_EVALUATION_DIR"] = temp
                record("triage", {"event_id": "a"})
                saved = Path(temp) / "evaluation-01" / "triage.jsonl"
                self.assertTrue(saved.exists())
                self.assertEqual(json.loads(saved.read_text())["event_id"], "a")

                os.environ["LAYER2_EVALUATION_RUN_ID"] = "../outside"
                record("triage", {"event_id": "b"})
                self.assertEqual(len(saved.read_text().splitlines()), 1)
            finally:
                if old_run_id is None:
                    os.environ.pop("LAYER2_EVALUATION_RUN_ID", None)
                else:
                    os.environ["LAYER2_EVALUATION_RUN_ID"] = old_run_id
                if old_directory is None:
                    os.environ.pop("LAYER2_EVALUATION_DIR", None)
                else:
                    os.environ["LAYER2_EVALUATION_DIR"] = old_directory

if __name__ == "__main__":
    unittest.main()
