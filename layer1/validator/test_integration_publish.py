import json, pika, sys, argparse
from pathlib import Path
sys.path.insert(0, '.')

from validator import load_config, DEFAULT_CONFIG_PATH, FALLBACK_RABBITMQ

# ── v1.3: connection params now come from validator_config.json, same
#    source of truth the validator itself uses -- not a second hardcoded
#    copy. Use --host to override for a quick one-off test. ─────────────
ap = argparse.ArgumentParser()
ap.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
ap.add_argument("--host", default=None, help="Override RabbitMQ hostname for this test run only")
a = ap.parse_args()

cfg = load_config(Path(a.config))
rmq = cfg.get("rabbitmq", FALLBACK_RABBITMQ)
host = a.host or rmq.get("host", FALLBACK_RABBITMQ["host"])

RMQPARAMS = pika.ConnectionParameters(
    host=host,
    port=rmq.get("port", FALLBACK_RABBITMQ["port"]),
    virtual_host=rmq.get("virtual_host", FALLBACK_RABBITMQ["virtual_host"]),
    credentials=pika.PlainCredentials(
        rmq.get("username", FALLBACK_RABBITMQ["username"]),
        rmq.get("password", FALLBACK_RABBITMQ["password"]),
    ),
)

# ── Publish test events ────────────────────────────────────────────────
conn = pika.BlockingConnection(RMQPARAMS)
ch = conn.channel()

# Event 1: valid
valid_event = {
    "event_id":           "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "timestamp":          "2026-04-01T10:00:00+00:00",
    "anomaly_type":       "cpu_memory_spike",
    "severity":           "HIGH",
    "affected_component": "ADM runner",
    "node":               "stream-node",
    "metric_values":      {"cpu_percent": 91.5},
    "context":            "Integration test — valid event",
}

# Event 2: invalid (missing node and metric_values)
invalid_event = {
    "event_id":           "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    "timestamp":          "2026-04-01T10:00:01+00:00",
    "anomaly_type":       "cpu_memory_spike",
    "severity":           "HIGH",
    "affected_component": "ADM runner",
    # deliberately missing: node, metric_values
}

ch.basic_publish(
    exchange=rmq.get("exchange", FALLBACK_RABBITMQ["exchange"]),
    routing_key='event.raw',
    body=json.dumps(valid_event).encode(),
    properties=pika.BasicProperties(delivery_mode=2)
)
print(f"[TEST] Published 1 VALID event to raw.events (via {host})")

ch.basic_publish(
    exchange=rmq.get("exchange", FALLBACK_RABBITMQ["exchange"]),
    routing_key='event.raw',
    body=json.dumps(invalid_event).encode(),
    properties=pika.BasicProperties(delivery_mode=2)
)
print(f"[TEST] Published 1 INVALID event to raw.events (via {host})")

conn.close()

print("\nNow check RabbitMQ queues:")
print("  - raw.events        should have 2 messages waiting")
print("  - Start the validator: python validator.py")
print("  - After processing:")
print("    - validated.event  queue should have 1 message (valid event)")
print("    - anomaly.detected queue should have 1 message (schema_drift)")
print("    - raw.events       queue should be empty")