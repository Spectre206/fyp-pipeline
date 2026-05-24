# layer1/seg/event_templates.py
# Per-category metric profiles and ground-truth mappings.
# EventTemplateFactory is called by seg.py to build each event dict.

import uuid
from datetime import datetime, timezone

# ── Component lists per anomaly type ──────────────────────────────────
COMPONENTS = {
    "cpu_memory_spike":   [
        "RabbitMQ consumer", "Isolation Forest process",
        "Feature Store",     "ADM runner", "SEG process"
    ],
    "error_rate_surge":   [
        "HTTP gateway", "REST API endpoint",
        "Django HITL view", "metrics collector"
    ],
    "throughput_drop":    [
        "RabbitMQ producer", "anomaly.detected consumer",
        "pipeline ingestion worker"
    ],
    "auth_failure_flood": [
        "SSH daemon", "FTP proxy",
        "API auth middleware", "VPN gateway"
    ],
    "schema_drift":       [
        "SEG output", "external data source",
        "Loghub replay adapter"
    ],
    "NORMAL":             [
        "RabbitMQ consumer", "HTTP gateway",
        "Feature Store", "ADM runner"
    ],
}

NODES = ["stream-node", "ai-brain-node", "gateway-node"]

# ── Metric value ranges ────────────────────────────────────────────────
NORMAL_METRICS = {
    "cpu_percent":           (10.0, 55.0),
    "mem_percent":           (20.0, 65.0),
    "messages_per_second":   (80.0, 200.0),
    "error_rate_percent":    (0.0,  2.0),
    "auth_failures_per_min": (0.0,  3.0),
}

ANOMALY_METRICS = {
    "cpu_memory_spike": {
        "MEDIUM":   {"cpu_percent": (70.0, 85.0),  "mem_percent": (70.0, 90.0)},
        "HIGH":     {"cpu_percent": (85.0, 95.0),  "mem_percent": (90.0, 97.0)},
        "CRITICAL": {"cpu_percent": (95.0, 100.0), "mem_percent": (97.0, 100.0)},
    },
    "error_rate_surge": {
        "MEDIUM":   {"error_rate_percent": (10.0, 18.0), "request_count_per_second": (50.0, 150.0)},
        "HIGH":     {"error_rate_percent": (18.0, 30.0), "request_count_per_second": (50.0, 150.0)},
        "CRITICAL": {"error_rate_percent": (30.0, 60.0), "request_count_per_second": (10.0,  50.0)},
    },
    "throughput_drop": {
        "MEDIUM":   {"messages_per_second": (20.0, 40.0)},
        "HIGH":     {"messages_per_second": (2.0,  20.0)},
        "CRITICAL": {"messages_per_second": (0.0,   2.0)},
    },
    "auth_failure_flood": {
        "MEDIUM":   {"auth_failures_per_min": (20.0,  40.0), "src_bytes": (100.0,  500.0)},
        "HIGH":     {"auth_failures_per_min": (40.0,  100.0),"src_bytes": (200.0,  800.0)},
        "CRITICAL": {"auth_failures_per_min": (100.0, 300.0),"src_bytes": (500.0, 2000.0)},
    },
}

# ── Ground truth mappings ──────────────────────────────────────────────
RISK_TIER_MAP = {
    ("cpu_memory_spike",   "MEDIUM"):   "LOW",
    ("cpu_memory_spike",   "HIGH"):     "LOW",
    ("cpu_memory_spike",   "CRITICAL"): "HIGH",
    ("error_rate_surge",   "MEDIUM"):   "LOW",
    ("error_rate_surge",   "HIGH"):     "HIGH",
    ("error_rate_surge",   "CRITICAL"): "HIGH",
    ("throughput_drop",    "MEDIUM"):   "LOW",
    ("throughput_drop",    "HIGH"):     "HIGH",
    ("throughput_drop",    "CRITICAL"): "HIGH",
    ("auth_failure_flood", "MEDIUM"):   "HIGH",
    ("auth_failure_flood", "HIGH"):     "HIGH",
    ("auth_failure_flood", "CRITICAL"): "HIGH",
    ("schema_drift",       "MEDIUM"):   "LOW",
    ("schema_drift",       "HIGH"):     "HIGH",
}

GROUND_TRUTH_ACTIONS = {
    "LOW":  "AUTO_RESTART_CONSUMER",
    "HIGH": "ESCALATE_TO_HITL",
    "N/A":  None,
}

SCHEMA_DRIFT_SEVERITY = {
    "missing_field":  "MEDIUM",
    "type_mutation":  "HIGH",
    "value_shift":    "MEDIUM",
}


class EventTemplateFactory:
    """
    Builds complete event dicts including ground_truth fields.
    Called by SyntheticEventGenerator for each event in the corpus.
    Ground truth is stripped by save_corpus() before writing to JSONL.
    """

    def __init__(self, rng):
        self.rng = rng

    def _sample(self, lo, hi):
        return round(float(self.rng.uniform(lo, hi)), 4)

    def _component(self, atype):
        return str(self.rng.choice(COMPONENTS[atype]))

    def _node(self):
        return str(self.rng.choice(NODES))

    # ── Normal event ──────────────────────────────────────────────────
    def normal(self, node=None) -> dict:
        node = node or self._node()
        return {
            "event_id":               str(uuid.uuid4()),
            "timestamp":              datetime.now(timezone.utc).isoformat(),
            "anomaly_type":           "NORMAL",
            "severity":               "N/A",
            "affected_component":     self._component("NORMAL"),
            "node":                   node,
            "metric_values": {
                k: self._sample(lo, hi)
                for k, (lo, hi) in NORMAL_METRICS.items()
            },
            "context":                "Healthy baseline traffic",
            "ground_truth_label":     "NORMAL",
            "ground_truth_risk_tier": "N/A",
            "ground_truth_action":    None,
        }

    # ── Anomaly event ─────────────────────────────────────────────────
    def anomaly(self, atype: str, severity: str, node=None) -> dict:
        node    = node or self._node()
        ranges  = ANOMALY_METRICS.get(atype, {}).get(severity, {})
        metrics = {k: self._sample(lo, hi) for k, (lo, hi) in ranges.items()}
        risk    = RISK_TIER_MAP.get((atype, severity), "HIGH")

        context_map = {
            "cpu_memory_spike":   f"CPU/memory spike on {self._component(atype)} — {severity}",
            "error_rate_surge":   f"5xx error rate surge on {self._component(atype)}",
            "throughput_drop":    f"Throughput drop / silent crash on {self._component(atype)}",
            "auth_failure_flood": f"Auth failure flood detected on {self._component(atype)}",
        }

        return {
            "event_id":               str(uuid.uuid4()),
            "timestamp":              datetime.now(timezone.utc).isoformat(),
            "anomaly_type":           atype,
            "severity":               severity,
            "affected_component":     self._component(atype),
            "node":                   node,
            "metric_values":          metrics,
            "context":                context_map.get(atype, f"{atype} anomaly"),
            "ground_truth_label":     "ANOMALY",
            "ground_truth_risk_tier": risk,
            "ground_truth_action":    GROUND_TRUTH_ACTIONS[risk],
        }

    # ── Schema drift event ────────────────────────────────────────────
    def schema_drift(self, subtype: str, node=None) -> dict:
        node     = node or self._node()
        severity = SCHEMA_DRIFT_SEVERITY[subtype]
        risk     = RISK_TIER_MAP.get(("schema_drift", severity), "LOW")

        base = {
            "event_id":               str(uuid.uuid4()),
            "timestamp":              datetime.now(timezone.utc).isoformat(),
            "anomaly_type":           "schema_drift",
            "severity":               severity,
            "affected_component":     self._component("schema_drift"),
            "node":                   node,
            "metric_values":          {"validation_error_count": float(self.rng.integers(1, 6))},
            "context":                f"Schema violation: {subtype}",
            "ground_truth_label":     "ANOMALY",
            "ground_truth_risk_tier": risk,
            "ground_truth_action":    GROUND_TRUTH_ACTIONS[risk],
        }

        # Deliberately corrupt the event to simulate the violation type
        if subtype == "missing_field":
            base.pop("severity")          # remove a required field

        elif subtype == "type_mutation":
            base["metric_values"] = "corrupted_string"   # wrong type

        elif subtype == "value_shift":
            # Metric values look valid but distribution is shifted
            base["metric_values"] = {
                "cpu_percent": self._sample(60.0, 99.0),
                "distribution_shift_marker": 1.0,
            }

        return base