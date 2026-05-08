"""
Triage Agent — Rule-Based Classifier + ChromaDB RAG

This module is the first agent in the Layer 2 pipeline. It consumes from the
anomaly.detected RabbitMQ queue and performs two operations for each incoming
event:

  1. Rule-based classification: applies a lookup table mapping (anomaly_type,
     severity) pairs to response protocol codes (e.g. RESTART_CONSUMER,
     RATE_LIMIT, ISOLATE_NODE). This is deterministic and requires no LLM call.

  2. RAG context retrieval: queries the ChromaDB incident_history collection
     using the event text as the query. Retrieves the top-3 most similar past
     incidents (filtered to successful outcomes only) to inject as context into
     the Strategy Agent prompt.

The Triage Agent publishes the enriched triage.result message (original event +
protocol code + RAG context + latency measurement) to the triage.result queue.
Target latency: ≤ 3 seconds. Hard timeout: 5 seconds.
"""
