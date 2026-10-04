import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import requests
from evaluation.baselines.single_agent.llm_client import Client, ModelError
from evaluation.baselines.single_agent.schema import SCHEMA
from evaluation.baselines.common.capture_incidents import Capture, load_capture
from evaluation.baselines.common.analyze_comparison import analyze
from evaluation.baselines.single_agent.tests.test_contracts import fused
from evaluation.baselines.single_agent.tests.test_controller import valid_output


def response(data):
    return Mock(status_code=200,text=json.dumps(data))


class ReadinessTests(unittest.TestCase):
    @patch('evaluation.baselines.single_agent.llm_client.requests.post')
    def test_client_options_and_real_telemetry(self, post):
        post.return_value=response({'done':True,'response':json.dumps(valid_output()),'eval_count':20,'eval_duration':2000000000,'load_duration':100})
        row=Client('http://localhost:11434').generate('p','s')
        self.assertEqual(row['telemetry']['tokens_per_second'],10)
        payload=post.call_args.kwargs['json']
        self.assertEqual(payload['options'],{'num_ctx':2048,'num_predict':512})
        self.assertEqual(payload['format'],SCHEMA)
        self.assertEqual(post.call_args.kwargs['timeout'],35)
        self.assertFalse(payload['stream'])

    @patch('evaluation.baselines.single_agent.llm_client.requests.post')
    def test_missing_tokens_unavailable(self, post):
        post.return_value=response({'done':True,'response':'{}'})
        self.assertIsNone(Client().generate('p','s')['telemetry']['tokens_per_second'])

    @patch('evaluation.baselines.single_agent.llm_client.requests.post')
    def test_transport_classification(self, post):
        for error,category in ((requests.Timeout(),'timeout'),(requests.ConnectionError(),'connection'),(requests.HTTPError(),'http')):
            with self.subTest(category=category):
                post.side_effect=error
                with self.assertRaises(ModelError) as caught:Client().generate('p','s')
                self.assertEqual(caught.exception.category,category)

    @patch('evaluation.baselines.single_agent.llm_client.requests.post')
    def test_invalid_runtime(self, post):
        for data in ({'response':'{}'},{'done':True,'response':{}},[]):
            post.return_value=response(data)
            with self.assertRaises(ModelError) as caught:Client().generate('p','s')
            self.assertEqual(caught.exception.category,'invalid_runtime_response')

    @patch('evaluation.baselines.single_agent.llm_client.requests.post')
    def test_warmup_is_fixed_separate_two_requests(self, post):
        post.side_effect=[response({'done':True}),response({'done':True,'response':'{"ready":true}'})]
        result=Client().warmup()
        self.assertEqual(post.call_count,2)
        self.assertNotIn('prompt',post.call_args_list[0].kwargs['json'])
        self.assertEqual(post.call_args_list[1].kwargs['json']['prompt'],'Return the JSON object {"ready":true}.')
        self.assertEqual(result['protocol'],'preload-and-fixed-inference-v1')

    def test_bad_manifest_schedule_and_count(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);capture=Capture(root)
            capture.write('anomaly.fused',json.dumps(fused()).encode());capture.finish()
            path=root/'incidents.manifest.json';manifest=json.loads(path.read_text())
            for changes in ({'schedule':'wrong'},{'count':True},{'capture_complete':False}):
                path.write_text(json.dumps({**manifest,**changes}))
                with self.assertRaises(ValueError):load_capture(root/'incidents.jsonl',path)

    def test_mixed_and_wrong_run_evidence(self):
        rows=[{'event_id':'a','run_id':'one','controller':'single_agent','routing_decision':'AUTO'},
              {'event_id':'b','run_id':'two','controller':'single_agent','routing_decision':'AUTO'}]
        with self.assertRaises(ValueError):analyze(['a','b'],rows)
        result=analyze(['a','b'],rows,run_id='one',controller='single_agent')
        self.assertEqual(result['wrong_run_decisions'],1)
        self.assertEqual(result['missing_decisions'],['b'])
