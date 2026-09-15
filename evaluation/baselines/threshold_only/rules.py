"""Approved first-match rules. No confidence gate or feedback dependency."""
import hashlib
import json
from pathlib import Path
from evaluation.baselines.common.contracts import validate_actions

RULES_PATH = Path(__file__).with_name('rules.json')
RULE_BYTES = RULES_PATH.read_bytes()
SPEC = json.loads(RULE_BYTES)
RULES_VERSION = SPEC['version']
RULES_SHA256 = hashlib.sha256(RULE_BYTES).hexdigest()
ACTION_SETS = {k: tuple(v) for k, v in SPEC['action_sets'].items()}
REASONS = tuple(SPEC['precedence'])
if not all(validate_actions(list(v)) for v in ACTION_SETS.values()):
    raise ValueError('Invalid frozen action set')
FAMILIES = {'cpu_memory_spike', 'error_rate_surge', 'throughput_drop', 'auth_failure_flood'}


def decide(incident):
    status, origin = incident['input_status'], incident['input_origin']
    family, severity = incident['anomaly_type'], incident['severity']
    route, risk, actions = 'HITL', None, 'review'
    if status == 'unidentifiable':
        reason, route, actions = REASONS[0], None, None
    elif status == 'invalid':
        reason = REASONS[1]
    elif origin == 'structural':
        reason, risk, actions = REASONS[2], 'HIGH', 'schema'
    elif family == 'compound':
        reason, risk, actions = REASONS[3], 'HIGH', 'compound'
    elif family == 'schema_drift':
        reason, risk, actions = REASONS[4], 'HIGH', 'schema'
    elif family in FAMILIES and severity in {'HIGH', 'CRITICAL'}:
        reason, risk, actions = REASONS[5], 'HIGH', family + '_intervention'
    elif family in FAMILIES and severity in {'LOW', 'MEDIUM'}:
        reason, risk, route, actions = REASONS[6], 'LOW', 'AUTO', family + '_bounded'
    else:
        reason = REASONS[7]
    return {**incident, 'controller': 'threshold_only', 'rules_version': RULES_VERSION,
            'rules_sha256': RULES_SHA256, 'routing_decision': route, 'risk_tier': risk,
            'routing_reason': reason, 'recommended_actions': list(ACTION_SETS[actions]) if actions else [],
            'rationale': f'Deterministic rule {reason}: {status} {severity or "unclassified"} {family} incident.'}
