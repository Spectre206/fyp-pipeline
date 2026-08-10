"""RabbitMQ Connection & Publishing Helpers for Node 2 agents."""
import os
import pika
from dotenv import load_dotenv

load_dotenv()

def get_connection() -> pika.BlockingConnection:
    """Return a fresh BlockingConnection to stream-node RabbitMQ."""
    params = pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "stream-node"),
        port=int(os.getenv("RABBITMQ_PORT", 5672)),
        virtual_host="fyp",
        credentials=pika.PlainCredentials(
            os.getenv("RABBITMQ_USER", "fyp_user"),
            os.getenv("RABBITMQ_PASS", "fyp_pass_2026"),
        ),
        heartbeat=600,
        blocked_connection_timeout=300,
    )
    return pika.BlockingConnection(params)

def publish(ch, routing_key: str, body: str):
    """Publish to fyp.events exchange with given routing key."""
    ch.basic_publish(
        exchange="fyp.events",
        routing_key=routing_key,
        body=body,
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
        ),
    )
