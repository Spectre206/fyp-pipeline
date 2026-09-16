import json
import tempfile
import unittest
from pathlib import Path
from evaluation.baselines.common.analyze_comparison import analyze, validate_label
from evaluation.baselines.common.capture_incidents import Capture, load_capture
from evaluation.baselines.common.replay_incidents import replay
from evaluation.baselines.common.journal import new_run
from evaluation.baselines.single_agent.tests.test_contracts import fused

ACTIONS = ['CHECK_QUEUE_DEPTH','MONITOR_AND_ALERT','GENERIC_INVESTIGATE']


def label(identity, safe=True, route='AUTO', **extra):
    return {'incident_id':identity,'safe_to_auto':safe,'expected_route':route,'expected_risk':'LOW' if safe else 'HIGH','acceptable_actions':ACTIONS, **extra}


def decision(identity, route='AUTO', risk='LOW'):
    return {'event_id':identity,'routing_decision':route,'risk_tier':risk,'recommended_actions':ACTIONS,'processing_seconds':.01}


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
