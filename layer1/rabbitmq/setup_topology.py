# layer1/rabbitmq/setup_topology.py — COMPLETE v1.2 (Corrected)
import pika

# Fix 1: Explicitly target the 'fyp' virtual host container
params = pika.ConnectionParameters(
    host="localhost", 
    virtual_host="fyp",
    credentials=pika.PlainCredentials("fyp_user", "fyp_pass_2026")
)
conn = pika.BlockingConnection(params)
ch = conn.channel()

print("[setup] Connecting to virtual host 'fyp'...")

# ── Exchanges ────────────────────────────────────────────────────────────
# Fix 2: Changed from "topic" to "fanout" to guarantee parallel model ingestion
ch.exchange_declare("detection.fanout", "fanout", durable=True) 
ch.exchange_declare("fyp.events", "topic", durable=True)       # Core Pipeline Bus
ch.exchange_declare("fyp.dlx", "direct", durable=True)         # Dead Letter Exchange

dlx = {"x-dead-letter-exchange": "fyp.dlx", "x-dead-letter-routing-key": "dead"}

# ── Layer 1 Queues ───────────────────────────────────────────────────────
ch.queue_declare("raw.events", durable=True, arguments=dlx)
ch.queue_declare("validated.event", durable=True, arguments=dlx)
ch.queue_declare("detect.cpu", durable=True, arguments=dlx)
ch.queue_declare("detect.error", durable=True, arguments=dlx)
ch.queue_declare("detect.throughput", durable=True, arguments=dlx)
ch.queue_declare("detect.auth", durable=True, arguments=dlx)
ch.queue_declare("detect.schema", durable=True, arguments=dlx)
ch.queue_declare("fusion.results", durable=True, arguments=dlx)

# ── Layer 2 Queues ───────────────────────────────────────────────────────
ch.queue_declare("anomaly.detected", durable=True, arguments=dlx)
ch.queue_declare("triage.result", durable=True, arguments=dlx)
ch.queue_declare("strategy.result", durable=True, arguments=dlx)
ch.queue_declare("auto.execute", durable=True, arguments=dlx)
ch.queue_declare("hitl.queue", durable=True, arguments=dlx)
ch.queue_declare("outcome.feedback", durable=True, arguments=dlx)

# ── Diagnostics & Quarantine Queues ──────────────────────────────────────
ch.queue_declare("schema.violations", durable=True)
ch.queue_declare("dead.letters", durable=True)

# ── Bindings ─────────────────────────────────────────────────────────────
# 1. Ingestion Routing
ch.queue_bind("raw.events", "fyp.events", "event.raw")
ch.queue_bind("validated.event", "fyp.events", "event.valid")
ch.queue_bind("fusion.results", "fyp.events", "fusion.result")
# 2. Parallel Model Fanout Routing (Routing keys are ignored by fanout exchanges, routing string can be empty)
ch.queue_bind("detect.cpu", "detection.fanout", "")
ch.queue_bind("detect.error", "detection.fanout", "")
ch.queue_bind("detect.throughput", "detection.fanout", "")
ch.queue_bind("detect.auth", "detection.fanout", "")
ch.queue_bind("detect.schema", "detection.fanout", "")

# 3. Asynchronous Multi-Agent Control Plane Routing
ch.queue_bind("anomaly.detected", "fyp.events", "anomaly.#") # Catch-all for schema & model anomalies
ch.queue_bind("triage.result", "fyp.events", "triage.result")
ch.queue_bind("strategy.result", "fyp.events", "strategy.result")
ch.queue_bind("auto.execute", "fyp.events", "auto.execute")
ch.queue_bind("hitl.queue", "fyp.events", "hitl.queue")
ch.queue_bind("outcome.feedback", "fyp.events", "outcome.feedback")

# 4. Dead Letter Diagnostic Routing
ch.queue_bind("dead.letters", "fyp.dlx", "dead")

conn.close()
print("[setup] Success: v1.2 diagram-aligned topology created inside virtual host 'fyp'.")