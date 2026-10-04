import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from evaluation.baselines.common.contracts import ROOT
from evaluation.baselines.single_agent.tests.test_contracts import fused
from evaluation.baselines.single_agent.tests.test_controller import valid_output


class NetworkTests(unittest.TestCase):
    def command(self, root, medium):
        return [sys.executable,'-B','-m','evaluation.baselines.single_agent.controller',
                '--run-id','test','--output',str(root/medium),'--network-medium',medium,
                '--dry-run',str(root/'input.jsonl'),'--mock-responses',str(root/'responses.jsonl')]

    def test_wifi_ethernet_provenance_and_decision_invariance(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'input.jsonl').write_text(json.dumps(fused())+'\n')
            (root/'responses.jsonl').write_text(json.dumps({'raw_response':json.dumps(valid_output())})+'\n')
            rows=[]
            for medium in ('wifi','ethernet'):
                result=subprocess.run(self.command(root,medium),cwd=ROOT,text=True,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr)
                manifest=json.loads((root/medium/'run.json').read_text())
                self.assertEqual(manifest['network_medium'],medium)
                self.assertTrue(manifest['ended_at']);self.assertTrue(manifest['measured_start_at'])
                self.assertEqual(manifest['requested_options'],{'num_ctx':2048,'num_predict':512})
                row=json.loads((root/medium/'decision.jsonl').read_text())
                rows.append({k:row[k] for k in ('accepted_model_output','routing_decision','risk_tier','recommended_actions','rationale')})
            self.assertEqual(*rows)
            before=(root/'wifi/decision.jsonl').read_bytes()
            self.assertNotEqual(subprocess.run(self.command(root,'wifi'),cwd=ROOT,capture_output=True).returncode,0)
            self.assertEqual(before,(root/'wifi/decision.jsonl').read_bytes())

    def test_invalid_network_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertEqual(subprocess.run(self.command(root,'cellular'),cwd=ROOT,capture_output=True).returncode,2)
            self.assertFalse((root/'cellular').exists())

    def test_live_requires_network(self):
        with tempfile.TemporaryDirectory() as directory:
            result=subprocess.run([sys.executable,'-B','-m','evaluation.baselines.single_agent.controller',
                '--live','--run-id','test','--output',str(Path(directory)/'run')],cwd=ROOT,capture_output=True)
            self.assertEqual(result.returncode,2)
            self.assertFalse((Path(directory)/'run').exists())
