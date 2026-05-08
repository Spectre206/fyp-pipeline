"""
RabbitMQ Producer — anomaly.detected Publisher

This module handles all outbound RabbitMQ publishing from Layer 1. It establishes
a persistent connection to the RabbitMQ Topic Exchange on Node 1, serialises anomaly
event dictionaries to JSON, and publishes them to the anomaly.detected routing key
with delivery_mode=2 (persistent) so messages survive a broker restart.

The producer implements automatic reconnection with exponential backoff so that
temporary RabbitMQ unavailability does not cause the ADM to crash. It also
exposes a Prometheus counter (anomalies_published_total) so the observability
stack on Node 3 can track Layer 1 output rate. The Dead Letter Exchange (DLX)
configuration for unroutable messages is defined here and matches the RabbitMQ
setup from Phase 0.
"""
