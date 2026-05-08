"""
Learning Agent — qwen3:0.6b via Ollama + ChromaDB Knowledge Accumulation

This module fires after every resolved incident (AUTO_EXECUTE_SUCCESS,
AUTO_EXECUTE_FAILURE, HITL_APPROVED, HITL_REJECTED, HITL_MODIFIED). It consumes
from the outcome.feedback queue published by Layer 3 after each dispatch.

For each outcome, the Learning Agent:
  1. Calls qwen3:0.6b via Ollama to generate a concise summary and categorisation
     of the incident and its resolution. The summary becomes the ChromaDB document
     text used for future RAG retrieval.
  2. Upserts the incident into ChromaDB with the full outcome metadata.
     Negative outcomes (FAILURE, REJECTED) are stored with negative_example=True
     and excluded from future positive RAG retrieval.
  3. Updates the EMA confidence threshold in config/threshold_config.json
     based on the outcome signal. Hard bounds: threshold ∈ [0.60, 0.90].

The Learning Agent fires post-dispatch and has zero latency impact on the main
pipeline path. Its timeout (10 seconds) does not affect MTTA or MTTR measurements.
"""
