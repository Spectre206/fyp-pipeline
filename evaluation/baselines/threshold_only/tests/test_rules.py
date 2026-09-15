import unittest
from evaluation.baselines.common.contracts import normalize, validate_actions
from evaluation.baselines.threshold_only.rules import decide, ACTION_SETS
from evaluation.baselines.threshold_only.tests.test_contracts import fused, structural


class RuleTests(unittest.TestCase):
    def test_all_severity_boundaries(self):
        for model in ('z_score_cpu_memory', 'z_score_error_rate', 'moving_average_throughput', 'statistical_auth_rate'):
            for severity in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'):
                with self.subTest(model=model, severity=severity):
                    got = decide(normalize(fused(model, severity)))
                    self.assertEqual(got['routing_decision'], 'AUTO' if severity in ('LOW', 'MEDIUM') else 'HITL')
                    self.assertEqual(got['risk_tier'], 'LOW' if severity in ('LOW', 'MEDIUM') else 'HIGH')
                    suffix = '_bounded' if severity in ('LOW', 'MEDIUM') else '_intervention'
                    self.assertEqual(got['recommended_actions'], list(ACTION_SETS[got['anomaly_type'] + suffix]))

    def test_structural_override(self):
        got = decide(normalize(structural()))
        self.assertEqual((got['routing_reason'], got['risk_tier']), ('TH_STRUCTURAL_SCHEMA', 'HIGH'))

    def test_schema_override(self):
        self.assertEqual(decide(normalize(fused('distribution_shift_marker', 'LOW')))['routing_reason'], 'TH_SCHEMA_REVIEW')

    def test_compound_override(self):
        raw = fused(severity='LOW')
        raw['fusion_type'] = 'compound'
        raw['contributing_models'].append(fused('distribution_shift_marker', 'LOW')['contributing_models'][0])
        self.assertEqual(decide(normalize(raw))['routing_reason'], 'TH_COMPOUND_REVIEW')

    def test_invalid_precedes_structural(self):
        raw = structural()
        raw['severity'] = 'N/A'
        got = decide(normalize(raw))
        self.assertEqual(got['routing_reason'], 'TH_INPUT_INVALID')
        self.assertIsNone(got['risk_tier'])

    def test_unidentifiable_has_no_actions_or_route(self):
        got = decide(normalize(b'{'))
        self.assertIsNone(got['routing_decision'])
        self.assertEqual(got['recommended_actions'], [])

    def test_unknown(self):
        got = decide(normalize(fused('new_detector')))
        self.assertEqual(got['routing_reason'], 'TH_UNSUPPORTED_INCIDENT')
        self.assertIsNone(got['risk_tier'])

    def test_all_action_sets(self):
        self.assertEqual(len(ACTION_SETS), 11)
        for actions in ACTION_SETS.values():
            self.assertTrue(validate_actions(list(actions)))

    def test_confidence_does_not_gate_auto(self):
        for confidence in (0, .1, .49, .99, 1):
            raw = fused()
            raw['fused_confidence'] = confidence
            self.assertEqual(decide(normalize(raw))['routing_decision'], 'AUTO')

    def test_deterministic(self):
        raw = normalize(fused())
        self.assertEqual(decide(raw), decide(raw))
