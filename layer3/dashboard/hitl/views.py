"""HITL Dashboard Views."""
import json
import sys
import os

# Add the layer3 directory to sys.path
sys.path.insert(0, "/home/spectre/fyp-pipeline/layer3")

from django.shortcuts import render, redirect
from .models import HitlIncident
from rabbitmq.connection import publish
from sqlite_logger.logger import write_decision

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
    incident.status = "APPROVED"
    incident.save()
    return redirect("queue")

def reject(request, incident_id):
    incident = HitlIncident.objects.get(id=incident_id, status="PENDING")
    payload = json.loads(incident.payload_json)
    write_decision(_build_decision(payload, "REJECT", "Rejected by operator", []))
    _publish_outcome(payload, "HITL_REJECTED", [], "Rejected")
    incident.status = "REJECTED"
    incident.save()
    return redirect("queue")
