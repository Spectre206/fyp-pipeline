"""Ethernet adaptation tests: no sockets, service starts or publication."""
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from evaluation.baselines.common.journal import Journal
from evaluation.baselines.common import rabbitmq
from evaluation.baselines.shared.evaluate import evaluate
from evaluation.baselines.threshold_only.controller import Controller
from evaluation.baselines.threshold_only.feedback import FeedbackRecorder
from evaluation.baselines.threshold_only.metrics import Metrics
from evaluation.baselines.threshold_only.ethernet_checks import check_targets, check_revision, check_corpus, REQUIRED_TARGETS
from evaluation.baselines.threshold_only.prepare_ethernet_diagnostic import prepare
from evaluation.baselines.threshold_only.tests.test_contracts import fused

ROOT=Path(__file__).resolve().parents[4]


class EthernetTests(unittest.TestCase):
    def test_frozen_runtime_bytes(self):
        expected={
            'controller.py':'eb386f51040e097c524949ca511fb515f62144dc2b6f855235d475b2ebf6f8c3',
            'rules.py':'24002a2975ed085cb3d9b639da3c5e9bbc43e63f07a25e864c9f09a637190fbc',
            'rules.json':'b895e21134fbab1741865ef6c05985df6f4782f74451ba863965af32c9a83245',
            'feedback.py':'1b21b7eb203e6d47beb0c64bb6ed5b9000266a25e7a9431f97888ef798318879',
            'metrics.py':'6bed901e2f3f7d4c34c23a3c63b781acf9817a980fd8c576c2554b751532f9d8'}
        for name,digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT/'evaluation/baselines/threshold_only'/name).read_bytes()).hexdigest(),digest)

    def test_profiles_and_broker_env(self):
        for node in (2,3):
            path=ROOT/f'deployment/ethernet/node{node}.env.sh'
            result=subprocess.check_output(['bash','-c','source "$1"; printf "%s:%s" "$RABBITMQ_HOST" "$RABBITMQ_PORT"','bash',str(path)],text=True)
            self.assertEqual(result,'10.10.10.11:5672')
        with patch.dict(os.environ,dict(RABBITMQ_HOST='10.10.10.11',RABBITMQ_PORT='5672',RABBITMQ_USER='test',RABBITMQ_PASS='test')):
            with patch.object(rabbitmq.pika,'BlockingConnection') as connect:
                rabbitmq.connect()
                params=connect.call_args.args[0]
                self.assertEqual((params.host,params.port,params.virtual_host),('10.10.10.11',5672,'fyp'))

    def test_real_threshold_exports_join_without_top_level_controller(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);journal=Journal(path);self.addCleanup(journal.close)
            publisher=Mock();controller=Controller(journal,'run',Metrics(),publisher)
            recorder=FeedbackRecorder(journal,'run',Metrics())
            labels={}
            for identity,severity in [('a','MEDIUM'),('h','HIGH')]:
                body=json.dumps(fused(event_id=identity,severity=severity)).encode()
                controller.process(body);controller.process(body)  # duplicate not republished
                route,envelope=publisher.call_args.args;envelope=json.loads(envelope)
                self.assertEqual(envelope['event_id'],identity)
                self.assertEqual(route,'auto.execute' if identity=='a' else 'hitl.queue')
                outcome='AUTO_EXECUTE_SUCCESS' if identity=='a' else 'HITL_APPROVED'
                recorder.process(json.dumps(dict(event_id=identity,outcome_type=outcome,
                    actual_actions_taken=[],operator_notes='',full_policy_result=envelope)).encode())
                labels[identity]=dict(ground_truth_label='ANOMALY',ground_truth_risk_tier='LOW',
                                     expected_route='AUTO',safe_to_auto='true')
            self.assertEqual(publisher.call_count,2)
            self.assertNotIn('controller',journal.records('feedback')[0])
            journal.export()
            summary,decisions,integrity=evaluate(labels,path/'decision.jsonl',path/'feedback.jsonl',
                'threshold_only','run',path/'delivery.jsonl',True)
            self.assertEqual(summary['feedback_completion']['value'],1)
            self.assertEqual(summary['fer']['value'],.5)
            self.assertEqual(summary['expected_auto_controller_coverage']['value'],1)
            self.assertFalse(integrity['feedback_issues'])
            self.assertEqual(summary['counts']['received_anomaly_ids'],2)
            rows=journal.records('feedback');rows[0]['controller']='single_agent'
            (path/'feedback.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            _,_,integrity=evaluate(labels,path/'decision.jsonl',path/'feedback.jsonl','threshold_only','run')
            self.assertEqual(integrity['feedback_issues']['wrong_identity'],1)

    def targets(self):
        rows=[dict(labels=dict(job=job,instance=instance),scrapeUrl=f'http://{host}:{port}/metrics',health='up')
              for job,instance,host,port in sorted(REQUIRED_TARGETS)]
        for job,port in [('fyp-agent-pipeline',p) for p in range(8010,8014)]+[('fyp-single-agent-baseline',8030)]:
            rows.append(dict(labels=dict(job=job,instance=f'ai-brain-node:{port}'),scrapeUrl=f'http://10.10.10.12:{port}/metrics',health='down'))
        return dict(data=dict(activeTargets=rows))

    def test_condition_targets_ignore_inactive(self):
        self.assertEqual(check_targets(self.targets())['required_up'],16)

    def test_target_down_wrong_ip_and_duplicate_rejected(self):
        for change in ['health','url','duplicate']:
            data=self.targets();rows=data['data']['activeTargets']
            if change=='health':rows[0]['health']='down'
            elif change=='url':rows[0]['scrapeUrl']='http://192.168.18.12:9100/metrics'
            else:rows.append(rows[0])
            with self.assertRaises(ValueError):check_targets(data)

    def test_dashboard_selectors_no_proposed_agents(self):
        path=ROOT/'evaluation/baselines/threshold_only/observability/FYP_Threshold_Baseline_Observability.json'
        text=path.read_text();json.loads(text)
        self.assertNotIn('layer1-application',text);self.assertNotIn('layer3-application',text)
        for name in ['fyp-layer1','fyp-layer3-autoexec','fyp-layer3-hitl','fyp-threshold-baseline','fyp-cluster','rabbitmq']:
            self.assertIn(name,text)
        for name in ['fyp_strategy_','fyp_triage_','fyp_learning_','fyp_policy_']:self.assertNotIn(name,text)

    def test_manifest_identity_and_inventory_fail_closed(self):
        with self.assertRaises(ValueError):check_revision(ROOT,{})
        manifest=dict(controller_branch='experiment/threshold-baseline',controller='threshold_only',network_medium='ethernet',replay_speed=1,
                      frozen_input_hashes={name:'a'*64 for name in ['events_1950.jsonl','seg_config.json','labels.csv','labels_routing.csv']})
        with self.assertRaisesRegex(ValueError,'inventory'):check_revision(ROOT,manifest)

    def test_gateway_ethernet_host_and_relative_import_paths(self):
        settings=(ROOT/'layer3/dashboard/settings.py').read_text()
        self.assertIn('"10.10.10.13"',settings)
        for relative,parent in [('layer3/dashboard/hitl/views.py',2),
            ('layer3/dashboard/hitl/management/commands/consume_hitl.py',4)]:
            text=(ROOT/relative).read_text()
            self.assertNotIn('/home/',text)
            self.assertIn(f'Path(__file__).resolve().parents[{parent}]',text)

    def test_complete_revision_inventory_delegates_to_shared_gate(self):
        groups={
          'shared_evaluation':['evaluation/baselines/shared/evaluate.py','evaluation/baselines/shared/verify_revision.py','evaluation/baselines/threshold_only/ethernet_checks.py'],
          'deployment':['deployment/ethernet/node2.env.sh','deployment/ethernet/node3.env.sh','deployment/ethernet/prometheus.ethernet.yml','layer3/dashboard/settings.py','layer3/requirements_node3.txt','layer3/dashboard/hitl/views.py','layer3/dashboard/hitl/management/commands/consume_hitl.py'],
          'routing_policy':['layer2/evaluation/generate_routing_labels.py','layer2/evaluation/ROUTING_LABEL_POLICY.md'],
          'corpus':['seg/labels.csv','seg/labels_routing.csv']}
        manifest=dict(controller_branch='experiment/threshold-baseline',controller='threshold_only',network_medium='ethernet',replay_speed=1,node='ai-brain-node',
            frozen_input_hashes={name:'a'*64 for name in ['events_1950.jsonl','seg_config.json','labels.csv','labels_routing.csv']},
            files={k:[dict(path=p,sha256='a'*64) for p in paths] for k,paths in groups.items()})
        with patch('evaluation.baselines.threshold_only.ethernet_checks.verify',return_value={'status':'verified'}) as gate:
            self.assertEqual(check_revision(ROOT,manifest)['status'],'verified')
            gate.assert_called_once_with(ROOT,manifest)

    def test_full_corpus_validation_and_source_annotation_preservation(self):
        import csv
        from evaluation.baselines.shared.evaluate import load_labels
        from layer2.evaluation.generate_routing_labels import generate
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);rows=[]
            for i in range(1950):
                label,risk,action=('NORMAL','N/A','') if i<1000 else (('ANOMALY','LOW','AUTO_RESTART_CONSUMER') if i<1380 else ('ANOMALY','HIGH','ESCALATE_TO_HITL'))
                rows.append(dict(event_id=str(i),ground_truth_label=label,ground_truth_risk_tier=risk,ground_truth_action=action,expected_route='',safe_to_auto=''))
            with (root/'labels.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            generate(root/'labels.csv',root/'labels_routing.csv')
            (root/'events_1950.jsonl').write_text(''.join(json.dumps({'event_id':str(i)})+'\n' for i in range(1950)))
            (root/'seg_config.json').write_text('{}')
            manifest={'frozen_input_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}}
            self.assertEqual(check_corpus(root,manifest)['events'],1950)
            # Even a rehashed inconsistent original CSV must not redefine source labels.
            p=root/'labels.csv';p.write_text(p.read_text().replace('AUTO_RESTART_CONSUMER','ESCALATE_TO_HITL',1))
            manifest['frozen_input_hashes']['labels.csv']=hashlib.sha256(p.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'annotation changed'):check_corpus(root,manifest)

    def test_corpus_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in ['events_1950.jsonl','labels.csv','labels_routing.csv','seg_config.json']:(Path(temp)/name).write_text('x')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                check_corpus(temp,{'frozen_input_hashes':{name:'a'*64 for name in ['events_1950.jsonl','labels.csv','labels_routing.csv','seg_config.json']}})

    def test_diagnostic_deterministic_fifty_source_events(self):
        import csv
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);corpus=root/'source.jsonl';labels=root/'labels.csv'
            events=[dict(event_id=str(i),affected_component='consumer',value=i) for i in range(60)]
            corpus.write_text(''.join(json.dumps(r)+'\n' for r in events))
            rows=[dict(event_id=str(i),ground_truth_label='NORMAL' if i<25 else 'ANOMALY',
                       ground_truth_risk_tier='N/A' if i<25 else 'LOW',ground_truth_action='' if i<25 else 'AUTO_RESTART_CONSUMER',
                       expected_route='' if i<25 else 'AUTO',safe_to_auto='' if i<25 else 'true') for i in range(60)]
            with labels.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            for name in ['a','b']:prepare(corpus,labels,root/name)
            selected=(root/'a/events_50_diagnostic.jsonl').read_bytes()
            self.assertEqual(selected,(root/'b/events_50_diagnostic.jsonl').read_bytes())
            self.assertEqual(len(selected.splitlines()),50)
            self.assertEqual([json.loads(line)['event_id'] for line in selected.splitlines()],
                             [str(i) for i in list(range(20))+list(range(25,55))])
            with self.assertRaises(FileExistsError):prepare(corpus,labels,root/'a')

if __name__=='__main__':unittest.main()
