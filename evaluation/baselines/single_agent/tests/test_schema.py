import json
import unittest
from evaluation.baselines.single_agent.schema import extract, validate
from evaluation.baselines.single_agent.tests.test_controller import valid_output


class SchemaTests(unittest.TestCase):
    def test_valid(self): self.assertEqual(validate(valid_output()),[])
    def test_extra(self): self.assertIn('EXTRA_FIELD',validate(valid_output(extra=1)))
    def test_missing(self):
        row=valid_output();del row['reasoning'];self.assertIn('MISSING_FIELD',validate(row))
    def test_count(self): self.assertIn('WRONG_ACTION_COUNT',validate(valid_output(recommended_actions=[])))
    def test_duplicate(self): self.assertIn('DUPLICATE_ACTION',validate(valid_output(recommended_actions=['MONITOR_AND_ALERT']*3)))
    def test_unknown(self): self.assertIn('UNKNOWN_ACTION',validate(valid_output(recommended_actions=['fake','CHECK_QUEUE_DEPTH','LOG_AND_CONTINUE'])))
    def test_confidence(self):
        for value in (True,-1,2,None,'0.5',float('nan'),float('inf')):
            with self.subTest(value=value): self.assertIn('INVALID_CONFIDENCE',validate(valid_output(confidence=value)))
    def test_enums(self):
        for field in ('risk_tier','severity','routing_decision'):
            for value in ([],{},None,'invalid'):
                with self.subTest(field=field,value=value): self.assertIn('INVALID_ENUM',validate(valid_output(**{field:value})))
    def test_empty_string(self): self.assertIn('INVALID_STRING',validate(valid_output(reasoning=' ')))
    def test_nonfinite_and_duplicate_keys(self):
        for raw in ('{"confidence":NaN}','{"confidence":Infinity}','{"confidence":1e999}','{"x":1,"x":2}'):
            with self.subTest(raw=raw): self.assertEqual(extract(raw)[2],['INVALID_JSON'])
    def test_extraction_modes(self):
        raw=json.dumps(valid_output())
        for text,mode in ((raw,'direct'),('```json\n'+raw+'\n```','fence'),('Answer: '+raw,'braced')):
            with self.subTest(mode=mode):
                parsed,actual,issues=extract(text);self.assertEqual(actual,mode);self.assertEqual(issues,[]);self.assertEqual(validate(parsed),[])
