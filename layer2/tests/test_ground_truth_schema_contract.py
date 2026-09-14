"""Regression checks for the manually annotated FAR/FER label columns."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class GroundTruthSchemaContractTests(unittest.TestCase):
    def test_seg_writes_blank_manual_far_fer_columns(self):
        source = (ROOT / "layer1" / "seg" / "seg.py").read_text()
        self.assertIn('"expected_route"', source)
        self.assertIn('"safe_to_auto"', source)

    def test_event_templates_leave_manual_fields_unlabeled(self):
        tree = ast.parse((ROOT / "layer1" / "seg" / "event_templates.py").read_text())
        assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Dict)]
        template_dicts = [
            node for node in assignments
            if any(isinstance(key, ast.Constant) and key.value == "ground_truth_label" for key in node.keys)
        ]
        self.assertGreaterEqual(len(template_dicts), 3)
        for template in template_dicts:
            values = {
                key.value: value for key, value in zip(template.keys, template.values)
                if isinstance(key, ast.Constant)
            }
            self.assertIsInstance(values["expected_route"], ast.Constant)
            self.assertIsNone(values["expected_route"].value)
            self.assertIsInstance(values["safe_to_auto"], ast.Constant)
            self.assertIsNone(values["safe_to_auto"].value)


if __name__ == "__main__":
    unittest.main()
