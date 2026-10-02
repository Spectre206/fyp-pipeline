"""Offline contract tests for routing-label-policy-v2 and FAR/FER denominators."""
import csv
import tempfile
import unittest
from pathlib import Path

from layer2.evaluation.generate_routing_labels import generate
from layer2.evaluation.analyze_run import automation_metrics


class RoutingLabelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.source = self.path / 'labels.csv'
        self.output = self.path / 'labels_routing.csv'

    def write(self, rows, fields=None):
        with self.source.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def row(self, event_id='a', label='ANOMALY', risk='LOW', action='AUTO_RESTART_CONSUMER'):
        return dict(event_id=event_id, ground_truth_label=label,
                    ground_truth_risk_tier=risk, ground_truth_action=action)

    def test_frozen_rules_preservation_and_determinism(self):
        rows = [self.row('normal', 'NORMAL', 'N/A', ''),
                self.row('low'),
                self.row('high', risk='HIGH', action='ESCALATE_TO_HITL')]
        for row in rows:
            row['extra'] = 'preserve, exactly\nincluding newline'
        self.write(rows); original = self.source.read_bytes()
        report = generate(self.source, self.output)
        with self.output.open(newline='') as f:
            reader = csv.DictReader(f); result = list(reader)
            self.assertEqual(reader.fieldnames, list(rows[0]) + ['expected_route', 'safe_to_auto'])
        self.assertEqual(self.source.read_bytes(), original)
        for src, dst in zip(rows, result):
            self.assertEqual(src, {k:dst[k] for k in src})
        self.assertEqual([(r['expected_route'],r['safe_to_auto']) for r in result],
                         [('', ''), ('AUTO','true'), ('HITL','false')])
        generate(self.source, self.path/'again.csv')
        self.assertEqual(self.output.read_bytes(), (self.path/'again.csv').read_bytes())
        self.assertEqual(report['rows'], 3)

    def test_existing_blank_routing_columns_populated_without_duplicate_headers(self):
        row = self.row(); row.update(expected_route='',safe_to_auto='')
        self.write([row]); report = generate(self.source,self.output)
        self.assertEqual(report['source_columns'],report['output_columns'])
        with self.output.open() as f:
            self.assertEqual(next(csv.DictReader(f))['expected_route'],'AUTO')

    def test_reject_malformed_input_before_creating_output(self):
        cases = [[self.row(),self.row()], [self.row(event_id='')],
                 [self.row(risk='')], [self.row(risk='MEDIUM')],
                 [self.row(action='')], [self.row(label='')],
                 [self.row(action='ESCALATE_TO_HITL')], [self.row(risk='HIGH')],
                 [self.row(action='UNKNOWN')], [self.row(action='RESTART_FAILED_CONSUMER')],
                 [self.row(label='UNKNOWN')],
                 [dict(self.row(), expected_route='HITL', safe_to_auto='false')]]
        for rows in cases:
            with self.subTest(rows=rows):
                self.write(rows)
                with self.assertRaises(ValueError):generate(self.source,self.output)
                self.assertFalse(self.output.exists())
        row=self.row();del row['ground_truth_action'];self.write([row])
        with self.assertRaisesRegex(ValueError,'required columns'):generate(self.source,self.output)
        self.source.write_text('event_id,event_id\na,b\n')
        with self.assertRaisesRegex(ValueError,'duplicate CSV'):generate(self.source,self.output)
        self.write([self.row()]);self.source.write_text(self.source.read_text()+'broken,row\n')
        with self.assertRaisesRegex(ValueError,'number of fields'):generate(self.source,self.output)

    def test_never_overwrite_source_or_existing_output(self):
        self.write([self.row()]);original=self.source.read_bytes()
        with self.assertRaises(ValueError):generate(self.source,self.source)
        self.output.hardlink_to(self.source)
        with self.assertRaises(FileExistsError):generate(self.source,self.output)
        self.assertEqual(self.source.read_bytes(),original)


class RoutingMetricTests(unittest.TestCase):
    def test_id_join_denominators_missing_decisions_and_normal_exclusion(self):
        labels = {
            'safe': {'expected_route':'AUTO','safe_to_auto':'true'},
            'unsafe': {'expected_route':'HITL','safe_to_auto':'false'},
            'escalated': {'expected_route':'AUTO','safe_to_auto':'true'},
            'missing': {'expected_route':'AUTO','safe_to_auto':'true'},
            'normal': {'ground_truth_label':'NORMAL','expected_route':'AUTO','safe_to_auto':'false'},
            'blank': {'expected_route':'','safe_to_auto':''},
        }
        policy = {k:dict(routing_decision=v) for k,v in [
            ('escalated','HITL'),('blank','AUTO'),('unsafe','AUTO'),('normal','AUTO'),('safe','AUTO')]}
        far,fer=automation_metrics(policy,labels)
        self.assertEqual((far['numerator'],far['denominator'],far['value']),(1,2,.5))
        self.assertEqual((fer['numerator'],fer['denominator'],fer['value']),(1,2,.5))
        self.assertEqual(fer['eligible_without_policy'],1)
        self.assertEqual(fer['eligible_without_valid_route'],1)
        self.assertEqual(fer['expected_auto_total_corpus'],3)
        self.assertEqual(fer['expected_auto_with_policy'],2)
        self.assertEqual(fer['expected_auto_policy_coverage']['value'],2/3)
        self.assertEqual(fer['expected_auto_missing_before_policy']['value'],1/3)

    def test_eligible_without_policy_has_coverage_but_no_routing_fer(self):
        _,fer=automation_metrics({}, {'a':dict(expected_route='AUTO',safe_to_auto='true')})
        self.assertEqual(fer['status'],'not_computable')
        self.assertEqual(fer['denominator'],0)
        self.assertIsNone(fer['value'])
        self.assertEqual(fer['expected_auto_policy_coverage']['value'],0)
        self.assertEqual(fer['expected_auto_missing_before_policy']['value'],1)

    def test_invalid_policy_record_is_not_a_routing_decision_or_missing_record(self):
        _,fer=automation_metrics({'a':dict(routing_decision='UNKNOWN')},
                                {'a':dict(expected_route='AUTO',safe_to_auto='true')})
        self.assertEqual(fer['status'],'not_computable')
        self.assertEqual(fer['expected_auto_invalid_policy'],1)
        self.assertEqual(fer['expected_auto_missing_policy'],0)
        self.assertEqual(fer['expected_auto_policy_coverage']['value'],0)

    def test_absent_labels_and_zero_denominators_not_computable(self):
        for labels in [{}, {'a':dict(expected_route='',safe_to_auto='')},
                       {'a':dict(expected_route='HITL',safe_to_auto='false')}]:
            far,fer=automation_metrics({'a':dict(routing_decision='HITL')},labels)
            for metric in [far,fer]:
                self.assertEqual(metric['status'],'not_computable')
                self.assertEqual(metric['denominator'],0)
                self.assertIsNone(metric['value'])
            self.assertEqual(fer['expected_auto_policy_coverage']['status'],'not_computable')


if __name__ == '__main__':
    unittest.main()
