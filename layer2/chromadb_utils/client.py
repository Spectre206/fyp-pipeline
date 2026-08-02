"""ChromaDB Client — Connection and Collection Initialisation."""
import os

# Force offline mode to prevent HuggingFace connection attempts
# (model is already cached locally; no internet on ai-brain-node)
os.environ["HF_HUB_OFFLINE"] = "1"

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()

CHROMA_PATH = "./chromadb_data"
COLLECTION_NAME = "incident_history"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384-dimensional, cosine distance

_client = None
_collection = None

def get_collection():
    """Return the incident_history collection. Creates if not exists. Singleton."""
    global _client, _collection
    if _collection is not None:
        return _collection

    _client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )
    return _collection

def get_document_count() -> int:
    return get_collection().count()
