"""HITL Dashboard Views."""
import json
import sys
import os

# Add the layer3 directory to sys.path
sys.path.insert(0, "/home/spectre/fyp-pipeline/layer3")

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.utils import timezone
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from .models import HitlIncident
from .metrics import (
    HITL_APPROVED,
    HITL_MODIFIED,
    HITL_REJECTED,
    HITL_REGISTRY,
    observe_human_decision_latency,
)
from rabbitmq.connection import publish
from sqlite_logger.logger import write_decision


def metrics_view(request):
    """Expose the Django HITL process Prometheus registry for scraping."""
    return HttpResponse(
        generate_latest(HITL_REGISTRY), content_type=CONTENT_TYPE_LATEST
    )


def _persist_human_decision(incident, status, counter):
    """Persist one terminal transition before recording its metrics."""
    decided_at = timezone.now()
    updated = HitlIncident.objects.filter(
        pk=incident.pk,
        status="PENDING",
    ).update(status=status, decided_at=decided_at)
    if not updated:
        return False
    incident.status = status
    incident.decided_at = decided_at
    observe_human_decision_latency(incident.arrived_at, decided_at)
    counter.inc()
    return True

def queue_view(request):
    incidents = HitlIncident.objects.filter(status="PENDING").order_by("arrived_at")
    return render(request, "hitl/queue.html", {"incidents": incidents})

def incident_detail(request, incident_id):
    incident = HitlIncident.objects.get(id=incident_id, status="PENDING")
    payload = json.loads(incident.payload_json)
    return render(request, "hitl/detail.html", {
        "incident": incident,
        "payload": payload,
    })

def _build_decision(payload, decision_type, notes, final_actions):
    chain = payload.get("full_reasoning_chain", {})
    triage = chain.get("triage_result", {})
    strategy = chain.get("strategy_result", {})
    llm = strategy.get("llm_response", {})
    ev = triage.get("original_event", {})
    return {
        "event_id": payload.get("event_id", ""),
        "decision_type": decision_type,
        "operator_notes": notes,
        "anomaly_type": triage.get("anomaly_type", ""),
        "severity": triage.get("severity", ""),
        "affected_component": ev.get("affected_component", ""),
        "node": ev.get("node", ""),
        "routing_reason": payload.get("routing_reason", ""),
        "risk_tier_from_llm": llm.get("risk_tier", ""),
        "confidence_from_llm": llm.get("confidence", 0),
        "time_in_queue_seconds": 0.0,
        "original_actions": llm.get("recommended_actions", []),
        "final_actions": final_actions,
        "auto_execute_outcome": None,
    }

def _publish_outcome(payload, outcome_type, actions, notes):
    outcome = {
        "event_id": payload.get("event_id"),
        "outcome_type": outcome_type,
        "actual_actions_taken": actions,
        "operator_notes": notes,
        "resolution_time_ms": 0,
        "full_policy_result": payload,
    }
    publish("outcome.feedback", json.dumps(outcome))

def approve(request, incident_id):
    incident = HitlIncident.objects.get(id=incident_id, status="PENDING")
    payload = json.loads(incident.payload_json)
    actions = payload.get("full_reasoning_chain", {}).get("strategy_result", {}).get("llm_response", {}).get("recommended_actions", [])
    write_decision(_build_decision(payload, "APPROVE", "Approved by operator", actions))
    _publish_outcome(payload, "HITL_APPROVED", actions, "Approved")
    _persist_human_decision(incident, "APPROVED", HITL_APPROVED)
    return redirect("queue")

def reject(request, incident_id):
    incident = HitlIncident.objects.get(id=incident_id, status="PENDING")
    payload = json.loads(incident.payload_json)
    write_decision(_build_decision(payload, "REJECT", "Rejected by operator", []))
    _publish_outcome(payload, "HITL_REJECTED", [], "Rejected")
    _persist_human_decision(incident, "REJECTED", HITL_REJECTED)
    return redirect("queue")

def modify_form(request, incident_id):
    """Show a form to edit the recommended actions."""
    incident = HitlIncident.objects.get(id=incident_id, status="PENDING")
    payload = json.loads(incident.payload_json)
    actions = payload.get("full_reasoning_chain", {}).get("strategy_result", {}).get("llm_response", {}).get("recommended_actions", [])
    return render(request, "hitl/modify.html", {
        "incident": incident,
        "actions": actions,
    })

def modify_submit(request, incident_id):
    """Process the modified actions form."""
    incident = HitlIncident.objects.get(id=incident_id, status="PENDING")
    payload = json.loads(incident.payload_json)

    if request.method == "POST":
        # Get edited actions from the form
        action1 = request.POST.get("action1", "").strip()
        action2 = request.POST.get("action2", "").strip()
        action3 = request.POST.get("action3", "").strip()
        final_actions = [a for a in [action1, action2, action3] if a]
        notes = request.POST.get("operator_notes", "Modified by operator").strip()

        #1. Write to SQLite (always succeeds locally)
        write_decision(_build_decision(payload, "MODIFY", notes, final_actions))

        # 2. Persist the authoritative action before the best-effort feedback publish.
        _persist_human_decision(incident, "MODIFIED", HITL_MODIFIED)

        # 3. Try to publish outcome.feedback (may fail if Node 1 is offline — status already saved)
        try:
            _publish_outcome(payload, "HITL_MODIFIED", final_actions, notes)
        except Exception as e:
            # Log the failure, but don't fail the operation
            print(f"Warning: Could not publish outcome.feedback: {e}")

    return redirect("queue")
