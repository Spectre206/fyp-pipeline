"""Static checks for the final dashboard metric semantics."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "layer3" / "grafana" / "FYP_Hybrid_Agentic_Framework_Observability_v3_Node_Naming.json"


class DashboardMetricContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panels = json.loads(DASHBOARD.read_text())["panels"]
        cls.by_title = {panel.get("title"): panel for panel in cls.panels}

    def test_detector_counters_are_current_process_bar_gauges(self):
        for title in (
            "Detector Evaluations — Current Process",
            "Detector Detections — Current Process",
        ):
            panel = self.by_title[title]
            self.assertEqual(panel["type"], "bargauge")
            self.assertTrue(panel["targets"][0]["instant"])
            self.assertIn("Current-process", panel["description"])

    def test_active_latency_panels_do_not_present_mtta_or_mttr(self):
        titles = set(self.by_title)
        self.assertNotIn("MTTA (p50 / p95)", titles)
        self.assertNotIn("MTTR (p50 / p95)", titles)
        self.assertIn("End-to-End Decision Latency — p50 / p95", titles)
        self.assertIn("Feedback Completion Latency — p50 / p95", titles)
        self.assertIn("Control-Plane Processing Latency — p50 / p95", titles)
        expressions = "\n".join(
            target.get("expr", "")
            for panel in self.panels for target in panel.get("targets", [])
        )
        self.assertIn("fyp_end_to_end_decision_latency_seconds", expressions)
        self.assertIn("fyp_feedback_completion_latency_seconds", expressions)
        self.assertIn("fyp_control_plane_processing_latency_seconds", expressions)
        self.assertNotIn("fyp_mtta_seconds", expressions)
        self.assertNotIn("fyp_mttr_seconds", expressions)

    def test_auto_executor_exposes_measurable_execution_and_feedback_counts(self):
        source = (ROOT / "layer3" / "auto_executor" / "executor.py").read_text()
        self.assertIn("fyp_auto_executor_attempts_total", source)
        self.assertIn("fyp_auto_executor_execution_latency_seconds", source)
        self.assertIn("fyp_outcome_feedback_emitted_total", source)

if __name__ == "__main__":
    unittest.main()
