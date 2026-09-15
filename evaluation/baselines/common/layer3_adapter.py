"""Legacy keys are serialization aliases, never fabricated agent execution."""
from copy import deepcopy


def envelope(decision):
    if decision['routing_decision'] not in {'AUTO', 'HITL'}:
        raise ValueError('Quarantined input has no Layer 3 envelope')
    raw = deepcopy(decision['original_event'])
    return {
        'event_id': decision['event_id'], 'controller': decision['controller'],
        'run_id': decision['run_id'], 'rules_version': decision['rules_version'],
        'policy_timestamp': decision['decision_ready_at'],
        'controller_decision_latency_ms': decision['processing_seconds'] * 1000,
        'routing_decision': decision['routing_decision'], 'routing_reason': decision['routing_reason'],
        'full_reasoning_chain': {
            'triage_result': {'anomaly_type': decision['anomaly_type'], 'severity': decision['severity'],
                              'response_protocol': decision['routing_reason'], 'original_event': raw},
            'strategy_result': {'llm_response': {
                'risk_tier': decision['risk_tier'], 'confidence': None,
                'recommended_actions': list(decision['recommended_actions']), 'reasoning': decision['rationale'],
            }},
        },
    }
