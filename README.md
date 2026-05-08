# Distributed Multi-Agent Coordination for Self-Healing Data Pipelines
## A Human-in-the-Loop Approach on Commodity Hardware

> **Institution:** Department of CS&IT, UET Peshawar — Nowshera Campus
> **Team:** Muhammad Adeel (23JZBCS0226) & Muhammad Asim
> **Supervisor:** Dr. Laeeq Ahmed (Big Data & AI)
> **Timeline:** March – December 2026
> **Target Publication:** MDPI Big Data & Cognitive Computing — Submission 15 Oct 2026

---

## What This Project Does

This system detects anomalies in a distributed streaming data pipeline and autonomously decides whether to fix them or escalate them to a human operator. It runs on three physical commodity machines with no cloud or GPU dependency. When an anomaly is detected — a CPU spike, error rate surge, authentication flood, throughput drop, or schema drift — a chain of four AI agents classifies it, reasons about the best response using a local LLM, routes it to either automatic execution or a human review dashboard, and learns from the outcome to improve future decisions.

The research goal is to prove that this class of self-healing agentic system — previously only described theoretically in the AIOps literature — can be built and benchmarked on real commodity hardware, with measurable improvements in Mean Time To Acknowledge (MTTA) and Mean Time To Remediate (MTTR) over a static threshold-only baseline.

---

## Architecture at a Glance

```
Node 1 — stream-node (192.168.18.101)        Layer 1: Real-Time Data Plane
  SEG → Pydantic Validator → Feature Store → 5 ML Detectors → RabbitMQ Topic Exchange

Node 2 — ai-brain-node (192.168.18.102)      Layer 2: AI Control Plane
  Triage Agent → Strategy Agent (qwen3:1.7b) → Policy Agent → Learning Agent (qwen3:0.6b)
  ChromaDB (RAG — Historical Incidents)

Node 3 — gateway-node (192.168.18.103)       Layer 3: HITL & Observability
  Django HITL Dashboard → Auto-Execution Engine → SQLite Decision Log
  Prometheus + Grafana (scraping all 3 nodes)
```

---

## Repository Structure

```
fyp-pipeline/
├── layer1/                  — Node 1: ingestion, validation, feature extraction, anomaly detection
│   ├── seg/                 — Synthetic Event Generator
│   ├── validator/           — Pydantic schema enforcement
│   ├── feature_store/       — Rolling window feature computation
│   ├── adm/                 — Five anomaly detection models
│   └── rabbitmq/            — RabbitMQ producer
│
├── layer2/                  — Node 2: four AI agents + ChromaDB + Ollama
│   ├── agents/              — Triage, Strategy, Policy, Learning agents
│   ├── chromadb_utils/      — RAG client, query, upsert utilities
│   ├── prompts/             — System prompts for qwen3:1.7b and qwen3:0.6b
│   └── config/              — EMA confidence threshold config
│
├── layer3/                  — Node 3: HITL dashboard, auto-executor, observability
│   ├── dashboard/           — Django project (HITL views, SSE, SQLite ORM)
│   ├── auto_executor/       — Consumes auto.execute queue, logs outcomes
│   └── sqlite_logger/       — Centralised decision log writer
│
├── evaluation/              — Dataset generation, baseline system, metrics calculation
├── Phase_0_Infrastructure/  — Phase 0 cluster setup and LLM benchmark (COMPLETE)
├── datasets/                — Download instructions: NAB, Loghub HDFS, KDD99
├── docs/                    — Project planning and design documents
├── .gitignore
└── README.md
```

---

## Phase Status

| Phase | Description | Status | Deadline |
|:------|:------------|:------:|:---------|
| Phase 0 | Cluster setup + LLM evaluation (qwen3:1.7b selected) | ✅ Complete | 31 Mar 2026 |
| Phase 1 | Layer 1: SEG, Validator, Feature Store, 5 ADM detectors | 🔄 In Progress | 30 Apr 2026 |
| Phase 2 | Layer 2: Four agents + ChromaDB RAG + H1 hypothesis test | ⏳ Planned | 31 May 2026 |
| Phase 3 | Layer 3: Django HITL Dashboard + Auto-Executor | ⏳ Planned | 30 Jun 2026 |
| Phase 4 | Full integration + end-to-end pipeline testing | ⏳ Planned | 15 Jul 2026 |
| Phase 5 | 1,950-event evaluation run + HDFS real-stream replay | ⏳ Planned | 31 Jul 2026 |

---

## Selected Models (Phase 0 Evaluation — Complete)

| Agent | Model | Why Selected |
|:------|:------|:-------------|
| Strategy Agent | `qwen3:1.7b` via Ollama | 90% schema validity on 30 strict adversarial prompts. Only model meeting the production viability hard constraint. All 3 failures traced to fixable engineering issues. |
| Learning Agent | `qwen3:0.6b` via Ollama | Sub-1B RAM budget for Node 2. Formal quality evaluation in Phase 2. |
| Triage Agent | None — rule-based + RAG | LLM not needed. ChromaDB retrieval only. Keeps latency within 3s SLA. |
| Policy Agent | None — pure Python | Deterministic routing table. Zero inference latency. |

Full evaluation details → `Phase_0_Infrastructure/README.md`
Paper-ready summary → `docs/Phase0_Evaluation_Summary.docx`

---

## Evaluation Dataset — 1,950 Events

| Category | Count |
|:---------|------:|
| Normal events (baseline healthy traffic) | 1,000 |
| CPU / Memory Spike | 200 |
| Error Rate Surge (5xx) | 200 |
| Throughput Drop / Silent Crash | 200 |
| Auth Failure Flood | 200 |
| Schema Change — 3 sub-types (missing fields, type mutations, value shifts) | 150 |
| **TOTAL** | **1,950** |

Ground truth labels are stored separately in `evaluation/labels.csv` and are never visible to the pipeline during evaluation runs.

---

## Primary Research Metrics

| Metric | Symbol | Production Target |
|:-------|:-------|:-----------------|
| Mean Time To Acknowledge | MTTA | Median < 30 seconds (nominal path) |
| Mean Time To Remediate | MTTR | Measurably lower than 60s static baseline |
| False Escalation Rate | FER | < 30% at Phase 5 |
| False Automation Rate | FAR | < 5% (safety-critical upper bound) |
| Risk Tier Accuracy | RTA | ≥ 75% at Phase 5 |
| Schema Validity Rate | SVR | ≥ 95% in production (90% baseline from Phase 0) |

---

## Getting Started

Work through the guides in this order:

1. **Cluster infrastructure** → `Phase_0_Infrastructure/User_Guide.md`
2. **Layer 1 (Node 1)** → `layer1/README.md` then `layer1/User_Guide.md`
3. **Layer 2 (Node 2)** → `layer2/README.md` then `layer2/User_Guide.md`
4. **Layer 3 (Node 3)** → `layer3/README.md` then `layer3/User_Guide.md`
5. **Evaluation** → `evaluation/README.md`

---

## Git Branch Strategy

| Branch | Purpose |
|:-------|:--------|
| `main` | Production-quality code only. Tagged at each phase completion. Never commit broken code. |
| `develop` | Integration branch. Feature branches merge here first after unit tests pass. |
| `feature/*` | One branch per component (e.g. `feature/seg`, `feature/triage-agent`, `feature/hitl-dashboard`). |

---

*Full system design, agent I/O contracts, evaluation methodology, and research hypotheses are documented in `docs/System_Design_Methodology_v1.1.docx`.*
