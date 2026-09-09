# Layer 2 — AI Control Plane

> **Node:** ai-brain-node — `192.168.18.102`
> **Hardware:** AMD Ryzen 5, 8 GB RAM, Ubuntu 24.04 Server (headless)

---

## 1. Overview
Layer 2 is the asynchronous AI Control Plane of the self-healing data pipeline. It acts as the bridge between Layer 1 (anomaly detection) and Layer 3 (execution). 

Layer 2 receives anomaly events, fetches historical incident context, evaluates the best remediation strategy using local Large Language Models (LLMs), and applies deterministic policy rules to route the incident for either human review (HITL) or autonomous execution.

## 2. Architecture and Agent Flow

Layer 2 consists of four distinct agents running asynchronously on Node 2. The agents communicate strictly via RabbitMQ queues on Node 1, decoupling reasoning from anomaly detection.

```mermaid
flowchart TD
    L1[Layer 1: anomaly.detected] --> Triage
    
    subgraph Layer 2: Node 2 (ai-brain-node)
        Triage[Triage Agent\nRule-based + RAG] --> |triage.result| Strategy
        Strategy[Strategy Agent\nLLM: qwen3:1.7b] --> |strategy.result| Policy
        Policy[Policy Agent\nDeterministic Rules] 
    end
    
    Policy --> |auto.execute| L3[Layer 3: Execution]
    Policy --> |hitl.queue| L3
    
    L3 --> |outcome.feedback| Learning
    
    subgraph Layer 2: Node 2
        Learning[Learning Agent\nLLM: qwen3:0.6b] --> |Upsert| ChromaDB[(ChromaDB)]
    end
    
    ChromaDB -.-> |Query| Triage
```

### Agent Responsibilities
1. **Triage Agent:** A deterministic, rule-based classifier that normalizes incoming anomalies and queries ChromaDB for historical context. **It is NOT an LLM agent.**
2. **Strategy Agent:** The core LLM reasoning component. Uses `qwen3:1.7b` via Ollama to generate a strict 7-field JSON remediation strategy.
3. **Policy Agent:** A deterministic policy enforcement boundary. It evaluates the Strategy Agent's output against a 5-rule table to safely authorize execution or mandate human-in-the-loop (HITL) review.
4. **Learning Agent:** Summarizes outcomes from Layer 3 using `qwen3:0.6b` and writes incidents to ChromaDB. It mathematically adjusts the auto-execution confidence threshold using an Exponential Moving Average (EMA).

## 3. The Policy and Safety Boundary
Layer 2 enforces a strict boundary between LLM reasoning and operational authority:
- **LLM Proposes:** The Strategy Agent proposes a remediation strategy, assigning a risk tier and a confidence score.
- **Policy Constrains:** The Policy Agent strictly enforces safety. It blocks any proposal that is marked as `HIGH` risk, falls below the dynamic confidence threshold, or lacks valid JSON parsing, routing them deterministically to HITL. Autonomous execution is strictly constrained by these policies.

## 4. LLM and ChromaDB Integration
- **Local Inference:** Layer 2 runs CPU-only LLM inference via Ollama (`http://localhost:11434`). No GPU/CUDA hardware is required.
- **Historical Context (RAG):** ChromaDB (`all-MiniLM-L6-v2` embeddings) provides Retrieval-Augmented Generation (RAG). The Triage Agent retrieves similar incidents with positive outcomes to help the Strategy Agent calibrate its risk judgements.
- **Learning/Persistence:** The Learning Agent uses ChromaDB for persistent historical memory, but does not perform any model weight updating or fine-tuning. 

## 5. Observability and Metrics
All agents expose Prometheus metrics (ports 8010–8013) and write append-only logs to `layer2/logs/` (e.g., `strategy_agent.jsonl`, `parse_error.jsonl`).

**Key Latency Boundaries:**
- **MTTA (Mean Time To Acknowledge):** Computed strictly as the control-plane interval between `triage_timestamp` and `policy_timestamp`.
- **MTTR (Mean Time To Recovery):** Computed as the interval from `triage_timestamp` to the receipt of Layer 3 `outcome.feedback`. 
*(Note: These measure decision latency, not infrastructure recovery times).*

## 6. Evaluation Status
- **Strategy Model Benchmark:** In an offline Phase 0 model-selection benchmark, `qwen3:1.7b` achieved approximately 90% schema-valid outputs across 30 strict adversarial prompts. This is a model-level benchmark and distinct from the runtime end-to-end System Schema Validity Rate (SVR).
- **Learning Agent Formal Evaluation:** Formal quantitative evaluation of the Learning Agent's downstream learning improvement or summarization accuracy is not currently measured or demonstrated in the implementation.

## 7. Known Limitations
- The Learning Agent provides observability and dynamically updates a mathematical threshold, but formal end-to-end learning accuracy has not been experimentally validated.
- Several configurations are currently hardcoded (e.g., RabbitMQ host to `stream-node`, Ollama to `localhost:11434`, ChromaDB directory paths).
- Risk Tier Accuracy metrics lack an automated mechanism to compare against ground truth datasets in production. 

## 8. Cross-Layer Contracts
- **Layer 1 to Layer 2:** The `anomaly.detected` payload processes both structural anomalies (which bypass Fusion and contain a direct `anomaly_type`) and Fused incidents (which require the Triage Agent to derive the type from `contributing_models`). 
- **Layer 2 to Layer 3:** The Policy Agent is the sole publisher to Layer 3, guaranteeing a strictly validated and safety-checked JSON payload to either `auto.execute` or `hitl.queue`.

For precise implementation details, message schemas, and historical logs, consult the **[Layer 2 Component Log](docs/layer2_component_log.md)**.