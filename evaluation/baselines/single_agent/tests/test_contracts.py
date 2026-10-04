import copy
import json
import unittest
from evaluation.baselines.common.contracts import normalize, MODEL_TYPES


def fused(model='z_score_cpu_memory', severity='MEDIUM', event_id='e1'):
    return {'event_id': event_id, 'node': 'stream-node', 'affected_component': 'consumer',
            'timestamp': '2026-09-15T10:00:00+00:00', 'ingestion_time': None,
            'fused_severity': severity, 'fused_confidence': .1, 'fusion_type': 'single',
            'contributing_models': [{'model_name': model, 'severity': severity, 'confidence': .2, 'detected': True}],
            'fused_at': '2026-09-15T10:00:01+00:00', 'note': 'standard_window'}


def structural():
    return {'event_id': 's1', 'node': 'stream-node', 'affected_component': 'consumer',
            'timestamp': '2026-09-15T10:00:00+00:00', 'ingestion_time': None,
            'anomaly_type': 'schema_drift', 'severity': 'MEDIUM', 'risk_tier': 'LOW',
            'bypass_fusion': True, 'detection_model': 'pydantic_validator',
            'detection_metadata': {'error_type': 'MISSING_FIELD'}, 'context': 'error'}


class NormalizationTests(unittest.TestCase):
    def test_five_detector_families(self):
        for model, family in MODEL_TYPES.items():
            with self.subTest(model=model):
                got = normalize(fused(model))
                self.assertEqual((got['anomaly_type'], got['input_status']), (family, 'valid'))

    def test_compound(self):
        raw = fused()
        raw['fusion_type'] = 'compound'
        raw['contributing_models'].append(fused('z_score_error_rate')['contributing_models'][0])
        self.assertEqual(normalize(raw)['anomaly_type'], 'compound')

    def test_structural_preserves_risk_only_as_provenance(self):
        got = normalize(structural())
        self.assertIsNone(got['input_confidence'])
        self.assertEqual(got['original_event']['risk_tier'], 'LOW')
        self.assertEqual(got['input_status'], 'valid')

    def test_unknown_detector(self):
        self.assertEqual(normalize(fused('unseen'))['anomaly_type'], 'unknown')

    def test_malformed(self):
        for body in (b'{', b'[]', b'null', b'\xff', b'{"event_id":NaN}'):
            with self.subTest(body=body):
                self.assertEqual(normalize(body)['input_status'], 'unidentifiable')

    def test_missing_or_invalid_id(self):
        for identity in (None, '', ' ', 1, 'x' * 256):
            self.assertEqual(normalize(fused(event_id=identity))['input_status'], 'unidentifiable')

    def test_original_is_unmodified(self):
        raw = fused()
        expected = copy.deepcopy(raw)
        got = normalize(raw)
        self.assertEqual(raw, expected)
        got['original_event']['node'] = 'changed'
        self.assertEqual(raw, expected)

    def test_inconsistent_fusion(self):
        raw = fused()
        raw['fusion_type'] = 'compound'
        self.assertEqual(normalize(raw)['input_status'], 'invalid')

    def test_confidence_bounds_and_types(self):
        for value in (-.1, 1.1, True, '0.5', None, float('inf')):
            raw = fused()
            raw['fused_confidence'] = value
            self.assertEqual(normalize(raw)['input_status'], 'invalid')

    def test_duplicate_models_invalid(self):
        raw = fused()
        raw['contributing_models'] *= 2
        raw['fusion_type'] = 'compound'
        self.assertEqual(normalize(raw)['input_status'], 'invalid')

    def test_invalid_severity_types(self):
        for value in ([], {}, None, 'N/A'):
            raw = fused()
            raw['fused_severity'] = value
            self.assertEqual(normalize(raw)['input_status'], 'invalid')

    def test_malformed_model(self):
        for model in (None, 'x', {}, {'model_name': 'a', 'severity': [], 'detected': True, 'confidence': .5}):
            raw = fused()
            raw['contributing_models'] = [model]
            self.assertEqual(normalize(raw)['input_status'], 'invalid')
