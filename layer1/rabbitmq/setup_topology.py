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
ch.exchange_declare('detection.fanout', 'topic',  durable=True)
ch.exchange_declare('fyp.events',       'topic',  durable=True)
ch.exchange_declare('pipeline.events',  'topic',  durable=True)
ch.exchange_declare('fyp.dlx',          'direct', durable=True)

# ── Dead letter args ──────────────────────────────────────────────────
dlx_args = {
    'x-dead-letter-exchange':    'fyp.dlx',
    'x-dead-letter-routing-key': 'dead'
}

# ── Queues ────────────────────────────────────────────────────────────
# Per-detector queues (internal Layer 1)
ch.queue_declare('detect.cpu',        durable=True, arguments=dlx_args)
ch.queue_declare('detect.error',      durable=True, arguments=dlx_args)
ch.queue_declare('detect.throughput', durable=True, arguments=dlx_args)
ch.queue_declare('detect.auth',       durable=True, arguments=dlx_args)
ch.queue_declare('detect.schema',     durable=True, arguments=dlx_args)

# Fusion Engine input queue (internal Layer 1)
ch.queue_declare('fusion.results',    durable=True, arguments=dlx_args)

# Pipeline queues (cross-node)
ch.queue_declare('anomaly.detected',  durable=True, arguments=dlx_args)
ch.queue_declare('schema.violations', durable=True)
ch.queue_declare('dead.letters',      durable=True)

# ── Bindings ──────────────────────────────────────────────────────────
# detection.fanout → per-detector queues
ch.queue_bind('detect.cpu',        'detection.fanout', 'detect.cpu')
ch.queue_bind('detect.error',      'detection.fanout', 'detect.error')
ch.queue_bind('detect.throughput', 'detection.fanout', 'detect.throughput')
ch.queue_bind('detect.auth',       'detection.fanout', 'detect.auth')
ch.queue_bind('detect.schema',     'detection.fanout', 'detect.schema')

# fyp.events → anomaly.detected (Triage Agent on Node 2)
ch.queue_bind('anomaly.detected',  'pipeline.events',  'anomaly.raw')

# fyp.dlx → dead.letters
ch.queue_bind('dead.letters',      'fyp.dlx',    'dead')

conn.close()
print('[setup] v1.2 two-exchange topology created successfully.')