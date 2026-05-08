"""
Strategy Agent — qwen3:1.7b via Ollama (Structured JSON Reasoning)

This module is the LLM reasoning core of the pipeline. It consumes from the
triage.result queue and calls qwen3:1.7b via the Ollama REST API
(http://localhost:11434/api/generate) with a structured prompt constructed from:
  - The triaged incident fields
  - The RAG context injected by the Triage Agent
  - The versioned system prompt from prompts/strategy_system_prompt.txt

The system prompt includes the extra-field constraint identified in Phase 0
failure analysis ("Output ONLY these 7 fields...") and num_predict is set to 512.

The agent validates the LLM response against the 7-field JSON schema using the
same validation logic as the Phase 0 benchmark. Schema-valid responses are
published to strategy.result. Parse errors or timeouts (> 30 seconds) cause
the event to be routed directly to hitl.queue with the appropriate reason code.
Response time and tokens/second are recorded per event for Prometheus metrics.
"""
