"""Offline tests for authoritative HITL observability."""
import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase
from django.utils import timezone

from hitl import metrics, views
from hitl.models import HitlIncident


def policy_payload(event_id):
    return {
        "event_id": event_id,
        "full_reasoning_chain": {
            "strategy_result": {
                "llm_response": {"recommended_actions": ["MONITOR_AND_ALERT"] * 3}
            },
        },
    }


class HitlObservabilityTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def incident(self, event_id="event-1"):
        return HitlIncident.objects.create(
            event_id=event_id,
            payload_json=json.dumps(policy_payload(event_id)),
        )

    def test_approve_persists_once_and_emits_feedback(self):
        incident = self.incident()
        approved = MagicMock()
        with patch.object(views, "write_decision"), \
             patch.object(views, "publish") as publish, \
             patch.object(views, "HITL_APPROVED", approved), \
             patch.object(views, "observe_human_decision_latency") as observe:
            response = views.approve(self.factory.post("/"), incident.id)

        incident.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(incident.status, "APPROVED")
        self.assertIsNotNone(incident.decided_at)
        self.assertTrue(timezone.is_aware(incident.decided_at))
        approved.inc.assert_called_once_with()
        observe.assert_called_once_with(incident.arrived_at, incident.decided_at)
        self.assertEqual(publish.call_args.args[0], "outcome.feedback")
        self.assertEqual(json.loads(publish.call_args.args[1])["outcome_type"], "HITL_APPROVED")

    def test_reject_increments_only_rejected_counter(self):
        incident = self.incident()
        approved, rejected, modified = MagicMock(), MagicMock(), MagicMock()
        with patch.object(views, "write_decision"), \
             patch.object(views, "publish"), \
             patch.object(views, "HITL_APPROVED", approved), \
             patch.object(views, "HITL_REJECTED", rejected), \
             patch.object(views, "HITL_MODIFIED", modified):
            views.reject(self.factory.post("/"), incident.id)

        incident.refresh_from_db()
        self.assertEqual(incident.status, "REJECTED")
        rejected.inc.assert_called_once_with()
        approved.inc.assert_not_called()
        modified.inc.assert_not_called()

    def test_modify_increments_only_modified_counter(self):
        incident = self.incident()
        approved, rejected, modified = MagicMock(), MagicMock(), MagicMock()
        request = self.factory.post("/", {"action1": "MONITOR_AND_ALERT"})
        with patch.object(views, "write_decision"), \
             patch.object(views, "publish"), \
             patch.object(views, "HITL_APPROVED", approved), \
             patch.object(views, "HITL_REJECTED", rejected), \
             patch.object(views, "HITL_MODIFIED", modified):
            views.modify_submit(request, incident.id)

        incident.refresh_from_db()
        self.assertEqual(incident.status, "MODIFIED")
        self.assertIsNotNone(incident.decided_at)
        modified.inc.assert_called_once_with()
        approved.inc.assert_not_called()
        rejected.inc.assert_not_called()

    def test_failed_approve_does_not_transition_or_increment(self):
        incident = self.incident()
        approved = MagicMock()
        with patch.object(views, "write_decision"), \
             patch.object(views, "publish", side_effect=RuntimeError("broker unavailable")), \
             patch.object(views, "HITL_APPROVED", approved):
            with self.assertRaises(RuntimeError):
                views.approve(self.factory.post("/"), incident.id)

        incident.refresh_from_db()
        self.assertEqual(incident.status, "PENDING")
        self.assertIsNone(incident.decided_at)
        approved.inc.assert_not_called()

    def test_repeated_terminal_request_does_not_double_count(self):
        incident = self.incident()
        approved = MagicMock()
        with patch.object(views, "write_decision"), \
             patch.object(views, "publish"), \
             patch.object(views, "HITL_APPROVED", approved):
            views.approve(self.factory.post("/"), incident.id)
            with self.assertRaises(HitlIncident.DoesNotExist):
                views.approve(self.factory.post("/"), incident.id)
        approved.inc.assert_called_once_with()

    def test_stale_terminal_transition_does_not_increment(self):
        incident = self.incident()
        stale_copy = HitlIncident.objects.get(pk=incident.pk)
        approved = MagicMock()
        self.assertTrue(views._persist_human_decision(incident, "APPROVED", approved))
        self.assertFalse(views._persist_human_decision(stale_copy, "APPROVED", approved))
        approved.inc.assert_called_once_with()

    def test_latency_observation_uses_authoritative_timestamps_only(self):
        arrived_at = timezone.now() - timedelta(seconds=12)
        decided_at = timezone.now()
        with patch.object(metrics.HUMAN_DECISION_LATENCY, "observe") as observe:
            self.assertTrue(metrics.observe_human_decision_latency(arrived_at, decided_at))
            observe.assert_called_once_with((decided_at - arrived_at).total_seconds())

    def test_missing_or_invalid_latency_does_not_observe(self):
        now = timezone.now()
        with patch.object(metrics.HUMAN_DECISION_LATENCY, "observe") as observe:
            self.assertFalse(metrics.observe_human_decision_latency(None, now))
            self.assertFalse(metrics.observe_human_decision_latency(now, now - timedelta(seconds=1)))
        observe.assert_not_called()

    def test_metrics_endpoint_exposes_hitl_collectors(self):
        response = views.metrics_view(self.factory.get("/metrics"))
        body = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("fyp_hitl_approved_total", body)
        self.assertIn("fyp_hitl_rejected_total", body)
        self.assertIn("fyp_hitl_modified_total", body)
        self.assertIn("fyp_human_decision_latency_seconds", body)
        for boundary in ("5.0", "10.0", "30.0", "60.0", "120.0", "300.0", "600.0", "900.0", "1800.0", "+Inf"):
            self.assertIn(
                f'fyp_human_decision_latency_seconds_bucket{{le="{boundary}"}}',
                body,
            )

    def test_grafana_uses_authoritative_hitl_metrics(self):
        dashboard = Path(__file__).resolve().parents[2] / "grafana" / (
            "FYP_Hybrid_Agentic_Framework_Observability_v3_Node_Naming.json"
        )
        panels = {
            panel.get("title"): panel for panel in json.loads(dashboard.read_text())["panels"]
        }
        decision_queries = "\n".join(
            target["expr"] for target in panels["HUMAN OVERSIGHT — Decisions"]["targets"]
        )
        self.assertIn("fyp_hitl_approved_total", decision_queries)
        self.assertIn("fyp_hitl_rejected_total", decision_queries)
        self.assertIn("fyp_hitl_modified_total", decision_queries)
        self.assertIn(
            'rabbitmq_queue_messages_ready{queue="hitl.queue"}',
            panels["HITL Pending"]["targets"][0]["expr"],
        )
        latency = panels["Human Decision Latency — p50 / p95"]
        latency_queries = "\n".join(target["expr"] for target in latency["targets"])
        self.assertIn("fyp_human_decision_latency_seconds_bucket", latency_queries)
        self.assertIn("sum by (le)", latency_queries)
        self.assertNotIn("MTTA", latency["description"])
        self.assertNotIn("MTTR", latency["description"])

    def test_dashboard_has_final_layer_names_and_non_overlapping_panels(self):
        dashboard = Path(__file__).resolve().parents[2] / "grafana" / (
            "FYP_Hybrid_Agentic_Framework_Observability_v3_Node_Naming.json"
        )
        panels = json.loads(dashboard.read_text())["panels"]
        titles = {panel["title"] for panel in panels}
        self.assertTrue({
            "LAYER 1 — REAL-TIME STATISTICAL DATA PLANE",
            "LAYER 2 — AI CONTROL PLANE",
            "LAYER 3 — EXECUTION, HUMAN OVERSIGHT & OBSERVABILITY LAYER",
            "INFRASTRUCTURE / HARDWARE",
        }.issubset(titles))
        ids = [panel["id"] for panel in panels]
        self.assertEqual(len(ids), len(set(ids)))
        non_rows = [panel for panel in panels if panel["type"] != "row"]
        for index, panel in enumerate(non_rows):
            x, y, w, h = (panel["gridPos"][key] for key in ("x", "y", "w", "h"))
            self.assertLessEqual(x + w, 24)
            for other in non_rows[index + 1:]:
                ox, oy, ow, oh = (other["gridPos"][key] for key in ("x", "y", "w", "h"))
                self.assertFalse(x < ox + ow and ox < x + w and y < oy + oh and oy < y + h)
