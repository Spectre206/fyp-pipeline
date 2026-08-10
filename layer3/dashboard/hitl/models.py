"""Django ORM model mapping to the existing decisions table."""
from django.db import models

class Decision(models.Model):
    event_id = models.CharField(max_length=255)
    anomaly_type = models.CharField(max_length=100, blank=True, null=True)
    severity = models.CharField(max_length=50, blank=True, null=True)
    affected_component = models.CharField(max_length=255, blank=True, null=True)
    node = models.CharField(max_length=100, blank=True, null=True)
    routing_reason = models.CharField(max_length=100, blank=True, null=True)
    risk_tier_from_llm = models.CharField(max_length=50, blank=True, null=True)
    confidence_from_llm = models.FloatField(blank=True, null=True)
    decision_type = models.CharField(max_length=50)
    decision_timestamp = models.CharField(max_length=100, blank=True, null=True)
    time_in_queue_seconds = models.FloatField(blank=True, null=True)
    original_actions = models.TextField(blank=True, null=True)
    final_actions = models.TextField(blank=True, null=True)
    operator_notes = models.TextField(blank=True, null=True)
    auto_execute_outcome = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "decisions"

    def __str__(self):
        return f"{self.event_id} — {self.decision_type}"

class HitlIncident(models.Model):
    """Incident awaiting operator action in the HITL dashboard."""
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("MODIFIED", "Modified"),
    ]

    event_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    payload_json = models.TextField(help_text="Full Policy Agent message as JSON")
    arrived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["arrived_at"]

    def __str__(self):
        return f"{self.event_id} ({self.status})"
