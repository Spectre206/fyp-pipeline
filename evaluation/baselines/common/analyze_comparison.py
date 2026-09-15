"""Controller-neutral ID-based analysis; labels are offline inputs only."""
import argparse
import json
import math
from pathlib import Path
from evaluation.baselines.common.contracts import ALLOWED_ACTIONS, number, validate_actions
from evaluation.baselines.common.capture_incidents import load_capture


def ratio(numerator, denominator):
    return {'status': 'computed' if denominator else 'not computable', 'numerator': numerator,
            'denominator': denominator, 'value': numerator / denominator if denominator else None}


def validate_label(label):
    required = {'incident_id', 'expected_route', 'safe_to_auto', 'expected_risk', 'acceptable_actions'}
    if not isinstance(label, dict) or not required <= label.keys():
        raise ValueError('Missing ground-truth fields')
    if not isinstance(label['incident_id'], str) or not label['incident_id'].strip() or len(label['incident_id']) > 255:
        raise ValueError('Invalid label ID')
    allowed = required | {'prohibited_actions', 'rationale', 'ambiguous', 'reviewer_ids', 'adjudication_notes', 'anomaly_category', 'required_action_categories'}
    if set(label) - allowed:
        raise ValueError('Unknown label fields')
    ambiguous = label.get('ambiguous', False)
    if not isinstance(ambiguous, bool):
        raise ValueError('ambiguous must be boolean')
    for field, choices in [('expected_route', ('AUTO', 'HITL')), ('expected_risk', ('LOW', 'HIGH'))]:
        if label[field] not in choices and not (ambiguous and label[field] is None):
            raise ValueError('Invalid ' + field)
    if not isinstance(label['safe_to_auto'], bool) and not (ambiguous and label['safe_to_auto'] is None):
        raise ValueError('safe_to_auto must be boolean')
    if label['expected_route'] == 'AUTO' and label['safe_to_auto'] is False:
        raise ValueError('Unsafe incident cannot be AUTO eligible')
    for field in ('acceptable_actions', 'prohibited_actions'):
        actions = label.get(field, [])
        if (not isinstance(actions, list) or any(not isinstance(a, str) or a not in ALLOWED_ACTIONS for a in actions)
                or len(set(actions)) != len(actions)):
            raise ValueError('Invalid action labels')
    if set(label['acceptable_actions']) & set(label.get('prohibited_actions', [])):
        raise ValueError('Acceptable and prohibited actions overlap')
    for field in ('rationale', 'adjudication_notes', 'anomaly_category'):
        if field in label and not isinstance(label[field], str):
            raise ValueError('Invalid ' + field)
    for field in ('required_action_categories', 'reviewer_ids'):
        if field in label and (not isinstance(label[field], list) or not all(isinstance(v, str) for v in label[field])):
            raise ValueError('Invalid ' + field)
    return label


def distribution(values):
    values = sorted(v for v in values if number(v) and v >= 0)
    if not values:
        return {'status': 'not computable', 'count': 0}
    percentile = lambda p: values[max(0, math.ceil(p * len(values)) - 1)]
    n = len(values)
    return {'status': 'computed', 'count': n, 'mean': sum(values) / n,
            'median': (values[(n - 1) // 2] + values[n // 2]) / 2,
            'p95': percentile(.95), 'max': values[-1], 'percentile_method': 'nearest-rank'}


def analyze(expected_ids, decisions, labels=(), feedback=(), expect_hitl_feedback=False):
    expected_list = list(expected_ids)
    if any(not isinstance(x, str) or not x.strip() for x in expected_list) or len(set(expected_list)) != len(expected_list):
        raise ValueError('Expected IDs must be unique usable strings')
    expected = set(expected_list)
    truth = {}
    for label in labels:
        validate_label(label)
        identity = label['incident_id']
        if identity in truth or identity not in expected:
            raise ValueError('Duplicate or unexpected label ID')
        truth[identity] = label
    valid, duplicate_ids, conflicts, unexpected, malformed = {}, set(), set(), set(), 0
    for row in decisions:
        if not isinstance(row, dict) or not isinstance(row.get('event_id'), str) or row.get('routing_decision') not in ('AUTO', 'HITL'):
            malformed += 1
            continue
        identity = row['event_id']
        if identity not in expected:
            unexpected.add(identity)
            continue
        if identity in valid:
            duplicate_ids.add(identity)
            fields = ('routing_decision', 'risk_tier', 'recommended_actions')
            if any(valid[identity].get(k) != row.get(k) for k in fields):
                conflicts.add(identity)
        else:
            valid[identity] = row
    # A conflicting pair has no uniquely scoreable decision; do not silently select the last.
    for identity in conflicts:
        valid.pop(identity)
    scoreable = {i: label for i, label in truth.items() if not label.get('ambiguous', False)}
    unsafe = {i for i, label in scoreable.items() if label['safe_to_auto'] is False}
    eligible = {i for i, label in scoreable.items() if label['safe_to_auto'] is True and label['expected_route'] == 'AUTO'}
    correct_route = sum(valid.get(i, {}).get('routing_decision') == label['expected_route'] for i, label in scoreable.items())
    correct_risk = sum(valid.get(i, {}).get('risk_tier') == label['expected_risk'] for i, label in scoreable.items())
    auto = {i for i, row in valid.items() if row['routing_decision'] == 'AUTO'}
    hitl = set(valid) - auto
    coverage, prohibited, acceptable_selected, selected = [], 0, 0, 0
    for i, label in scoreable.items():
        actions = valid.get(i, {}).get('recommended_actions', [])
        chosen = {a for a in actions if isinstance(a, str)} if isinstance(actions, list) else set()
        acceptable = set(label['acceptable_actions'])
        if acceptable:
            coverage.append(len(chosen & acceptable) / len(acceptable))
        prohibited += len(chosen & set(label.get('prohibited_actions', [])))
        acceptable_selected += len(chosen & acceptable)
        selected += len(chosen)
    feedback_ids, feedback_duplicates, feedback_errors = set(), 0, 0
    for record in feedback:
        if not isinstance(record, dict):
            feedback_errors += 1
            continue
        if record.get('status') in ('duplicate', 'conflicting_duplicate'):
            feedback_duplicates += 1
            continue
        if record.get('status') != 'accepted' or record.get('event_id') not in valid:
            feedback_errors += 1
            continue
        identity = record['event_id']
        outcome = record.get('outcome_type', '')
        if outcome not in ('AUTO_EXECUTE_SUCCESS', 'AUTO_EXECUTE_FAILURE', 'HITL_APPROVED', 'HITL_REJECTED', 'HITL_MODIFIED') or (identity in auto) != outcome.startswith('AUTO_'):
            feedback_errors += 1
            continue
        if identity in feedback_ids:
            feedback_duplicates += 1
        feedback_ids.add(identity)
    feedback_expected = auto | (hitl if expect_hitl_feedback else set())
    return {
        'expected_incidents': len(expected), 'completion': ratio(len(valid), len(expected)),
        'missing_decisions': sorted(expected - set(valid)), 'duplicate_decision_ids': sorted(duplicate_ids),
        'conflicting_decision_ids': sorted(conflicts), 'unexpected_decision_ids': sorted(unexpected),
        'malformed_decisions': malformed,
        'label_coverage': {'labeled': len(truth), 'scoreable': len(scoreable), 'ambiguous': len(truth) - len(scoreable), 'unlabeled': len(expected - set(truth))},
        'route_accuracy': ratio(correct_route, len(scoreable)), 'risk_accuracy': ratio(correct_risk, len(scoreable)),
        'far': ratio(len(auto & unsafe), len(unsafe)), 'fer': ratio(len(hitl & eligible), len(eligible)),
        'action_validity': ratio(sum(validate_actions(row.get('recommended_actions')) for row in valid.values()), len(valid)),
        'acceptable_action_coverage': {'status': 'computed' if coverage else 'not computable', 'value': sum(coverage) / len(coverage) if coverage else None, 'incidents': len(coverage), 'definition': 'macro mean |selected intersect acceptable| / |acceptable|; alternatives, not required-action completion'},
        'acceptable_selected_action_fraction': ratio(acceptable_selected, selected), 'prohibited_action_count': prohibited,
        'workload': {'AUTO': len(auto), 'HITL': len(hitl), 'auto_fraction_of_decisions': ratio(len(auto), len(valid)), 'hitl_fraction_of_decisions': ratio(len(hitl), len(valid))},
        'controller_latency_seconds': distribution(row.get('processing_seconds') for row in valid.values()),
        'boundary_to_decision_seconds': distribution(row.get('boundary_to_decision_seconds') for row in valid.values()),
        'feedback_completion': ratio(len(feedback_ids & feedback_expected), len(feedback_expected)),
        'feedback_duplicates': feedback_duplicates, 'feedback_errors': feedback_errors,
        'hitl_feedback_required': expect_hitl_feedback,
    }


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--decisions', type=Path, required=True, help='Canonical confirmed decision JSONL')
    parser.add_argument('--labels', type=Path)
    parser.add_argument('--feedback', type=Path)
    parser.add_argument('--expect-hitl-feedback', action='store_true')
    args = parser.parse_args()
    records, _ = load_capture(args.capture, args.manifest)
    result = analyze([r['event_id'] for r in records], read_jsonl(args.decisions),
                     read_jsonl(args.labels) if args.labels else [], read_jsonl(args.feedback) if args.feedback else [], args.expect_hitl_feedback)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
