# Layer 2 User Guide — ai-brain-node (192.168.18.102)

This guide covers installing, configuring, and running the full Layer 2 agent stack
on Node 2 from scratch. Layer 1 must be verified and publishing to anomaly.detected
before Layer 2 agents are started.

---

## 1. Prerequisites Checklist

Before starting Layer 2, confirm: Node 2 has static IP 192.168.18.102, hostname
ai-brain-node, is accessible via passwordless SSH from the other nodes, Ollama is
installed and configured with OLLAMA_HOST=0.0.0.0:11434 (from Phase 0), both
qwen3:1.7b and qwen3:0.6b are pulled, ChromaDB is reachable (smoke test from
Phase 0 passed), and the anomaly.detected queue on Node 1 RabbitMQ is receiving
messages from Layer 1.

---

## 2. Python Environment Setup

This section will cover creating a virtual environment on Node 2, installing all
dependencies from requirements_node2.txt, and verifying that both the pika RabbitMQ
client and the chromadb library can connect to their respective services. The
sentence-transformers model (all-MiniLM-L6-v2) is downloaded at import time on
first run — this section will document the expected download size and location.

---

## 3. ChromaDB Initialisation

This section will describe how to create the incident_history collection in ChromaDB
with the correct schema and metadata fields, how to verify the collection is empty
(fresh start) or pre-populated (existing deployment), and how to run a query test
to confirm that vector retrieval is working before starting the Triage Agent. The
collection schema matches the specification in the System Design document Section 4.2.

---

## 4. Loading the Confidence Threshold Config

This section will describe the config/threshold_config.json file, its initial value
(0.65), and how the Policy Agent loads it on startup. It will also cover what happens
if the file is missing or corrupt (Policy Agent falls back to the hardcoded default
of 0.65 and logs a warning), and how to reset the threshold to the default after
the Learning Agent has modified it.

---

## 5. Starting the Triage Agent

This section will describe starting the Triage Agent as a RabbitMQ consumer on the
anomaly.detected queue. It will cover expected startup log output (ChromaDB
connection, consumer registration, sentence-transformers model load), how to verify
that triage.result is receiving messages after events flow through from Layer 1, and
what the latency counter output looks like under normal operation.

---

## 6. Starting the Strategy Agent

This section will cover starting the Strategy Agent as a consumer on triage.result.
It will document how to verify that the Ollama API is reachable at localhost:11434,
how to read the per-prompt timing output (response time, tokens/second), and how
to confirm that the 7-field JSON schema validation is passing in production (the
extra-field constraint and num_predict=512 fixes from Phase 0 must be in the
strategy_system_prompt.txt file).

---

## 7. Starting the Policy Agent

This section will describe starting the Policy Agent as a consumer on strategy.result.
It will explain how to verify that routing decisions are being written to the correct
output queues (auto.execute vs. hitl.queue) and how to inspect routing reason codes
in the log output. The threshold_config.json reload behaviour (reloaded on each
decision, not once at startup) will be documented here.

---

## 8. Starting the Learning Agent

This section will describe starting the Learning Agent as a consumer on outcome.feedback.
It will explain the EMA threshold update formula, how to observe threshold changes in
the log output, and how to verify that ChromaDB is being updated after each resolved
incident. The Learning Agent fires post-dispatch and does not block the main pipeline
path — this section will document how to confirm that its latency does not affect MTTA.

---

## 9. Running All Four Agents Concurrently

This section will document how to run all four agents simultaneously on Node 2
(as separate processes or systemd services) and how to monitor the combined RAM
usage to confirm it stays within the Node 2 budget (~3.8GB nominal, ~4.9GB peak
during embedding). The concurrent RAM validation test from Open Question 2 in the
System Design document is documented here.

---

## 10. Troubleshooting

Common issues will be documented here as they are encountered: Ollama not responding
(OLLAMA_HOST not set), ChromaDB collection not found (initialisation step skipped),
Strategy Agent timeout fires too early (check num_predict and num_ctx settings),
Learning Agent not updating ChromaDB (outcome.feedback queue not receiving messages
from Layer 3), and Policy Agent routing all events to HITL (check threshold_config.json
value — may have drifted below 0.65 or the file may be corrupt).
