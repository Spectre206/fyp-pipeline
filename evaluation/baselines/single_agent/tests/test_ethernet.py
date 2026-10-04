"""Offline Ethernet readiness and native-export integration; no live services."""
import copy
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from evaluation.baselines.single_agent import ethernet_checks as checks
from evaluation.baselines.single_agent.controller import Controller
from evaluation.baselines.single_agent.feedback import FeedbackRecorder
from evaluation.baselines.single_agent.metrics import Metrics
from evaluation.baselines.single_agent.tests.test_contracts import fused
from evaluation.baselines.single_agent.tests.test_controller import valid_output, fake_client
from evaluation.baselines.common.journal import Journal

ROOT = Path(__file__).resolve().parents[4]


class EthernetTests(unittest.TestCase):
    def targets(self):
        return {'data': {'activeTargets': [
            {'labels': {'job': job, 'instance': instance},
             'scrapeUrl': f'http://{host}:{port}/metrics', 'health': 'up'}
            for job, instance, host, port in sorted(checks.REQUIRED_TARGETS)]}}

    def test_targets_require_single_agent_allow_inactive(self):
        data = self.targets()
        for job in checks.INACTIVE:
            data['data']['activeTargets'].append({'labels': {'job': job}, 'health': 'down'})
        self.assertEqual(checks.check_targets(data)['required_up'], 16)
        self.assertIn(('fyp-single-agent-baseline', 'ai-brain-node:8030', '10.10.10.12', 8030), checks.REQUIRED_TARGETS)

    def test_target_faults_rejected(self):
        for mutation in ('down', 'missing', 'duplicate', 'wifi'):
            data = self.targets(); rows = data['data']['activeTargets']
            if mutation == 'down': rows[0]['health'] = 'down'
            elif mutation == 'missing': rows.pop()
            elif mutation == 'duplicate': rows.append(rows[0])
            else: rows[0]['scrapeUrl'] = 'http://192.168.18.12:8030/metrics'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                checks.check_targets(data)

    def queue_rows(self):
        # Independent RabbitMQ contract: never derive fixtures from checker constants.
        ownership = (
            ('raw.events', 1), ('validated.event', 1),
            ('detect.cpu', 1), ('detect.error', 1), ('detect.throughput', 1),
            ('detect.auth', 1), ('detect.schema', 1), ('fusion.results', 1),
            ('anomaly.detected', 1), ('auto.execute', 1), ('hitl.queue', 1),
            ('outcome.feedback', 1), ('triage.result', 0),
            ('strategy.result', 0), ('dead.letters', 0),
        )
        return [dict(name=name, consumers=consumers,
                     messages_ready=0, messages_unacknowledged=0)
                for name, consumers in ownership]

    def test_queue_names_match_literal_rabbitmq_contract(self):
        self.assertIn('raw.events', checks.ACTIVE_QUEUES)
        self.assertNotIn(r'raw\.events', checks.ACTIVE_QUEUES)
        rows = self.queue_rows()
        self.assertEqual(checks.ACTIVE_QUEUES, {r['name'] for r in rows if r['consumers'] == 1})
        self.assertEqual(checks.IDLE_QUEUES, {r['name'] for r in rows if r['consumers'] == 0})

    def test_escaped_raw_queue_regression_rejected(self):
        incorrect = (checks.ACTIVE_QUEUES - {'raw.events'}) | {r'raw\.events'}
        with patch.object(checks, 'ACTIVE_QUEUES', incorrect):
            with self.assertRaisesRegex(ValueError, 'Missing experiment queue'):
                checks.check_queues(self.queue_rows())

    def test_queue_ownership_and_empty_state(self):
        self.assertEqual(checks.check_queues(self.queue_rows())['queues_verified'], 15)
        for index, row in enumerate(self.queue_rows()):
            invalid_values = {
                'consumers': (0, 2) if row['consumers'] == 1 else (1,),
                'messages_ready': (1,),
                'messages_unacknowledged': (1,),
            }
            for key, values in invalid_values.items():
                for value in values:
                    rows = self.queue_rows(); rows[index][key] = value
                    with self.subTest(queue=row['name'], key=key, value=value), self.assertRaises(ValueError):
                        checks.check_queues(rows)
        for rows in (self.queue_rows()[:-1], self.queue_rows() + self.queue_rows()[:1]):
            with self.assertRaises(ValueError): checks.check_queues(rows)

    def test_both_workers_required(self):
        good = '\n'.join(f'fyp_single_agent_worker_up{{worker="{name}"}} 1.0' for name in ('controller','feedback'))
        self.assertEqual(checks.check_workers(good)['workers_ready'], ['controller','feedback'])
        for bad in (good.replace('1.0','0.0'), good.splitlines()[0], good+'\n'+good,
                    good.replace('1.0','NaN')):
            with self.assertRaises(ValueError): checks.check_workers(bad)

    def test_profiles_dashboard_and_gateway(self):
        for node in (2,3):
            result = subprocess.check_output(['bash','-c',
                'source "$1"; printf "%s:%s" "$RABBITMQ_HOST" "$RABBITMQ_PORT"',
                'bash',str(ROOT/f'deployment/ethernet/node{node}.env.sh')],text=True)
            self.assertEqual(result,'10.10.10.11:5672')
        text=(ROOT/'evaluation/baselines/single_agent/observability/FYP_Single_Agent_Baseline_Observability.json').read_text()
        json.loads(text)
        for old in ('layer1-application','layer3-application','fyp_strategy_','fyp_policy_'):
            self.assertNotIn(old,text)
        for job in ('fyp-layer1','fyp-layer3-autoexec','fyp-layer3-hitl','fyp-single-agent-baseline'):
            self.assertIn(job,text)
        self.assertIn('"10.10.10.13"',(ROOT/'layer3/dashboard/settings.py').read_text())
        for path in ('layer3/dashboard/hitl/views.py','layer3/dashboard/hitl/management/commands/consume_hitl.py'):
            self.assertNotIn('/home/',(ROOT/path).read_text())

    def manifest(self):
        groups = {
            'shared_evaluation': ['evaluation/baselines/shared/evaluate.py','evaluation/baselines/shared/verify_revision.py',
                                  'evaluation/baselines/single_agent/ethernet_checks.py'],
            'deployment': ['deployment/ethernet/node2.env.sh','deployment/ethernet/node3.env.sh',
                           'deployment/ethernet/prometheus.ethernet.yml','layer3/dashboard/settings.py',
                           'layer3/requirements_node3.txt','layer3/dashboard/hitl/views.py',
                           'layer3/dashboard/hitl/management/commands/consume_hitl.py'],
            'routing_policy': ['layer2/evaluation/generate_routing_labels.py','layer2/evaluation/ROUTING_LABEL_POLICY.md'],
            'controller': ['evaluation/baselines/single_agent/'+n for n in
                ('controller.py','feedback.py','llm_client.py','metrics.py','prompt.py','schema.py',
                 'ETHERNET_FULL_RUN.md','ethernet_checks.py','observability/FYP_Single_Agent_Baseline_Observability.json')]
                + ['evaluation/baselines/common/'+n for n in ('contracts.py','journal.py','rabbitmq.py',
                   'layer3_adapter.py','presentation_settings.py','templates/hitl/detail.html')]
                + ['layer2/agents/schema_validator.py']}
        files={g:[dict(path=p,sha256=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()) for p in paths]
               for g,paths in groups.items()}
        files['corpus']=[dict(path='seg/'+n,sha256='a'*64) for n in ('labels.csv','labels_routing.csv')]
        return dict(controller_branch='experiment/single-agent-baseline', controller='single_agent',
            controller_commit='a'*40, network_medium='ethernet',replay_speed=1,node='ai-brain-node',files=files,
            frozen_input_hashes={n:'a'*64 for n in checks.FROZEN_FILES})

    def test_revision_requires_identity_and_complete_inventory(self):
        with self.assertRaises(ValueError): checks.check_revision(ROOT,{})
        for group in ('shared_evaluation','deployment','routing_policy','controller','corpus'):
            m=self.manifest();m['files'][group]=[]
            with self.subTest(group=group), self.assertRaises(ValueError): checks.check_revision(ROOT,m)

    def test_revision_checks_runtime_against_reviewed_commit(self):
        m=self.manifest()
        def blob(command): return (ROOT/command[-1].split(':',1)[1]).read_bytes()
        with patch.object(checks,'verify',return_value={'status':'verified'}) as shared, \
             patch.object(checks.subprocess,'check_output',side_effect=blob) as git:
            self.assertEqual(checks.check_revision(ROOT,m)['status'],'verified')
            shared.assert_called_once_with(ROOT,m)
            self.assertEqual(git.call_count,len(m['files']['controller']))
            m['files']['controller'][0]['sha256']='b'*64
            with self.assertRaisesRegex(ValueError,'hash mismatch'): checks.check_revision(ROOT,m)

    def test_runtime_revision_blob_mismatch_rejected(self):
        with patch.object(checks,'verify',return_value={}), \
             patch.object(checks.subprocess,'check_output',return_value=b'different'):
            with self.assertRaisesRegex(ValueError,'source revision mismatch'):
                checks.check_revision(ROOT,self.manifest())

    def test_corpus_hashes_labels_and_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);rows=[]
            for i in range(1950):
                normal=i<1000;auto=1000<=i<1380
                rows.append(dict(event_id=str(i),ground_truth_label='NORMAL' if normal else 'ANOMALY',
                    ground_truth_risk_tier='N/A' if normal else 'LOW' if auto else 'HIGH',
                    ground_truth_action='NONE' if normal else 'AUTO_RESTART_CONSUMER' if auto else 'ESCALATE_TO_HITL',
                    expected_route='' if normal else 'AUTO' if auto else 'HITL',safe_to_auto='' if normal else 'true' if auto else 'false'))
            for name in ('labels.csv','labels_routing.csv'):
                with (root/name).open('w',newline='') as f:
                    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            (root/'events_1950.jsonl').write_text(''.join(json.dumps({'event_id':r['event_id']})+'\n' for r in rows))
            (root/'seg_config.json').write_text('{}')
            m={'frozen_input_hashes':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in checks.FROZEN_FILES}}
            self.assertEqual(checks.check_corpus(root,m)['events'],1950)
            events=(root/'events_1950.jsonl').read_text().splitlines()
            (root/'events_1950.jsonl').write_text('\n'.join(reversed(events))+'\n')
            with self.assertRaisesRegex(ValueError,'hash mismatch'): checks.check_corpus(root,m)

    def test_native_exports_shared_cli_attempts_and_partial_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); journal=Journal(root)
            try:
                publisher=Mock();client=fake_client(valid_output())
                controller=Controller(journal,'run',Metrics(),publisher,client)
                controller.process(json.dumps(fused()).encode())
                identity=journal.records('decision')[0]['event_id']
                payload=json.loads(publisher.call_args.args[1])
                FeedbackRecorder(journal,'run',Metrics()).process(json.dumps(dict(event_id=identity,
                    outcome_type='AUTO_EXECUTE_SUCCESS',actual_actions_taken=[],operator_notes='',full_policy_result=payload)).encode())
                journal.export()
            finally: journal.close()
            rows=[dict(event_id=i,ground_truth_label='ANOMALY',ground_truth_risk_tier='LOW',
                       ground_truth_action='AUTO_RESTART_CONSUMER',expected_route='AUTO',safe_to_auto='true')
                  for i in (identity,'unobserved')]
            with (root/'labels.csv').open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            command=[sys.executable,'-B','-m','evaluation.baselines.shared.evaluate',
                '--labels',str(root/'labels.csv'),'--controller','single_agent','--run-id','run',
                '--output',str(root/'analysis'),'--expect-hitl-feedback']
            for flag,name in [('decisions','decision'),('feedback','feedback'),('deliveries','delivery'),
                              ('attempts','attempt'),('quarantine','quarantine'),('failures','failure')]:
                command += ['--'+flag,str(root/(name+'.jsonl'))]
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            summary=json.loads((root/'analysis/evaluation_summary.json').read_text())
            self.assertEqual(summary['feedback_completion']['value'],1)
            self.assertEqual(summary['expected_auto_controller_coverage']['value'],.5)
            self.assertEqual(summary['expected_auto_missing_before_routing']['value'],.5)
            self.assertEqual(summary['integrity_status'],'no_detected_record_errors')
            self.assertEqual(json.loads((root/'analysis/integrity_report.json').read_text())['attempts']['records'],1)
            self.assertIn('attempts',json.loads((root/'analysis/manifest.json').read_text())['inputs'])
            (root/'attempt.jsonl').unlink()
            command[command.index('--output')+1]=str(root/'missing-analysis')
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('FileNotFoundError',result.stderr)

    def test_publication_failure_preserves_attempt_no_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            journal=Journal(directory)
            try:
                client=fake_client(valid_output());publisher=Mock(side_effect=RuntimeError('publish'))
                controller=Controller(journal,'run',Metrics(),publisher,client)
                body=json.dumps(fused()).encode()
                with self.assertRaises(RuntimeError): controller.process(body)
                journal.export()
                self.assertEqual(len(journal.records('attempt')),1)
                self.assertEqual(journal.records('decision'),[])
                self.assertEqual(len(journal.records('failure')),1)
                publisher.side_effect=None
                controller.process(body)  # object-level redelivery, not formal-run resume permission
                self.assertEqual(client.generate.call_count,1)
            finally: journal.close()
