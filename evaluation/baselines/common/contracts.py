"""Normalize only observable incident fields; never consult labels or agents."""
import ast
import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODEL_TYPES = {
    'z_score_cpu_memory': 'cpu_memory_spike',
    'z_score_error_rate': 'error_rate_surge',
    'moving_average_throughput': 'throughput_drop',
    'statistical_auth_rate': 'auth_failure_flood',
    'distribution_shift_marker': 'schema_drift',
}
SEVERITIES = {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}


def allowed_actions():
    """Read the literal vocabulary without importing any proposed-system code."""
    tree = ast.parse((ROOT / 'layer2/agents/schema_validator.py').read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == 'ALLOWED_ACTIONS' for t in node.targets
        ):
            return frozenset(ast.literal_eval(node.value.args[0]))
    raise ValueError('Authoritative action vocabulary missing')


ALLOWED_ACTIONS = allowed_actions()


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def decode(body):
    if isinstance(body, dict):
        return copy.deepcopy(body)
    return json.loads(body, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def normalize(body):
    result = dict(event_id=None, input_origin='unknown', anomaly_type='unknown', severity=None,
                  affected_component=None, node=None, input_confidence=None,
                  input_confidence_source=None, input_status='unidentifiable', original_event=None)
    try:
        raw = decode(body)
    except (ValueError, TypeError, UnicodeError):
        return result
    result['original_event'] = raw
    if not isinstance(raw, dict):
        return result
    event_id = raw.get('event_id')
    if not isinstance(event_id, str) or not event_id.strip() or len(event_id) > 255:
        return result
    result.update(event_id=event_id, input_status='valid')
    invalid = False
    for key in ('affected_component', 'node'):
        value = raw.get(key)
        result[key] = value if isinstance(value, str) else None
        if not isinstance(value, str) or not value.strip():
            invalid = True
    structural = raw.get('bypass_fusion') is True
    fused = any(k in raw for k in ('fusion_type', 'contributing_models', 'fused_severity'))
    if structural:
        result.update(input_origin='structural', anomaly_type='schema_drift', severity=raw.get('severity'))
        if fused or raw.get('anomaly_type') != 'schema_drift' or raw.get('detection_model') != 'pydantic_validator':
            invalid = True
        if not isinstance(raw.get('detection_metadata'), dict):
            invalid = True
    elif fused:
        result.update(input_origin='fused', severity=raw.get('fused_severity'),
                      input_confidence_source='fused_confidence')
        confidence = raw.get('fused_confidence')
        if not number(confidence) or not 0 <= confidence <= 1:
            invalid = True
        else:
            result['input_confidence'] = confidence
        models = raw.get('contributing_models')
        if not isinstance(models, list) or not models:
            invalid = True
        else:
            names = []
            for model in models:
                if not isinstance(model, dict):
                    invalid = True
                    continue
                name = model.get('model_name')
                if not isinstance(name, str) or not name:
                    invalid = True
                    continue
                names.append(name)
                conf = model.get('confidence')
                if (model.get('detected') is not True or not isinstance(model.get('severity'), str) or model.get('severity') not in SEVERITIES
                        or not number(conf) or not 0 <= conf <= 1):
                    invalid = True
            if len(set(names)) != len(models):
                invalid = True
            expected = 'compound' if len(models) > 1 else 'single'
            if raw.get('fusion_type') != expected:
                invalid = True
            result['anomaly_type'] = 'compound' if len(models) > 1 else MODEL_TYPES.get(names[0], 'unknown') if names else 'unknown'
            if raw.get('severity') not in (None, result['severity']):
                invalid = True
            if raw.get('anomaly_type') not in (None, result['anomaly_type']):
                invalid = True
    else:
        result.update(anomaly_type='unknown', severity=raw.get('severity'))
    if not isinstance(result['severity'], str) or result['severity'] not in SEVERITIES:
        invalid = True
    if invalid:
        result['input_status'] = 'invalid'
    return result


def validate_actions(actions):
    return (isinstance(actions, list) and len(actions) == 3
            and all(isinstance(x, str) and x in ALLOWED_ACTIONS for x in actions)
            and len(set(actions)) == 3)
