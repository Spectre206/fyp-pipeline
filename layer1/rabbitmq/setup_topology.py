# layer1/rabbitmq/setup_topology.py
# Run FIRST before any producers or consumers. Idempotent.

import pika

params = pika.ConnectionParameters(
    host='localhost',
    virtual_host='fyp',
    credentials=pika.PlainCredentials('fyp_user', 'fyp_pass_2026')
)
conn = pika.BlockingConnection(params)
ch   = conn.channel()

# ── Exchanges ─────────────────────────────────────────────────────────
# Matches Layer 1 Diagram exactly
ch.exchange_declare('raw.events',       'topic',  durable=True)
ch.exchange_declare('validated.event',  'topic',  durable=True)
ch.exchange_declare('detection.fanout', 'topic',  durable=True)
ch.exchange_declare('fyp.dlx',          'direct', durable=True)

# ── Dead letter args ──────────────────────────────────────────────────
dlx_args = {
    'x-dead-letter-exchange':    'fyp.dlx',
    'x-dead-letter-routing-key': 'dead'
}

# ── Queues ────────────────────────────────────────────────────────────
# 1. Ingestion Queues
ch.queue_declare('raw.events',        durable=True, arguments=dlx_args)
ch.queue_declare('validated.event',   durable=True, arguments=dlx_args)
ch.queue_declare('schema.violations', durable=True)

# 2. Per-detector queues (internal Layer 1)
ch.queue_declare('detect.cpu',        durable=True, arguments=dlx_args)
ch.queue_declare('detect.error',      durable=True, arguments=dlx_args)
ch.queue_declare('detect.throughput', durable=True, arguments=dlx_args)
ch.queue_declare('detect.auth',       durable=True, arguments=dlx_args)
ch.queue_declare('detect.schema',     durable=True, arguments=dlx_args)

# 3. Fusion Engine internal & final output
ch.queue_declare('fusion.results',    durable=True, arguments=dlx_args)
ch.queue_declare('anomaly.detected',  durable=True, arguments=dlx_args)
ch.queue_declare('dead.letters',      durable=True)

# ── Bindings ──────────────────────────────────────────────────────────
# SEG -> raw.events (Consumed by Pydantic Validator)
ch.queue_bind('raw.events', 'raw.events', 'anomaly.raw')

# Validator -> validated.event (Consumed by ADM Runner)
ch.queue_bind('validated.event', 'validated.event', 'event.valid')

# detection.fanout → per-detector queues
ch.queue_bind('detect.cpu',        'detection.fanout', 'detect.cpu')
ch.queue_bind('detect.error',      'detection.fanout', 'detect.error')
ch.queue_bind('detect.throughput', 'detection.fanout', 'detect.throughput')
ch.queue_bind('detect.auth',       'detection.fanout', 'detect.auth')
ch.queue_bind('detect.schema',     'detection.fanout', 'detect.schema')

# fyp.dlx → dead.letters
ch.queue_bind('dead.letters', 'fyp.dlx', 'dead')

conn.close()
print('[setup] v1.2 diagram-aligned topology created successfully.')