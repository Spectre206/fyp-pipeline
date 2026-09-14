"""Prometheus instrumentation for authoritative HITL decisions."""
from django.utils import timezone
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

HITL_REGISTRY = CollectorRegistry()

HITL_APPROVED = Counter(
    "fyp_hitl_approved_total",
    "Authoritative HITL approvals",
    registry=HITL_REGISTRY,
)
HITL_REJECTED = Counter(
    "fyp_hitl_rejected_total",
    "Authoritative HITL rejections",
    registry=HITL_REGISTRY,
)
HITL_MODIFIED = Counter(
    "fyp_hitl_modified_total",
    "Authoritative HITL modifications",
    registry=HITL_REGISTRY,
)
HITL_PENDING_INCIDENTS = Gauge(
    "fyp_hitl_pending_incidents",
    "Persisted HITL incidents currently awaiting an authoritative human decision",
    registry=HITL_REGISTRY,
)
HUMAN_DECISION_LATENCY = Histogram(
    "fyp_human_decision_latency_seconds",
    "HITL queue entry to authoritative human decision latency",
    buckets=(5, 10, 30, 60, 120, 300, 600, 900, 1800),
    registry=HITL_REGISTRY,
)


def pending_incident_count():
    """Return the current authoritative pending HITL workload from Django."""
    # Import lazily so this instrumentation remains import-safe while Django
    # initializes its app registry. A scrape queries the database directly,
    # which also reconstructs the gauge correctly after a process restart.
    from .models import HitlIncident

    return HitlIncident.objects.filter(status="PENDING").count()


HITL_PENDING_INCIDENTS.set_function(pending_incident_count)


def observe_human_decision_latency(arrived_at, decided_at):
    """Observe a valid human-decision interval without fabricating a value."""
    if not arrived_at or not decided_at:
        return False
    if not timezone.is_aware(arrived_at) or not timezone.is_aware(decided_at):
        return False
    latency_seconds = (decided_at - arrived_at).total_seconds()
    if latency_seconds < 0:
        return False
    HUMAN_DECISION_LATENCY.observe(latency_seconds)
    return True
