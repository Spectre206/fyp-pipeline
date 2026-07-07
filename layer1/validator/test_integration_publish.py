import json, pika, sys
sys.path.insert(0, '.')

# ── CORRECTED CONNECTION PARAMS ────────────────────────────────────────
RMQPARAMS = pika.ConnectionParameters(
    host='192.168.18.101',
    virtual_host='fyp',
    credentials=pika.PlainCredentials('fyp_user', 'fyp_pass_2026')
)

# ── Publish test events ────────────────────────────────────────────────
conn = pika.BlockingConnection(RMQPARAMS)
ch   = conn.channel()

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
    exchange='fyp.events', routing_key='event.raw',
    body=json.dumps(valid_event).encode(),
    properties=pika.BasicProperties(delivery_mode=2)
)
print("[TEST] Published 1 VALID event to raw.events")

ch.basic_publish(
    exchange='fyp.events', routing_key='event.raw',
    body=json.dumps(invalid_event).encode(),
    properties=pika.BasicProperties(delivery_mode=2)
)
print("[TEST] Published 1 INVALID event to raw.events")

conn.close()

print("\nNow check RabbitMQ queues:")
print("  • raw.events        should have 2 messages waiting")
print("  • Start the validator: python validator.py")
print("  • After processing:")
print("    - validated.event  queue should have 1 message (valid event)")
print("    - anomaly.detected queue should have 1 message (schema_drift)")
print("    - raw.events       queue should be empty")
print("    - Prometheus at http://localhost:8002/metrics:")
print("      fyp_validation_passed_total 1")
print("      fyp_validation_errors_total{error_type='MISSING_FIELD'} 1")