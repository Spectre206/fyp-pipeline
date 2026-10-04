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
            setattr(self, name, Counter('fyp_threshold_' + name + '_total', name.replace('_', ' '), labels, registry=self.registry))
        buckets = (.0001, .0005, .001, .005, .01, .05, .1, .5, 1, 5, 30, 300, 1800, 7200, 14400)
        for name in ('controller_processing', 'publish', 'input_queue_wait', 'boundary_to_decision'):
            setattr(self, name, Histogram('fyp_threshold_' + name + '_seconds', name.replace('_', ' '), buckets=buckets, registry=self.registry))
        self.worker_up = Gauge('fyp_threshold_worker_up', 'Worker consuming state', ('worker',), registry=self.registry)
        for name in ('controller', 'feedback'):
            self.worker_up.labels(name).set(0)
