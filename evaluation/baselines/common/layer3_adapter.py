"""Serialization aliases for shared Layer 3; no fabricated agent stages."""
from copy import deepcopy


def envelope(decision):
    if decision['routing_decision'] not in ('AUTO', 'HITL'):
        raise ValueError('No dispatchable decision')
    return {
        'event_id': decision['event_id'], 'controller': decision['controller'],
        'run_id': decision['run_id'], 'policy_timestamp': decision['decision_ready_at'],
        'routing_decision': decision['routing_decision'], 'routing_reason': decision['routing_reason'],
        'controller_decision_latency_ms': decision['processing_seconds'] * 1000,
        'fallback_applied': decision.get('fallback_applied', False),
        'validation_status': decision.get('validation_status'),
        'full_reasoning_chain': {
            'triage_result': {'anomaly_type': decision['anomaly_type'], 'severity': decision['severity'],
                             'original_event': deepcopy(decision['original_event'])},
            'strategy_result': {'llm_response': {
                'recommended_actions': list(decision['recommended_actions']),
                'risk_tier': decision['risk_tier'], 'confidence': decision.get('confidence'),
                'reasoning': decision['rationale'],
            }},
        },
    }
