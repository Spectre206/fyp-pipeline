"""ChromaDB Upsert — Learning Agent write operations."""
from .client import get_collection
import structlog

log = structlog.get_logger()


def upsert_incident(incident_id: str, summary: str, metadata: dict):
    """
    Upsert a resolved incident into ChromaDB.
    Uses incident_id as document ID — safe to call multiple times.
    negative_example=True incidents are stored but excluded from RAG retrieval
    by the query module's outcome filter.
    """
    col = get_collection()
    col.upsert(
        ids=[incident_id],
        documents=[summary],
        metadatas=[metadata],
    )
    log.info(
        "chromadb_upserted",
        incident_id=incident_id,
        outcome=metadata.get("outcome_type"),
        negative=metadata.get("negative_example", False),
    )
