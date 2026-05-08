"""
ChromaDB Client — Connection and Collection Initialisation

This module handles the ChromaDB connection and ensures the incident_history
collection exists with the correct configuration before any agent tries to
use it. It uses sentence-transformers (all-MiniLM-L6-v2) as the embedding
function, producing 384-dimensional vectors.

On startup, it checks whether the incident_history collection already exists
(existing deployment with accumulated knowledge) or needs to be created fresh
(first run). The collection name, embedding model, and distance metric (cosine)
are defined here as constants so they are consistent across all agents that
access ChromaDB. This module is imported by both the Triage Agent (for queries)
and the Learning Agent (for upserts).
"""
