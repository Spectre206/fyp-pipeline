import base64
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from evaluation.baselines.shared.evaluate import evaluate, load_labels, normalize


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.labels={}
        for i,risk in [('a','LOW'),('b','LOW'),('c','LOW'),('u','HIGH'),('v','HIGH'),('n','N/A')]:
            self.labels[i]=dict(event_id=i,ground_truth_label='NORMAL' if i=='n' else 'ANOMALY',
                ground_truth_risk_tier=risk,ground_truth_action={'LOW':'AUTO_RESTART_CONSUMER','HIGH':'ESCALATE_TO_HITL','N/A':''}[risk],
                expected_route={'LOW':'AUTO','HIGH':'HITL','N/A':''}[risk],safe_to_auto={'LOW':'true','HIGH':'false','N/A':''}[risk])
        self.csv=self.root/'labels.csv'
        with self.csv.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(self.labels['a']));w.writeheader();w.writerows(self.labels.values())
        self.decisions=self.root/'decision.jsonl';self.feedback=self.root/'feedback.jsonl'

    def row(self,i='a',route='AUTO',controller='threshold_only',**kw):
        return dict(event_id=i,routing_decision=route,controller=controller,run_id='run',risk_tier='LOW',**kw)

    def write(self,path,rows):path.write_text(''.join(json.dumps(r)+'\n' for r in rows))

    def run_eval(self,rows,feedback=(),**kw):
        self.write(self.decisions,rows);self.write(self.feedback,feedback)
        return evaluate(self.labels,self.decisions,self.feedback,'threshold_only','run',**kw)

    def fb(self,i='a',route='AUTO',**kw):
        outcome='AUTO_EXECUTE_SUCCESS' if route=='AUTO' else 'HITL_APPROVED'
        return dict(event_id=i,run_id='run',controller='threshold_only',status='accepted',outcome_type=outcome,
            payload=dict(event_id=i,outcome_type=outcome,full_policy_result=dict(event_id=i,run_id='run',controller='threshold_only')),**kw)

    def test_threshold_normalization(self):
        for route in ['AUTO','HITL']:
            self.assertEqual(normalize(self.row(route=route),'threshold_only','run',{})['actual_route'],route)

    def test_single_agent_normalization(self):
        for route in ['AUTO','HITL']:
            r=self.row(route=route,controller='single_agent',attempts=[{'valid':True}],fallback_applied=False)
            n=normalize(r,'single_agent','run',{})
            self.assertEqual(n['actual_route'],route);self.assertEqual(len(n['validation_metadata']['attempts']),1)

    def test_id_join_final_metrics_normal_exclusion_and_missing_coverage(self):
        s,_,i=self.run_eval([self.row('u'),self.row('n'),self.row('b','HITL'),self.row('a')])
        self.assertEqual((s['far']['numerator'],s['far']['denominator']),(1,2))
        self.assertEqual((s['fer']['numerator'],s['fer']['denominator']),(1,2))
        self.assertEqual(s['expected_auto_controller_coverage']['value'],2/3)
        self.assertEqual(s['expected_auto_missing_before_routing']['value'],1/3)
        self.assertEqual(i['expected_auto_without_scoreable_decision'],['c'])
        # Neither obsolete unsafe-population FAR (denominator 2 happens to match here)
        # nor full-corpus FER (denominator 3) is used.
        s,_,_=self.run_eval([self.row('a'),self.row('b'),self.row('u')])
        self.assertEqual(s['far']['denominator'],3)

    def test_duplicate(self):
        s,n,i=self.run_eval([self.row(),self.row()]);self.assertEqual(len(n),1)
        self.assertEqual(i['duplicate_decision_ids'],['a']);self.assertEqual(s['integrity_status'],'review_required')

    def test_conflict_excluded_even_with_later_repeat(self):
        s,n,i=self.run_eval([self.row(),self.row(route='HITL'),self.row()])
        self.assertFalse(n);self.assertEqual(i['conflicting_decision_ids'],['a'])
        self.assertEqual(s['fer']['status'],'not_computable')

    def test_malformed_and_wrong_identity(self):
        r=self.row();r['run_id']='other'
        s,_,i=self.run_eval([self.row(route='UNKNOWN'),r,{'event_id':None}])
        self.assertEqual(len(i['malformed_decision_lines']),1)
        self.assertEqual(len(i['wrong_identity_decision_lines']),2)

    def test_feedback_join_missing_unexpected(self):
        s,_,i=self.run_eval([self.row(),self.row('b','HITL')],[self.fb(),self.fb('u')],expect_hitl_feedback=True)
        self.assertEqual(s['feedback_completion']['value'],.5)
        self.assertEqual(i['missing_feedback_ids'],['b']);self.assertEqual(i['feedback_issues']['unexpected_id'],1)

    def test_feedback_conflict_excluded(self):
        f=self.fb();g=self.fb();g['payload']['operator_notes']='different'
        s,_,i=self.run_eval([self.row()],[f,g]);self.assertEqual(s['feedback_completion']['value'],0)
        self.assertEqual(i['conflicting_feedback_ids'],['a'])

    def test_no_decisions(self):
        s,_,_=self.run_eval([])
        self.assertEqual(s['fer']['status'],'not_computable')
        self.assertEqual(s['expected_auto_controller_coverage']['value'],0)
        self.assertEqual(s['expected_auto_missing_before_routing']['value'],1)

    def test_no_eligible(self):
        self.labels={k:v for k,v in self.labels.items() if k in ('n','u')}
        s,_,_=self.run_eval([])
        self.assertEqual(s['expected_auto_controller_coverage']['status'],'not_computable')

    def test_risk_present(self):
        s,_,_=self.run_eval([self.row('a'),self.row('u')])
        self.assertEqual(s['risk_accuracy']['value'],.5)

    def test_risk_absent(self):
        r=self.row();r['risk_tier']=None
        s,_,_=self.run_eval([r]);self.assertEqual(s['risk_accuracy']['status'],'not_computable')

    def test_delivery_reconciliation(self):
        p=self.root/'delivery.jsonl'
        self.write(p,[dict(body_base64=base64.b64encode(json.dumps({'event_id':i}).encode()).decode()) for i in ['a','b']])
        s,_,i=self.run_eval([self.row()],deliveries_path=p)
        self.assertEqual(s['counts']['received_ids'],2);self.assertEqual(i['received_without_decision'],['b'])

    def test_policy_compatibility_and_reject_changed_labels(self):
        self.assertEqual(load_labels(self.csv),self.labels)
        self.csv.write_text(self.csv.read_text().replace('AUTO,true','HITL,false'))
        with self.assertRaises(ValueError):load_labels(self.csv)

    def test_unknown_and_wrong_route_feedback(self):
        f=self.fb();f['outcome_type']='HITL_APPROVED';f['payload']['outcome_type']='HITL_APPROVED'
        s,_,i=self.run_eval([self.row()],[f])
        self.assertEqual(i['feedback_issues']['route_mismatch'],1)
        self.assertEqual(s['feedback_completion']['value'],0)

    def test_duplicate_label_rejected(self):
        text=self.csv.read_text();self.csv.write_text(text+text.splitlines()[1]+'\n')
        with self.assertRaises(ValueError):load_labels(self.csv)

    def test_duplicate_json_key_rejected(self):
        self.decisions.write_text('{"event_id":"a","event_id":"b"}\n')
        _,_,i=evaluate(self.labels,self.decisions,None,'threshold_only','run')
        self.assertEqual(i['malformed_decision_lines'],[1])

    def test_bad_json_and_nonfinite(self):
        self.decisions.write_text('{broken\n{"value":NaN}\n')
        s,_,i=evaluate(self.labels,self.decisions,None,'threshold_only','run')
        self.assertEqual(i['malformed_decision_lines'],[1,2])

    def test_cli_no_proposed_stages_deterministic_outputs(self):
        self.write(self.decisions,[self.row()]);self.write(self.feedback,[self.fb()])
        for name in ['out1','out2']:
            subprocess.run([sys.executable,'-B','-m','evaluation.baselines.shared.evaluate','--labels',str(self.csv),
                '--decisions',str(self.decisions),'--feedback',str(self.feedback),'--controller','threshold_only',
                '--run-id','run','--output',str(self.root/name)],check=True,capture_output=True)
        for p in (self.root/'out1').iterdir():self.assertEqual(p.read_bytes(),(self.root/'out2'/p.name).read_bytes())

if __name__=='__main__':unittest.main()
