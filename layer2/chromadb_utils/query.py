"""
ChromaDB Query — RAG Retrieval Protocol for Triage Agent

This module implements the three-step RAG retrieval protocol used by the Triage
Agent:

  Step 1 — Similarity search: query incident_history with the incoming event
  text and retrieve the top-5 most similar documents by cosine similarity.

  Step 2 — Outcome filter: retain only documents where outcome_type is
  AUTO_EXECUTE_SUCCESS or HITL_APPROVED. Failed/rejected incidents are stored
  in ChromaDB for Learning Agent analysis but are not injected as positive
  RAG context.

  Step 3 — Risk tier balance check: if all retained documents share the same
  risk_tier, fetch one contrast example from the opposite tier to prevent
  systematic bias reinforcement in the Strategy Agent prompt.

Returns a list of up to 3 context objects, each containing incident_id,
summary text, risk_tier, outcome_type, and similarity_score. Returns an
empty list (not an error) if the collection is empty (cold start).
"""
