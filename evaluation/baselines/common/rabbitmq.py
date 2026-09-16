"""Explicit AMQP configuration. Does not create or purge application topology."""
import os
import pika


def connect():
    required = ('RABBITMQ_HOST', 'RABBITMQ_USER', 'RABBITMQ_PASS')
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise ValueError('Set broker environment variables: ' + ', '.join(missing))
    return pika.BlockingConnection(pika.ConnectionParameters(
        host=os.environ['RABBITMQ_HOST'], port=int(os.getenv('RABBITMQ_PORT', '5672')),
        virtual_host='fyp', credentials=pika.PlainCredentials(os.environ['RABBITMQ_USER'], os.environ['RABBITMQ_PASS']),
        heartbeat=600, blocked_connection_timeout=30, socket_timeout=10))


def require_idle(channel, queues):
    for queue in queues:
        status = channel.queue_declare(queue=queue, passive=True).method
        if status.consumer_count:
            raise RuntimeError(f'{queue} already has consumers; stop competing services')


def publish(channel, routing_key, body, headers=None):
    channel.basic_publish(exchange='fyp.events', routing_key=routing_key, body=body,
                          mandatory=True, properties=pika.BasicProperties(
                              delivery_mode=2, content_type='application/json', headers=headers or {}))
