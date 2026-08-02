"""ChromaDB Query — 3-Step RAG Retrieval Protocol for Triage Agent."""
from .client import get_collection
from typing import List, Dict, Optional

POSITIVE_OUTCOMES = {"AUTO_EXECUTE_SUCCESS", "HITL_APPROVED"}

def retrieve_rag_context(event: dict, n_results: int = 3) -> List[Dict]:
    """
    Three-step RAG retrieval:
    Step 1 — Similarity search: top-5 matches.
    Step 2 — Outcome filter: keep only positive outcomes.
    Step 3 — Risk tier balance: if all same tier, add one contrast example.
    Returns up to n_results context dicts, or empty list if collection < 3 docs.
    """
    col = get_collection()
    if col.count() < 3:
        return []  # cold start — skip RAG

    # Build query text from event fields
    query_text = (
        f"{event.get('anomaly_type', '')} on {event.get('node', '')}. "
        f"Severity: {event.get('severity', '')}. "
        f"Component: {event.get('affected_component', '')}."
    )

    # Step 1: Top-5 similarity search
    results = col.query(
        query_texts=[query_text],
        n_results=min(5, col.count()),
        include=["documents", "metadatas", "distances"],
    )
    docs      = results["documents"][0]
    metas     = results["metadatas"][0]
    distances = results["distances"][0]

    # Step 2: Filter to positive outcomes only
    positive = []
    for d, m, dist in zip(docs, metas, distances):
        if m.get("outcome_type") in POSITIVE_OUTCOMES:
            positive.append({
                "summary": d,
                "meta": m,
                "similarity": round(1 - dist, 4),
            })

    if not positive:
        return []

    # Step 3: Risk tier balance check
    tiers = {r["meta"].get("risk_tier") for r in positive[:n_results]}
    if len(tiers) == 1:
        # All same tier — try to add one contrast example
        opposite = "HIGH" if list(tiers)[0] == "LOW" else "LOW"
        contrast = col.query(
            query_texts=[query_text],
            n_results=1,
            where={
                "$and": [
                    {"risk_tier": opposite},
                    {"outcome_type": {"$in": list(POSITIVE_OUTCOMES)}}
                ]
            },
            include=["documents", "metadatas", "distances"],
        )
        if contrast["documents"][0]:
            positive.append({
                "summary":    contrast["documents"][0][0],
                "meta":       contrast["metadatas"][0][0],
                "similarity": round(1 - contrast["distances"][0][0], 4),
            })

    return positive[:n_results]


def format_rag_context(context: List[Dict]) -> str:
    """Format RAG context for injection into Strategy Agent's prompt."""
    if not context:
        return ""
    lines = ["HISTORICAL CONTEXT (use to calibrate risk tier judgment only):"]
    for c in context:
        m = c["meta"]
        lines.append(
            f"Past incident: {c['summary']} "
            f"Risk tier was: {m.get('risk_tier', '?')}. "
            f"This was {m.get('outcome_type', '?')}. "
            f"(similarity: {c['similarity']:.3f})"
        )
    lines.append("If history shows auto-recovery, bias toward LOW risk tier.")
    lines.append("If history shows cascading failures, bias toward HIGH risk tier.")
    return "\n".join(lines)
