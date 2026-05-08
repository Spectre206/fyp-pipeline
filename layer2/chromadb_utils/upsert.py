"""
ChromaDB Upsert — Learning Agent Write Operations

This module handles all write operations to the ChromaDB incident_history
collection. It is called exclusively by the Learning Agent — no other agent
writes to ChromaDB.

For each resolved incident, it upserts a document whose text field is the
qwen3:0.6b-generated summary (the text that will be embedded and used for
future similarity retrieval). The metadata fields stored alongside the
embedding include: incident_id, anomaly_type, risk_tier, outcome_type,
confidence_at_decision, severity, node, affected_component, timestamp,
operator_approved, and negative_example flag.

The upsert operation uses the incident_id as the ChromaDB document ID so
that re-running the same incident (e.g. after a retry) overwrites the
existing record rather than creating a duplicate.
"""
