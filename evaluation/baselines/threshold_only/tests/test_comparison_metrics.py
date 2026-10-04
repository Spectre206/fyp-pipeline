import json
import tempfile
import unittest
from pathlib import Path
from evaluation.baselines.common.analyze_comparison import analyze, validate_label
from evaluation.baselines.common.capture_incidents import Capture, load_capture
from evaluation.baselines.common.replay_incidents import replay
from evaluation.baselines.common.journal import new_run
from evaluation.baselines.threshold_only.tests.test_contracts import fused

ACTIONS = ['CHECK_QUEUE_DEPTH','MONITOR_AND_ALERT','GENERIC_INVESTIGATE']


def label(identity, safe=True, route='AUTO', **extra):
    return {'incident_id':identity,'safe_to_auto':safe,'expected_route':route,'expected_risk':'LOW' if safe else 'HIGH','acceptable_actions':ACTIONS, **extra}


def decision(identity, route='AUTO', risk='LOW'):
    return {'event_id':identity,'routing_decision':route,'risk_tier':risk,'recommended_actions':ACTIONS,'processing_seconds':.01}


class ComparisonTests(unittest.TestCase):
    def test_far_uses_all_unsafe_not_auto_denominator(self):
        result = analyze(['a','b','c'], [decision('a')], [label('a',False,'HITL'),label('b',False,'HITL'),label('c')])
        self.assertEqual(result['far']['value'], .5)
        self.assertEqual(result['far']['denominator'], 2)
        self.assertEqual(result['missing_decisions'], ['b','c'])

    def test_fer_includes_missing_eligible(self):
        result = analyze(['a','b'], [decision('a','HITL')], [label('a'),label('b')])
        self.assertEqual(result['fer']['value'], .5)
        self.assertEqual(result['completion']['value'], .5)

    def test_zero_denominators(self):
        result = analyze(['a'], [decision('a')])
        for key in ('far','fer','route_accuracy','risk_accuracy'):
            self.assertEqual(result[key]['status'], 'not computable')
            self.assertIsNone(result[key]['value'])

    def test_ambiguous_excluded_not_missing(self):
        result = analyze(['a','b'], [decision('a'),decision('b')], [label('a'),label('b',False,'HITL',ambiguous=True)])
        self.assertEqual(result['route_accuracy']['denominator'], 1)
        self.assertEqual(result['label_coverage']['ambiguous'], 1)
        self.assertEqual(result['completion']['value'], 1)

    def test_risk_and_route_missing_in_denominator(self):
        result = analyze(['a','b'], [decision('a')], [label('a'),label('b')])
        self.assertEqual(result['risk_accuracy']['value'], .5)
        self.assertEqual(result['route_accuracy']['value'], .5)

    def test_conflicts_not_silently_overwritten(self):
        result = analyze(['a'], [decision('a'),decision('a','HITL')], [label('a')])
        self.assertEqual(result['conflicting_decision_ids'], ['a'])
        self.assertEqual(result['completion']['value'], 0)

    def test_labels_invalid_or_duplicate_rejected(self):
        for labels in ([label('a'),label('a')], [label('b')], [label('a',False,'AUTO')]):
            with self.assertRaises(ValueError):
                analyze(['a'], [], labels)

    def test_actions_and_prohibited(self):
        truth = label('a',acceptable_actions=['MONITOR_AND_ALERT'], prohibited_actions=['GENERIC_INVESTIGATE'])
        result = analyze(['a'],[decision('a')],[truth])
        self.assertEqual(result['action_validity']['value'],1)
        self.assertEqual(result['prohibited_action_count'],1)
        self.assertEqual(result['acceptable_action_coverage']['value'],1)

    def test_feedback_completion_scope(self):
        rows=[decision('a'),decision('b','HITL')]
        feedback=[{'status':'accepted','event_id':'a','outcome_type':'AUTO_EXECUTE_SUCCESS'}]
        self.assertEqual(analyze(['a','b'],rows,feedback=feedback)['feedback_completion']['value'],1)
        self.assertEqual(analyze(['a','b'],rows,feedback=feedback,expect_hitl_feedback=True)['feedback_completion']['value'],.5)

    def test_nullable_ambiguous_labels(self):
        self.assertIsNotNone(validate_label(label('a',None,None,expected_risk=None,ambiguous=True)))


class CaptureReplayTests(unittest.TestCase):
    def test_exact_body_order_and_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            capture = Capture(directory)
            bodies = [json.dumps(fused(event_id='a'), indent=2).encode(), json.dumps(fused(event_id='b')).encode()]
            for body in bodies:
                capture.write('anomaly.fused',body)
            capture.finish()
            records,_=load_capture(Path(directory)/'incidents.jsonl',Path(directory)/'incidents.manifest.json')
            calls=[]
            with (Path(directory)/'replay.jsonl').open('w') as output:
                replay(records,lambda *args:calls.append(args),output,'run',sleep=lambda _:None)
            self.assertEqual([args[1] for args in calls],bodies)
            self.assertTrue(all(args[2]['run_id']=='run' for args in calls))

    def test_checksum_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            capture=Capture(directory)
            capture.write('anomaly.fused',json.dumps(fused()).encode())
            capture.finish()
            path=Path(directory)/'incidents.jsonl'
            path.write_bytes(path.read_bytes()+b'\n')
            with self.assertRaises(ValueError):load_capture(path,Path(directory)/'incidents.manifest.json')

    def test_duplicate_capture_id(self):
        with tempfile.TemporaryDirectory() as directory:
            capture=Capture(directory)
            try:
                body=json.dumps(fused()).encode()
                capture.write('anomaly.fused',body)
                with self.assertRaises(ValueError):capture.write('anomaly.fused',body)
            finally:capture.output.close()

    def test_refuses_evidence_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'run'
            new_run(path,'run')
            with self.assertRaises(FileExistsError):new_run(path,'run')
