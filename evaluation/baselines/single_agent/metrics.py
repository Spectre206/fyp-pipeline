"""Bounded labels and private registry; importing does not bind any port."""
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram


class Metrics:
    def __init__(self):
        self.registry = CollectorRegistry()
        counters = {
            'incident_deliveries': (), 'incidents_received': ('origin',),
            'malformed_input': ('reason',), 'duplicate_incidents': (),
            'decisions': ('route', 'reason', 'risk'), 'action_sets': ('status',),
            'processing_failures': ('stage',), 'feedback_received': ('outcome',),
            'feedback_duplicates': (), 'feedback_errors': ('reason',),
        }
        for name, labels in counters.items():
            setattr(self, name, Counter('fyp_single_agent_' + name + '_total', name.replace('_', ' '), labels, registry=self.registry))
        buckets = (.0001, .0005, .001, .005, .01, .05, .1, .5, 1, 5, 30, 300, 1800, 7200, 14400)
        for name in ('controller_processing', 'publish', 'input_queue_wait', 'boundary_to_decision'):
            setattr(self, name, Histogram('fyp_single_agent_' + name + '_seconds', name.replace('_', ' '), buckets=buckets, registry=self.registry))
        self.model_calls = Counter('fyp_single_agent_model_calls_total', 'Model attempts', ['attempt'], registry=self.registry)
        self.model_timeouts = Counter('fyp_single_agent_model_timeouts_total', 'Model timeouts', registry=self.registry)
        self.model_failures = Counter('fyp_single_agent_model_failures_total', 'Model failures', ['category'], registry=self.registry)
        self.retries = Counter('fyp_single_agent_retries_total', 'Eligible regeneration', ['reason'], registry=self.registry)
        self.output_valid = Counter('fyp_single_agent_output_valid_total', 'Valid attempt output', ['attempt'], registry=self.registry)
        self.output_invalid = Counter('fyp_single_agent_output_invalid_total', 'Invalid output', ['attempt', 'category'], registry=self.registry)
        self.schema_valid_output = Counter('fyp_single_agent_schema_valid_output_total', 'Contract-valid output', ['attempt'], registry=self.registry)
        self.model_generation = Histogram('fyp_single_agent_model_generation_seconds', 'HTTP attempt duration including failures', ['attempt', 'outcome'], buckets=(.1, 1, 5, 10, 20, 35, 60, 120), registry=self.registry)
        self.model_eval_tokens = Counter('fyp_single_agent_model_eval_tokens_total', 'Reported generated tokens', registry=self.registry)
        self.model_eval_seconds = Counter('fyp_single_agent_model_eval_seconds_total', 'Reported evaluation duration', registry=self.registry)
        self.model_tokens_per_second = Gauge('fyp_single_agent_model_tokens_per_second', 'Last available tokens per second; NaN when unavailable', registry=self.registry)
        self.model_tokens_per_second.set(float('nan'))
        self.worker_up = Gauge('fyp_single_agent_worker_up', 'Worker consuming state', ('worker',), registry=self.registry)
        for name in ('controller', 'feedback'):
            self.worker_up.labels(name).set(0)
