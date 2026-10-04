"""Generic structure only: no severity/risk/confidence routing relationship."""
import hashlib
import json
import re
from evaluation.baselines.common.contracts import ALLOWED_ACTIONS, SEVERITIES, decode, number

VERSION = 'sa-schema-v1'
FIELDS = ('anomaly_type', 'severity', 'affected_component', 'recommended_actions',
          'confidence', 'risk_tier', 'routing_decision', 'reasoning')
SCHEMA = {
    'type': 'object', 'additionalProperties': False, 'required': list(FIELDS),
    'properties': {
        'anomaly_type': {'type': 'string', 'minLength': 1},
        'severity': {'type': 'string', 'enum': ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']},
        'affected_component': {'type': 'string', 'minLength': 1},
        'recommended_actions': {'type': 'array', 'minItems': 3, 'maxItems': 3, 'uniqueItems': True,
                                'items': {'type': 'string', 'enum': sorted(ALLOWED_ACTIONS)}},
        'confidence': {'type': 'number', 'minimum': 0, 'maximum': 1},
        'risk_tier': {'type': 'string', 'enum': ['LOW', 'HIGH']},
        'routing_decision': {'type': 'string', 'enum': ['AUTO', 'HITL']},
        'reasoning': {'type': 'string', 'minLength': 1},
    },
}
SHA256 = hashlib.sha256(json.dumps(SCHEMA, sort_keys=True).encode()).hexdigest()


def extract(text):
    if not isinstance(text, str) or not text.strip():
        return None, 'none', ['INVALID_JSON']
    cleaned = re.sub(r'```(?:json)?', '', text).strip()
    candidates = [('direct', text), ('fence', cleaned)]
    start, end = cleaned.find('{'), cleaned.rfind('}')
    if start >= 0 and end > start:
        candidates.append(('braced', cleaned[start:end + 1]))
    for mode, candidate in candidates:
        try:
            return decode(candidate), mode, []
        except (ValueError, TypeError):
            continue
    return None, 'none', ['INVALID_JSON']


def validate(value):
    if not isinstance(value, dict):
        return ['NOT_OBJECT']
    issues = []
    if set(FIELDS) - value.keys(): issues.append('MISSING_FIELD')
    if value.keys() - set(FIELDS): issues.append('EXTRA_FIELD')
    for field in ('anomaly_type', 'affected_component', 'reasoning'):
        if not isinstance(value.get(field), str) or not value[field].strip(): issues.append('INVALID_STRING')
    for field, choices in [('severity', SEVERITIES), ('risk_tier', {'LOW', 'HIGH'}),
                           ('routing_decision', {'AUTO', 'HITL'})]:
        if not isinstance(value.get(field), str) or value[field] not in choices: issues.append('INVALID_ENUM')
    confidence = value.get('confidence')
    if not number(confidence) or not 0 <= confidence <= 1: issues.append('INVALID_CONFIDENCE')
    actions = value.get('recommended_actions')
    if not isinstance(actions, list) or len(actions) != 3:
        issues.append('WRONG_ACTION_COUNT')
    if isinstance(actions, list):
        if any(not isinstance(a, str) or a not in ALLOWED_ACTIONS for a in actions): issues.append('UNKNOWN_ACTION')
        elif len(set(actions)) != len(actions): issues.append('DUPLICATE_ACTION')
    return sorted(set(issues))
