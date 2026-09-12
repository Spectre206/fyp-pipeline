"""Management command — consume hitl.queue and store incidents for the dashboard."""
import json
import sys
import os

# Add the layer3 directory to sys.path so we can import rabbitmq and sqlite_logger
sys.path.insert(0, "/home/spectre/fyp-pipeline/layer3")

from django.core.management.base import BaseCommand
from hitl.models import HitlIncident
from rabbitmq.connection import get_connection


def persist_hitl_incident(data):
    """Persist one delivery without reopening a completed human decision."""
    event_id = data.get("event_id", "unknown")
    return HitlIncident.objects.get_or_create(
        event_id=event_id,
        defaults={
            "payload_json": json.dumps(data),
            "status": "PENDING",
        },
    )


class Command(BaseCommand):
    help = "Consume hitl.queue and store incidents as HitlIncident rows"

    def handle(self, *args, **options):
        conn = get_connection()
        ch = conn.channel()
        ch.basic_qos(prefetch_count=1)

        def on_message(ch, method, properties, body):
            try:
                data = json.loads(body)
                event_id = data.get("event_id", "unknown")
                _, created = persist_hitl_incident(data)
                ch.basic_ack(method.delivery_tag)
                state = "Stored" if created else "Duplicate ignored"
                self.stdout.write(f"[HITL] {state} {event_id}")
            except Exception as e:
                self.stderr.write(f"Error: {e}")
                ch.basic_nack(method.delivery_tag, requeue=True)

        ch.basic_consume("hitl.queue", on_message)
        self.stdout.write("[HITL] Listening on hitl.queue …")
        try:
            ch.start_consuming()
        except KeyboardInterrupt:
            self.stdout.write("[HITL] Consumer stopped.")
