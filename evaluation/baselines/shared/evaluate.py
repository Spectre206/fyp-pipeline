"""Offline Mode B evaluation of existing Threshold/Single-Agent journal exports."""
import argparse
import base64
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from layer2.evaluation.generate_routing_labels import POLICY_VERSION, routing_label

CONTRACT = 'ethernet-routing-stage-v1'
CONTROLLERS = ('threshold_only', 'single_agent')
OUTCOMES = {'AUTO_EXECUTE_SUCCESS', 'AUTO_EXECUTE_FAILURE',
            'HITL_APPROVED', 'HITL_REJECTED', 'HITL_MODIFIED'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ratio(n, d):
    return dict(status='computed' if d else 'not_computable', numerator=n,
                denominator=d, value=n / d if d else None)


def load_labels(path):
    """Validate the frozen translation; never construct labels from decisions."""
    required = {'event_id', 'ground_truth_label', 'ground_truth_risk_tier',
                'ground_truth_action', 'expected_route', 'safe_to_auto'}
    with Path(path).open(newline='', encoding='utf-8') as source:
        reader = csv.DictReader(source, strict=True)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not required <= set(fields):
            raise ValueError('Missing or duplicate label columns')
        result = {}
        for row in reader:
            identity = row.get('event_id')
            if (None in row or any(v is None for v in row.values()) or
                    not isinstance(identity, str) or not identity.strip() or
                    identity != identity.strip() or identity in result):
                raise ValueError(f'Invalid/duplicate label at CSV line {reader.line_num}')
            risk = row['ground_truth_risk_tier']
            if risk not in ({'N/A','LOW','HIGH'} if row['ground_truth_label']=='NORMAL' else {'LOW','HIGH'}):
                raise ValueError(f'Invalid source risk for {identity}')
            if row['ground_truth_action'] != row['ground_truth_action'].strip():
                raise ValueError(f'Invalid source action for {identity}')
            if (row['expected_route'], row['safe_to_auto']) != routing_label(row):
                raise ValueError(f'Routing-label-policy-v2 mismatch for {identity}')
            result[identity] = row
        if not result:
            raise ValueError('Empty labels')
        return result


def read_records(path):
    """Retain line references and malformed counts rather than silently dropping lines."""
    rows, malformed = [], []
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: '+key)
            result[key] = value
        return result
    def reject_constant(value):
        raise ValueError(f'Nonfinite JSON: {value}')
    with Path(path).open(encoding='utf-8') as source:
        for line, text in enumerate(source, 1):
            if not text.strip():
                continue
            try:
                row = json.loads(text, parse_constant=reject_constant, object_pairs_hook=unique_keys)
                if not isinstance(row, dict):
                    raise ValueError('not an object')
                rows.append((line, row))
            except (ValueError, TypeError):
                malformed.append(line)
    return rows, malformed


def normalize(row, controller, run_id, reference):
    """Both existing exports share these fields; retain SA validation metadata."""
    if row.get('controller') != controller or row.get('run_id') != run_id:
        raise ValueError('wrong_identity')
    identity, route = row.get('event_id'), row.get('routing_decision')
    if not isinstance(identity, str) or not identity.strip() or identity != identity.strip():
        raise ValueError('malformed')
    if route not in ('AUTO', 'HITL'):
        raise ValueError('malformed')
    if row.get('final_routing_decision', route) != route:
        raise ValueError('malformed')
    risk = row.get('risk_tier')
    if risk not in (None, 'LOW', 'HIGH'):
        raise ValueError('malformed')
    return dict(event_id=identity, actual_route=route, reported_risk=risk,
                decision_timestamp=row.get('publish_confirmed_at') or row.get('decision_ready_at'),
                controller_name=controller, run_id=run_id, source_record=reference,
                validation_metadata={k: row[k] for k in
                    ('validation_status', 'fallback_applied', 'attempts', 'raw_routing_decision') if k in row})


def evaluate(labels, decisions_path, feedback_path, controller, run_id,
             deliveries_path=None, expect_hitl_feedback=False):
    if controller not in CONTROLLERS or not run_id:
        raise ValueError('Explicit supported controller and run ID required')
    rows, bad = read_records(decisions_path)
    integrity = dict(malformed_decision_lines=list(bad), wrong_identity_decision_lines=[],
                     unexpected_decision_ids=[], duplicate_decision_ids=[], conflicting_decision_ids=[])
    candidates, signatures, duplicates, conflicts = {}, {}, set(), set()
    for line, raw in rows:
        try:
            item = normalize(raw, controller, run_id, dict(path=str(decisions_path), line=line))
        except ValueError as exc:
            key = 'wrong_identity_decision_lines' if str(exc) == 'wrong_identity' else 'malformed_decision_lines'
            integrity[key].append(line)
            continue
        identity = item['event_id']
        if identity not in labels:
            integrity['unexpected_decision_ids'].append(identity)
            continue
        # Timestamp/replay differences do not change a decision's semantics.
        signature = json.dumps({k: raw.get(k) for k in
            ('routing_decision', 'risk_tier', 'recommended_actions', 'fallback_applied',
             'validation_status', 'raw_routing_decision')}, sort_keys=True)
        if identity in candidates:
            duplicates.add(identity)
            if signature != signatures[identity]:
                conflicts.add(identity)
        else:
            candidates[identity], signatures[identity] = item, signature
    valid = {k: v for k, v in candidates.items() if k not in conflicts}
    integrity['duplicate_decision_ids'] = sorted(duplicates)
    integrity['conflicting_decision_ids'] = sorted(conflicts)
    integrity['unexpected_decision_ids'] = sorted(set(integrity['unexpected_decision_ids']))
    corpus = set(labels)
    normal = {i for i, r in labels.items() if r['ground_truth_label'] == 'NORMAL'}
    eligible = {i for i, r in labels.items() if r['expected_route'] == 'AUTO'} - normal
    unsafe = {i for i, r in labels.items() if r['safe_to_auto'] == 'false'} - normal
    auto = {i for i, r in valid.items() if r['actual_route'] == 'AUTO'}
    hitl = set(valid) - auto
    expected_feedback = auto | (hitl if expect_hitl_feedback else set())
    feedback_rows, bad_feedback = read_records(feedback_path) if feedback_path else ([], [])
    feedback_issues = Counter()
    accepted, feedback_signatures, feedback_conflicts = set(), {}, set()
    for line, row in feedback_rows:
        if row.get('run_id') != run_id or row.get('controller') != controller:
            feedback_issues['wrong_identity'] += 1
            continue
        payload = row.get('payload')
        if not isinstance(payload, dict) or row.get('status') not in ('accepted', 'duplicate', 'conflicting_duplicate'):
            feedback_issues['rejected_' + str(row.get('status', 'missing_status'))] += 1
            continue
        identity, outcome = row.get('event_id'), row.get('outcome_type')
        envelope = payload.get('full_policy_result')
        if (not isinstance(identity, str) or not isinstance(outcome, str) or
                not isinstance(envelope, dict) or payload.get('event_id') != identity or
                payload.get('outcome_type') != outcome or outcome not in OUTCOMES or
                envelope.get('event_id') != identity or envelope.get('run_id') != run_id or
                envelope.get('controller') != controller):
            feedback_issues['malformed'] += 1
            continue
        if identity not in valid:
            feedback_issues['unexpected_id'] += 1
            continue
        if (identity in auto) != outcome.startswith('AUTO_'):
            feedback_issues['route_mismatch'] += 1
            continue
        signature = json.dumps(payload, sort_keys=True)
        if identity in feedback_signatures:
            feedback_issues['duplicate'] += 1
            if signature != feedback_signatures[identity]:
                feedback_conflicts.add(identity)
        else:
            feedback_signatures[identity] = signature
        if row['status'] == 'conflicting_duplicate':
            feedback_conflicts.add(identity)
        if row['status'] == 'accepted':
            accepted.add(identity)
    accepted -= feedback_conflicts
    integrity.update(malformed_feedback_lines=bad_feedback,
                     feedback_issues=dict(sorted(feedback_issues.items())),
                     conflicting_feedback_ids=sorted(feedback_conflicts),
                     missing_feedback_ids=sorted(expected_feedback - accepted),
                     corpus_without_scoreable_decision=sorted(corpus - set(valid)),
                     expected_auto_without_scoreable_decision=sorted(eligible - set(valid)))
    reached, delivery_bad, delivery_unidentified = set(), [], 0
    if deliveries_path:
        deliveries, delivery_bad = read_records(deliveries_path)
        for line, row in deliveries:
            try:
                payload = json.loads(base64.b64decode(row['body_base64'], validate=True))
                identity = payload.get('event_id')
                if not isinstance(identity, str) or not identity:
                    raise ValueError('missing ID')
                reached.add(identity)
            except (ValueError, TypeError, KeyError, AttributeError):
                delivery_unidentified += 1
    integrity.update(malformed_delivery_lines=delivery_bad, unidentified_deliveries=delivery_unidentified,
                     unexpected_delivery_ids=sorted(reached - corpus),
                     received_without_decision=sorted((reached & corpus) - set(valid)) if deliveries_path else None)
    risk_ids = {i for i, r in valid.items() if i not in normal and r['reported_risk'] in ('LOW', 'HIGH')
                and labels[i]['ground_truth_risk_tier'] in ('LOW', 'HIGH')}
    summary = dict(contract=CONTRACT, routing_policy=POLICY_VERSION, controller=controller, run_id=run_id,
        counts=dict(decision_records=len(rows), corpus=len(corpus), anomalies=len(corpus-normal), normal=len(normal),
                    received_ids=len(reached & corpus) if deliveries_path else None,
                    routing_decisions=len(valid), actual_auto=len(auto), actual_hitl=len(hitl),
                    normal_decisions=len(set(valid)&normal), feedback_ids=len(accepted),
                    expected_auto_total=len(eligible), expected_auto_with_decision=len(eligible&set(valid)),
                    expected_auto_without_decision=len(eligible-set(valid))),
        far=ratio(len(auto & unsafe), len(auto-normal)),
        fer=ratio(len(hitl & eligible), len(eligible & set(valid))),
        expected_auto_controller_coverage=ratio(len(eligible & set(valid)), len(eligible)),
        expected_auto_missing_before_routing=ratio(len(eligible-set(valid)), len(eligible)),
        risk_accuracy=ratio(sum(valid[i]['reported_risk']==labels[i]['ground_truth_risk_tier'] for i in risk_ids),len(risk_ids)),
        feedback_completion=ratio(len(expected_feedback & accepted),len(expected_feedback)),
        hitl_feedback_required=expect_hitl_feedback,
        corpus_decision_coverage=ratio(len(valid),len(corpus)))
    # Corpus absence is coverage, not proof of failed delivery: calibration and suppression apply.
    blocking = any(integrity[k] for k in ('malformed_decision_lines','wrong_identity_decision_lines',
        'unexpected_decision_ids','duplicate_decision_ids','conflicting_decision_ids','malformed_feedback_lines',
        'feedback_issues','conflicting_feedback_ids','missing_feedback_ids','malformed_delivery_lines',
        'unidentified_deliveries','unexpected_delivery_ids','received_without_decision'))
    summary['integrity_status'] = 'review_required' if blocking else 'no_detected_record_errors'
    summary['completion_claim'] = 'offline records only; transport, upstream reconciliation and cutoff evidence required'
    return summary, [valid[i] for i in sorted(valid)], integrity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('labels', 'decisions', 'feedback', 'deliveries'):
        parser.add_argument('--'+name, type=Path, required=name in ('labels','decisions'))
    for name in ('attempts', 'quarantine', 'failures'):
        parser.add_argument('--'+name, type=Path, help='Optional journal export, retained as integrity evidence')
    parser.add_argument('--controller', choices=CONTROLLERS, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--output', type=Path, required=True, help='New analysis directory; never overwritten')
    parser.add_argument('--expect-hitl-feedback', action='store_true')
    args = parser.parse_args()
    labels = load_labels(args.labels)
    summary, decisions, integrity = evaluate(labels,args.decisions,args.feedback,args.controller,args.run_id,
                                              args.deliveries,args.expect_hitl_feedback)
    for name in ('attempts', 'quarantine', 'failures'):
        path = getattr(args, name)
        if path:
            records, malformed = read_records(path)
            integrity[name] = dict(records=len(records), malformed_lines=malformed)
            if malformed or (name != 'attempts' and records):
                summary['integrity_status'] = 'review_required'
    inputs = {name: {'path':str(getattr(args,name)), 'sha256':digest(getattr(args,name))}
              for name in ('labels','decisions','feedback','deliveries','attempts','quarantine','failures') if getattr(args,name)}
    args.output.mkdir(parents=True,exist_ok=False)
    def write(name, value):
        (args.output/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n')
    write('evaluation_summary.json',summary)
    write('integrity_report.json',integrity)
    (args.output/'normalized_decisions.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in decisions))
    # Independent cross-tab reconstruction from the normalized ID join.
    table = Counter((labels[r['event_id']]['expected_route'],r['actual_route']) for r in decisions
                    if labels[r['event_id']]['ground_truth_label'] != 'NORMAL')
    far_d = table['AUTO','AUTO'] + table['HITL','AUTO']
    fer_d = table['AUTO','AUTO'] + table['AUTO','HITL']
    eligible_total = sum(row['expected_route']=='AUTO' for row in labels.values())
    verified = (summary['far']==ratio(table['HITL','AUTO'],far_d)
                and summary['fer']==ratio(table['AUTO','HITL'],fer_d)
                and summary['expected_auto_controller_coverage']==ratio(fer_d,eligible_total)
                and summary['expected_auto_missing_before_routing']==ratio(eligible_total-fer_d,eligible_total))
    if not verified:
        raise ValueError('Independent cross-tab verification failed')
    write('verification_report.json',dict(cross_tab=[dict(expected=k[0],actual=k[1],count=v)
        for k,v in sorted(table.items())],far_fer_coverage_agreement=verified))
    write('manifest.json',dict(contract=CONTRACT,inputs=inputs,
        evaluator_sha256=digest(__file__), policy_generator_sha256=digest(Path(__file__).resolve().parents[3]/'layer2/evaluation/generate_routing_labels.py'),
        outputs={p.name:digest(p) for p in sorted(args.output.iterdir()) if p.is_file()}))
    print(json.dumps(summary,indent=2,sort_keys=True))


if __name__ == '__main__':
    main()
