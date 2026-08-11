# FYP Master Reference Document
### Distributed Multi-Agent Coordination for Self-Healing Data Pipelines: A Human-in-the-Loop Approach on Commodity Hardware

**Team:** Muhammad Adeel (23JZBCS0226) & Muhammad Asim
**Supervisor:** Dr. Laeeq Ahmed
**Department:** CS&IT, UET Peshawar — Nowshera Campus
**Document purpose:** Single consolidated reference of everything done so far (Literature Review → Phase 0 Infrastructure → Phase 0 LLM Evaluation → System Design v1.2), current status, known issues, and next steps. Built for reuse with Claude or any other AI assistant without needing to re-upload all source files.
**Last consolidated:** 12 July 2026

---

## 0. Key Dates & Status Snapshot

| Milestone | Date | Status |
|---|---|---|
| Phase 0 deadline (infra + env validation) | 31 March 2026 | ✅ COMPLETE |
| Literature Review submitted (Phase I) | March 2026 | ✅ COMPLETE |
| Phase 0 LLM Evaluation (model selection) | 25 April 2026 | ✅ COMPLETE — qwen3:1.7b selected |
| System Design v1.0 | 31 March 2026 | ✅ COMPLETE |
| System Design v1.1 (model switch documented) | May 2026 | ✅ COMPLETE |
| System Design v1.2 (Fusion Engine added) | May 2026 | ✅ COMPLETE — current version |
| Phase 1 (Layer 1 build: 5 ADM models, RabbitMQ, Fusion Engine) | 1 April – 30 April 2026 (per plan) | 🔶 IN PROGRESS — teammate (Asim) currently implementing Layer 1 |
| Layer 2 (AI Control Plane: Triage/Strategy/Policy/Learning agents) | Starts after Layer 1 complete | ⏳ NOT STARTED — Adeel to begin once Layer 1 is done |
| Layer 3 (HITL Django Gateway + Prometheus/Grafana) | — | ⏳ NOT STARTED (design complete, no implementation yet per files provided) |
| Switch from WiFi to Gigabit Ethernet cluster (real benchmark measurements begin) | 15 July 2026 | 🔶 DUE NOW — confirm this has happened; no paper-citable benchmark numbers before this |
| Codebase freeze (self-imposed) | 31 July 2026 | ⏳ UPCOMING |
| MDPI Big Data & Cognitive Computing submission target | 15 Oct 2026 | ⏳ UPCOMING |
| Dissertation due | 31 Dec 2026 | ⏳ UPCOMING |

**Division of labor (current):** Asim → building Layer 1 (stream-node). Adeel → will start Layer 2 (ai-brain-node) once Layer 1 is complete and handed off.

---

## 1. Chronological Order of Work (what came first)

1. **Literature Review** (submitted March 2026, Phase I) — 4 papers reviewed, gap analysis performed, 5 contributions (C1–C5) drafted, project positioned as first commodity-hardware, multi-agent, empirically-benchmarked self-healing pipeline. At this stage the plan still specified **Phi-4 Mini** as the Strategy Agent model.
2. **System Design & Methodology v1.0** (31 March 2026) — initial full architecture spec, based on the Phi-4 Mini plan and Phase 0 measurements.
3. **Phase 0 Infrastructure Execution** (14–31 March 2026) — 3-node cluster stood up, RabbitMQ+DLX, Ollama, ChromaDB, Prometheus/Grafana, datasets downloaded, and the first 30-prompt quality test run **against Phi-4 Mini**. Result: passed on paper (100% valid JSON, avg score 3.76–3.80/5, Cohen's Kappa 0.5448) but with a critical weak spot — only 43.3% correct risk-tier classification, below the 75% threshold.
4. **Phase 0 LLM Evaluation / Model Selection** (25 April 2026) — a *follow-up, more rigorous* evaluation comparing three candidate models (deepseek-r1:1.5b, qwen3:1.7b, phi4-mini:latest) under a harder "strict" prompt variant. This is where **Phi-4 Mini was formally rejected** (6.7% schema validity, 100% HIGH-risk-tier bias) and **qwen3:1.7b was selected** (90% schema validity, balanced risk-tier distribution). This evaluation supersedes the optimistic Phase 0 checklist numbers — the checklist test used easier prompts; the model-selection test used adversarial ones and is the one that should be cited in the paper.
5. **System Design v1.1** (May 2026) — formally updates the design to qwen3:1.7b (Strategy Agent) and designates qwen3:0.6b (Learning Agent), incorporating engineering fixes (system-prompt constraint, `num_predict` 400→512).
6. **System Design v1.2** (May 2026, current) — adds the **Fusion Engine**, a new Layer 1 component correlating multi-model detection signals before publishing to `anomaly.detected`. Updates data flow, ADM section, Triage Agent contract, Policy Agent routing, MTTA budget (30s → 33s), evaluation metrics (adds FSR, CDR), repo structure, and open questions (adds OQ8).
7. **Layer 1/2/3 architecture diagrams** (HTML mockups, undated but consistent with System Design v1.2) — visual reference for the three physical layers, currently used as the build blueprint. Layer 1 is being implemented now.

**Bottom line on ordering:** Literature Review → Phase 0 Infra → Phase 0 Model Eval (Phi-4 Mini rejected, qwen3:1.7b selected) → System Design v1.0 → v1.1 → v1.2 (current) → Layer 1 implementation (in progress) → Layer 2 (next, Adeel) → Layer 3 (after that).

---

## 2. Literature Review Summary

**Full citation list:**
1. Mayilsamy, M. (2025). *A Comprehensive Survey of Streaming Large Language Models.* JISEM, 10(60s). — Survey.
2. Kirubakaran, A. M. et al. (2025). *Governing Cloud Data Pipelines with Agentic AI.* arXiv:2512.23737. — Methodology.
3. Chakraborty, S. (2025). *Beyond ETL: How AI Agents Are Building Self-Healing Data Pipelines.* JCSTS, 7(3). — Methodology.
4. Kothamasu, L. S. (2025). *Autonomous Resilience: Advancing Data Engineering Through Self-Healing Pipelines and Generative AI.* EJCSIT, 13(28). — Conceptual.

**The unified gap statement (core thesis of the review):**
No existing work implements, deploys, or benchmarks a multi-agent self-healing pipeline on real distributed commodity hardware.
- Mayilsamy: surveys streaming LLM theory, no implementation.
- Kirubakaran (ACDE): closest architectural relative — policy-bounded agentic control, 45% MTTR reduction, 70% fewer manual interventions — but cloud-only, GPU-backed frontier LLMs, no commodity hardware.
- Chakraborty: defines horizontal/vertical agent decomposition conceptually, but no working system, all figures from third-party industry sources.
- Kothamasu: broadest conceptual framing, explicitly admits the sync-path LLM latency problem but proposes no fix.

**Our project's response — 5 contributions (as originally drafted in the Lit Review; superseded/refined by System Design v1.2's C1–C5, see Section 5 below):**
- C1 — Architecture: first commodity/CPU-only, cloud/GPU-free implementation of this system class.
- C2 — Multi-Agent Coordination Protocol: 4 agents (Triage, Strategy, Policy, Learning) with explicit contracts, RabbitMQ coordination, per-agent latency measurement, **compared against a single-agent baseline**.
- C3 — Adaptive Learning in Production: Learning Agent turns ChromaDB from static RAG into an evolving knowledge base.
- C4 — Distributed Commodity Hardware Benchmark: cross-node latency, RabbitMQ throughput, NTP drift, end-to-end timing on real Ethernet cluster.
- C5 (Optional) — Edge vs. Cloud LLM reasoning quality: quantised edge LLM vs. GPT-4o-mini on 30 curated prompts, activated only if API access obtained.

**Methodology patterns adopted from the literature (Section 4 synthesis):**
- **4.1 Decoupled sync/async processing** — Layer 1 (ms-scale ML anomaly detection) never blocks on Layer 2 (LLM reasoning over RabbitMQ). Directly operationalises Kirubakaran/Mayilsamy's core principle.
- **4.2 Policy-bounded autonomy** — Policy Agent routes, never executes; execution authority lives only in the Auto-Executor / HITL Gateway. Mirrors Kirubakaran's separation of reasoning from execution authority.
- **4.3 Evaluation against baseline** — see Section 6 below (Baseline Comparison) for full detail; this is the one methodological pattern Kirubakaran uniquely provides and the only paper with a real baseline.
- **4.4 Knowledge accumulation as a system property** — Learning Agent operationalises what Chakraborty/Kothamasu only describe conceptually: per-incident ChromaDB upserts, EMA confidence threshold recalibration, negative-example tagging for rejected HITL decisions.

**⚠ Note on staleness:** The Lit Review's "Relevance to Our Research" sections still describe the model as **Phi-4 Mini** throughout (this was accurate as of March 2026 but has since been superseded — see Section 4 below). Treat the Lit Review as a historical Phase I artifact; when citing model choice in the final paper, use qwen3:1.7b and optionally narrate the empirical switch as a methodological finding (a strength, not a weakness — it demonstrates rigorous model-selection methodology).

---

## 3. Phase 0 — Infrastructure Execution (14–31 March 2026)

**Goal:** No application code. Fully verified, SSH-accessible 3-node cluster; all software installed; datasets downloaded; LLM validated with a 30-prompt test.

### 3.1 Cluster / Node Roles

| Node | Hardware | OS | Role | Static IP |
|---|---|---|---|---|
| Node 1 — stream-node | AMD Ryzen 5 7340U / 8GB / 256GB NVMe | Ubuntu 24.04 Desktop | Layer 1: SEG, Stream Processor, ADM, RabbitMQ | 192.168.18.101 |
| Node 2 — ai-brain-node | AMD Ryzen 5 7340U / 8GB / 256GB NVMe | Ubuntu 24.04 Server (headless) | Layer 2: Ollama, LLMs, ChromaDB, 4 agents | 192.168.18.102 |
| Node 3 — gateway-node | Intel Core i5 8th Gen / 8GB / 256GB SATA | Ubuntu 24.04 Desktop | Layer 3: Django HITL, Prometheus, Grafana | 192.168.18.103 |

Router/Gateway: 192.168.18.1. **WiFi was used for Phase 0 only** — cutover to Gigabit Ethernet scheduled for **15 July 2026** (today is 12 July 2026 — confirm whether this cutover has happened; no benchmark numbers taken before that date are citable in the paper).

### 3.2 Phase 0 Deliverables — all ✅ complete
- All 3 nodes: static IPs, hostnames, passwordless SSH (all 6 directions).
- RabbitMQ + Dead Letter Exchange (DLX) operational on Node 1.
- Ollama + Phi-4 Mini (Q4_K_M) installed and responding on Node 2 *(superseded by qwen3:1.7b — see Section 4)*.
- ChromaDB installed and smoke-tested on Node 2.
- Prometheus + Grafana operational on Node 3, scraping all 3 nodes.
- All 3 datasets downloaded: NAB, Loghub HDFS, KDD99.
- 30-prompt quality test completed, both students scored independently.
- NTP sync verified across all 3 nodes (chrony).

### 3.3 Phase 0 Results Log (baseline cluster measurements)

| Measurement | Value |
|---|---|
| NTP offset — stream-node | 0.000021146s |
| NTP offset — ai-brain-node | 0.016272109s |
| NTP offset — gateway-node | 0.000009871s |
| WiFi latency Node1→Node2 (avg) | 57.875 ms |
| WiFi latency Node1→Node3 (avg) | 13.837 ms |
| WiFi latency Node2→Node3 (avg) | 21.748 ms |
| Free RAM Node1 / Node2 / Node3 (idle) | 5.1 GB / 6.2 GB / 5.6 GB |
| Free RAM Node2 with Ollama loaded | 3.6 GB |

### 3.4 Initial 30-Prompt Test (against Phi-4 Mini, checklist version)

This was the **first** quality test, run with an improved (schema-strict) system prompt after an initial poor result:

| Metric | Result | Threshold |
|---|---|---|
| Valid JSON rate | 100% (30/30) | ≥80% |
| Correct risk-tier classification | 43.3% (13/30) | ≥75% ❌ |
| Avg score/prompt (Adeel / Asim) | 3.76 / 3.80 | ≥3.5 |
| Cohen's Kappa | 0.5448 | ≥0.5 (borderline — below the "substantial agreement" ≥0.6 bar stated in the escalation table) |
| Avg tokens/sec | 4.44 | — |
| PASS/FAIL decision recorded | Overall Pass (proceed) | — |

**Note:** this test technically "passed" per the checklist's overall pass/fail logic, but risk-tier classification failed its own threshold (43.3% vs required 75%). This is what motivated the deeper Phase 0 LLM Evaluation in April (Section 4) rather than proceeding straight to Phase 1 with Phi-4 Mini.

⚠ **Minor doc issue:** the Phase 0 Execution Guide's Prometheus/Grafana access URLs are written as `http://192.168.1.103:...` (missing the "18") in several places — should be `192.168.18.103`. Likely a typo only, not an operational error, but worth fixing if this doc is reused/extended.

---

## 4. Phase 0 LLM Evaluation & Model Selection (25 April 2026) — THE MODEL SWITCH, EXPLAINED

This is the evaluation that formally replaced Phi-4 Mini with qwen3:1.7b. It used a **harder, adversarial "strict" prompt variant** (noisy/conflicting signals, ambiguous categories, edge-case severities, multi-component incidents) — deliberately more production-realistic than the original checklist test in Section 3.4.

**Hardware/inference environment:** Node 2 (ai-brain-node), Ollama, no GPU/cloud, `num_ctx=2048` for all models, `num_predict=400` during evaluation (raised to 512 for production).

### 4.1 Models evaluated

| Model | Params | Type | RAM (4-bit) |
|---|---|---|---|
| deepseek-r1:1.5b | 1.5B | Reasoning / Chain-of-Thought | ~0.9 GB |
| **qwen3:1.7b** | 1.7B | Instruction-following / JSON | ~1.1 GB |
| phi4-mini:latest | ~3.8B | General instruction-following | ~2.6 GB |

*(phi4-mini:reasoning variant was excluded before this evaluation even started — its CoT output structurally prevents valid JSON generation.)*

### 4.2 Head-to-head results (strict variant, 30 prompts each)

| Metric | deepseek-r1:1.5b | **qwen3:1.7b ✓ SELECTED** | phi4-mini:latest |
|---|---|---|---|
| JSON Valid % | 6.7% 🔴 | 96.7% 🟢 | 30.0% 🟡 |
| Schema Valid % | 0.0% 🔴 | 90.0% 🟢 | 6.7% 🔴 |
| Risk Tier LOW count | 1 | 11 | 0 |
| Risk Tier HIGH count | 0 | 18 | 9 (100% of parseable) |
| Avg response time | 19.69s | 20.19s | 13.47s (fastest) |
| Avg tokens/sec | 21.03 🟢 | 16.71 | 8.56 🔴 |
| Est. RAM (4-bit) | ~0.9GB | ~1.1GB | ~2.6GB |
| Viable for production? | NO | **YES** | NO |

### 4.3 Why each model was rejected/selected

- **deepseek-r1:1.5b — REJECTED.** 0% schema validity. Its chain-of-thought architecture produces prose before/after the JSON block, structurally breaking parsability — same failure mode as phi4-mini:reasoning.
- **phi4-mini:latest — REJECTED.** Only 6.7% schema validity *and* a systematic calibration failure: 100% of its parseable responses were classified HIGH risk tier (0% LOW). In production this would route every LOW/MEDIUM incident to a human, eliminating autonomous recovery — the system's entire purpose. Its speed advantage (33% faster) is irrelevant below the schema-validity threshold (a fast invalid response generates more operational overhead — error handling, HITL escalation, retries — than a slower valid one).
- **qwen3:1.7b — SELECTED.** 90% schema validity (only model meeting the hard constraint), balanced risk-tier distribution (11 LOW : 18 HIGH, matching ground-truth spread), calibrated confidence scores that track genuine ambiguity (MEDIUM prompts scored 0.70–0.85 vs CRITICAL prompts 0.85–0.95 — treating severity as real uncertainty, not a template), and domain-aware reasoning (e.g., correctly recommending full node isolation only for the coordinated multi-node CRITICAL auth-flood prompt, not for single-node HIGH prompts).

### 4.4 The 3 qwen3:1.7b failures — all engineering artifacts, not capability limits

| Prompt | Failure | Root Cause | Fix |
|---|---|---|---|
| CPU_03 | Extra fields in output | Model echoed input context fields | System prompt: "Output ONLY these 7 fields... do NOT include any other keys from the input" |
| AUTH_03 | Extra fields in output | Same pattern | Same fix |
| THR_06 | JSON truncated mid-string | `num_predict=400` too low for complex multi-component prompt | `num_predict` raised to 512 for production |

With both fixes applied, estimated production schema validity is **100% (30/30)** on the same test set — 90% is a conservative lower bound.

### 4.5 Final agent/model assignment

| Agent | Model | Rationale |
|---|---|---|
| Triage Agent | None (rule-based + ChromaDB RAG) | Keeps latency within 3s SLA — no LLM call |
| **Strategy Agent** | **qwen3:1.7b via Ollama** | Selected in this evaluation; 90% schema valid (est. 100% w/ fixes) |
| Policy Agent | None (pure Python, deterministic tiered routing) | ≤500ms SLA, no ML/LLM |
| Learning Agent | qwen3:0.6b (designated) | Sub-1B-class param budget for RAM compliance; formal evaluation deferred to Phase 2 |

**Phase 0 status: COMPLETE.** Model selection is final; qwen3:1.7b is the Strategy Agent going into Phase 1.

---

## 5. System Design & Methodology v1.2 (current version, May 2026)

### 5.1 Research Hypothesis

A four-agent, policy-bounded self-healing data pipeline deployed on a three-node commodity CPU-only cluster — using qwen3:1.7b (Strategy Agent) and qwen3:0.6b (Learning Agent) via Ollama — can achieve measurably lower MTTA and MTTR than a threshold-only static baseline, while maintaining safe HITL escalation for high-risk decisions, on real distributed hardware with no cloud/GPU dependency.

### 5.2 Five Research Contributions (current, v1.2 — supersedes the Lit Review's original C1–C5 wording)

| ID | Label | Statement |
|---|---|---|
| C1 | Architecture | Fully implemented three-layer tiered hybrid agentic framework, incorporating a Fusion Engine for multi-model signal correlation and compound incident detection; first paper to deploy/benchmark this class of system without cloud or GPU dependency |
| C2 | Multi-Agent Protocol | 4-agent system (Triage, Strategy, Policy, Learning) with explicit I/O contracts, dual-exchange RabbitMQ coordination including Fusion Engine correlation, per-agent latency measurement, **and empirical comparison against a single-agent baseline** |
| C3 | Adaptive Learning | Learning Agent converts ChromaDB from static RAG store into an evolving knowledge base via per-incident feedback ingestion |
| C4 | Hardware Benchmark | Cross-node latency, RabbitMQ throughput, NTP drift, Fusion Engine correlation overhead, end-to-end pipeline timing on a real 3-node Ethernet cluster |
| C5 (Optional) | Edge vs. Cloud LLM | qwen3:1.7b vs. GPT-4o-mini on 30 curated prompts — activated if API access obtained, else Future Work |

### 5.3 Three-Layer Architecture

| Layer | Node | Hardware | Responsibilities |
|---|---|---|---|
| Layer 1 — Real-Time Data Plane | Node 1, stream-node | AMD Ryzen 5, 8GB, Ubuntu Desktop | SEG, Pydantic Validator, Feature Store, 5-model ADM, **Fusion Engine** (signal correlation + compound merging), dual-exchange RabbitMQ + DLX, dataset storage |
| Layer 2 — AI Control Plane | Node 2, ai-brain-node | AMD Ryzen 5, 8GB, Ubuntu Server headless | Ollama serving qwen3:1.7b (Strategy) + qwen3:0.6b (Learning), ChromaDB, Triage Agent (rule-based + RAG), Policy Agent |
| Layer 3 — HITL & Observability | Node 3, gateway-node | Intel i5, 8GB, Ubuntu Desktop | Django HITL Dashboard, Auto-Executor, SQLite decision log, Prometheus + Grafana |

### 5.4 End-to-End Data Flow (Steps 1–9)

1. **SEG** (Layer 1) generates/replays labelled synthetic events → `raw.events`.
2. **Pydantic Validator**: valid events → Feature Store; structural violations → repackaged as `schema_drift` anomaly, published **directly** to `anomaly.detected`, bypassing Feature Store and Fusion Engine entirely.
3. **Feature Store**: rolling-window feature extraction per (node, component); appends `feature_vector`.
4a. **Detection Fanout**: ADM Runner publishes enriched event to `detection.fanout` Topic Exchange → all 5 detectors process in parallel.
4b. **Fusion Engine correlation** *(new in v1.2)*: each detector publishes lightweight result to `fusion.results`; Fusion Engine correlates all responses for the same `event_id` within a 3s window, applies confidence scoring, and publishes exactly one enriched event to `anomaly.detected` (never more than one per original event). CRITICAL-severity + high-weight-model detections bypass the window and publish immediately (fast-path).
5. **Triage Agent** (Layer 2): consumes `anomaly.detected`, uses `fusion_confidence`/`fusion_type`, fetches ≤3 ChromaDB RAG examples → `triage.result`. SLA ≤3s.
6. **Strategy Agent**: consumes `triage.result`, calls qwen3:1.7b via Ollama with incident + RAG context, returns 7-field JSON → `strategy.result`. SLA ≤25s.
7. **Policy Agent**: tiered routing table using LLM confidence + `fusion_confidence` → `auto.execute` or `hitl.queue`. SLA ≤1s (≤500ms target).
8a. **Auto-Execution Engine** (Layer 3): consumes `auto.execute`, logs to SQLite, executes simulated remediation, feeds `outcome.feedback`.
8b. **HITL Gateway** (Layer 3): consumes `hitl.queue`, shows full reasoning chain to operator, routes approvals to `auto.execute`, feeds decisions to Learning Agent.
9. **Learning Agent**: consumes `outcome.feedback`, uses qwen3:0.6b to summarise, upserts ChromaDB, recalibrates confidence threshold via EMA. Zero latency impact on remediation path (fires post-dispatch).

### 5.5 Fusion Engine (new in v1.2) — the key Layer 1 addition

**Why it exists:** a real failure often triggers multiple detectors at once (e.g., CPU spike → throughput drop → error surge). Without fusion, this becomes 3 separate incidents processed independently by Triage. The Fusion Engine correlates same-`event_id` signals within a 3-second window and publishes **one** enriched decision.

**Two-exchange architecture:**
- `detection.fanout` (Topic Exchange, internal to Layer 1) — ADM Runner fans every enriched event out to all 5 detectors in parallel.
- `fusion.results` (internal queue) — each detector publishes its individual result here (even `detected: false`, so Fusion Engine knows the model processed the event).
- `anomaly.detected` (pipeline queue, consumed by Layer 2) — Fusion Engine publishes fused incidents here; Pydantic schema violations also land here directly (bypass).

**Per-model confidence weights:**

| Model | Weight | Rationale |
|---|---|---|
| Isolation Forest (CPU/Memory) | 0.85 | ML-trained on real NAB data |
| Random Forest + Rate-gate (Auth) | 0.85 | ML + hard-threshold confirmation |
| PSI Detector (Schema Drift) | 0.80 | Structural violations unambiguous; statistical PSI slightly noisier |
| Z-Score (Error Rate) | 0.75 | Reliable but can lag on step changes |
| Moving Average (Throughput) | 0.70 | Can lag on fast transitions |

**Four fusion decision cases:**

| Case | Condition | Action | `fusion_type` |
|---|---|---|---|
| 1 — Suppress | No model detects anything in window | Publish nothing; log suppression counter | N/A |
| 2 — Confirmed Single | One model detects, confidence >0.75 | Publish single-model anomaly | `single` |
| 3 — Low Confidence | One model detects, confidence <0.75 | Publish anyway; Policy Agent forces HITL | `low_confidence` |
| 4 — Compound | ≥2 models detect within window | Merge into one compound incident; severity = highest fired; `contributing_models` = list | `compound` |

**CRITICAL fast-path:** any detector firing CRITICAL with model weight ≥0.80 bypasses the 3s window entirely and publishes immediately.

**Latency budget impact:** Fusion Engine window adds up to +3.0s (0s on fast-path). Updated end-to-end MTTA target: **≤33s** (was ≤30s in v1.1) = 3s fusion + 3s triage + 25s LLM + ~1–2s policy/overhead.

### 5.6 Multi-Agent Design — Contracts & SLAs

| Agent | Node/Process | Input → Output Queue | SLA / Timeout | Timeout behavior |
|---|---|---|---|---|
| Triage | Node 2, Proc 1 | `anomaly.detected` → `triage.result` | ≤3s / 5s | HITL with `triage_timeout` flag |
| Strategy | Node 2, Proc 2 | `triage.result` → `strategy.result` | ≤25s / 30s | HITL with `llm_timeout` flag |
| Policy | Node 2, Proc 3 | `strategy.result` → `auto.execute`/`hitl.queue` | ≤500ms / 2s | HITL with `policy_exception` flag |
| Learning | Node 2, Proc 4 | `outcome.feedback` → ChromaDB (no output queue) | ≤5s / 10s | Logs failure, skips — never blocks pipeline |

**Policy Agent tiered routing table:**

| Priority | risk_tier | confidence | fusion_type/error | Decision | Route |
|---|---|---|---|---|---|
| 1 | Any | Any | `timed_out` or `parse_error` | Mandatory HITL | HITL |
| 2 | Any | Any | `low_confidence` (Fusion) | Mandatory HITL, overrides everything | HITL |
| 3 | HIGH | Any | any | Always HITL | HITL |
| 4 | LOW | <0.65 | single/false | Low-risk but uncertain | HITL |
| 5 | LOW | ≥0.65 | single/compound | Safe for auto-remediation | AUTO |

### 5.7 ChromaDB / RAG (unchanged since v1.1)
- Embedding model: all-MiniLM-L6-v2 (384-dim).
- RAG protocol: similarity query → outcome filter → risk-tier balance check → 3-example context assembly, injected into Strategy Agent prompt as a HISTORICAL CONTEXT block.
- **Testable hypothesis H1**: RAG context improves risk-tier accuracy to ≥80% (Phase 2 milestone, 31 May 2026).
- Learning Agent updates ChromaDB per outcome type; EMA confidence-threshold recalibration (α=0.9, bounds [0.60, 0.90]).

### 5.8 Anomaly Detection Module — 5 models (v1.2: each now publishes to `fusion.results`, not directly to `anomaly.detected`)

| Model | Algorithm | Dataset | Key Hyperparameters | Routing Key |
|---|---|---|---|---|
| 1 — CPU/Memory Spike | Isolation Forest | NAB (cpu_utilization_asg_misconfig + machine_temp) | contamination=0.05, n_estimators=100, seed=42 | detect.cpu |
| 2 — Error Rate Surge | Statistical Z-Score | NAB Twitter_volume + KDD99 connection_failure | window=30, \|Z\|>3.0 | detect.error |
| 3 — Throughput Drop | Moving Average Deviation | NAB ambient_temperature_system_failure | drop_threshold=0.40, silence_timeout=30s | detect.throughput |
| 4 — Auth Failure Flood | Rate-Gate + Random Forest | KDD99 REJ connections | rate_threshold=20/min, RF n_estimators=50, max_depth=10 | detect.auth |
| 5 — Schema Drift | Pydantic Validator + PSI Detector | Loghub HDFS + synthetic mutations | PSI: 0.2 (MEDIUM), 0.5 (HIGH) | detect.schema |

### 5.9 Evaluation Dataset — 1,950 Events

| Category | Count | Notes |
|---|---|---|
| Normal | 1,000 | Baseline healthy traffic |
| CPU/Memory Spike | 200 | 100 HIGH / 60 MEDIUM / 40 CRITICAL |
| Error Rate Surge | 200 | 100 HIGH / 60 MEDIUM / 40 CRITICAL |
| Throughput Drop | 200 | 100 HIGH / 60 MEDIUM / 40 CRITICAL |
| Auth Failure Flood | 200 | 100 HIGH / 60 MEDIUM / 40 CRITICAL |
| Schema Change (3 sub-types) | 150 | 50 missing-field / 50 type-mutation / 50 value-shift |
| **TOTAL** | **1,950** | Fully labelled; ground truth stored separately in `labels.csv` |

### 5.10 Evaluation Methodology (Section 7 of System Design — UPDATED with baseline detail)

| Evaluation Component | Description |
|---|---|
| **Primary Evaluation** | Full 1,950-event replay: agentic system (with Fusion Engine) vs. **threshold-only static baseline** (no AI, no agents, static if/else rules). Measures MTTA, MTTR, FER, FAR, RTA, SVR, Fusion suppression rate. This is the core "does agentic self-healing beat the traditional approach" comparison. |
| **Single-agent baseline comparison** *(supports Contribution C2 directly)* | Same 1,950-event corpus, one LLM call per anomaly with no agent decomposition (no separate Triage/Policy/Learning stages) vs. the full 4-agent pipeline. Isolates whether multi-agent decomposition itself adds value beyond just "having an LLM in the loop." |
| Fusion Engine Controlled Test | 200 CPU-spike events, Fusion Engine enabled vs. disabled. Measures false-positive rate, compound detection rate, MTTA delta. |
| RAG Improvement Test (H1) | 30-prompt test re-run with RAG context injected. Phase 2 milestone. |
| Learning Agent Improvement | First 20% vs. last 20% of the 1,950-event run — tests ChromaDB accumulation improving Triage recall over time. |
| HITL Latency Measurement | Time from `hitl.queue` arrival to operator decision. Target: median <120s. |
| Throughput Benchmark | Messages/sec at 1/5/10 events/sec, with and without Fusion Engine window. |
| 30-Minute HDFS Replay (Phase 5) | Real-stream replay at 1x speed — external validity evidence. |

**Primary metrics:** MTTA (median target ≤33s), MTTR, False Escalation Rate (FER, target <30%), False Automation Rate (FAR, target <5% — safety-critical), Risk Tier Accuracy (RTA, target ≥75%), Schema Validity Rate (SVR, Phase 0 baseline 90%, production target ≥95%), Fusion Suppression Rate (FSR, new in v1.2), Compound Detection Rate (CDR, new in v1.2), Pipeline Throughput (PT), Cohen's Kappa (Phase 2 target κ≥0.6).

### 5.11 Node 2 Memory Budget

Total nominal ~3.8GB, peak (embedding) ~4.9GB, against 8.0GB total / 6.2GB free-at-idle (Phase 0 measured) → ~3.1GB headroom at peak. Fusion Engine runs on **Node 1**, adds only ~50MB RSS there (well within the 5.1GB free RAM), does not affect Node 2 budget.

### 5.12 Repository Structure (v1.2)

```
fyp-pipeline/
├── layer1/                      # Node 1 — stream-node
│   ├── seg/                     # Synthetic Event Generator
│   ├── validator/                # Pydantic + schema_drift bypass router
│   ├── feature_store/
│   ├── adm/
│   │   ├── detectors/            # 5 detectors — now publish to fusion.results
│   │   ├── models/                # trained .pkl files
│   │   └── adm_runner.py          # fans out via detection.fanout exchange
│   ├── fusion_engine/             # ← NEW in v1.2
│   │   ├── fusion_engine.py       # correlation window + 4-case decision logic
│   │   └── confidence_scorer.py
│   ├── rabbitmq/
│   └── requirements_node1.txt
├── layer2/                       # Node 2 — ai-brain-node
│   ├── agents/                    # triage_agent.py, strategy_agent.py, policy_agent.py, learning_agent.py
│   ├── chromadb_utils/
│   ├── prompts/
│   ├── config/threshold_config.json
│   └── requirements_node2.txt
├── layer3/                       # Node 3 — gateway-node
│   ├── dashboard/hitl/
│   ├── auto_executor/
│   ├── sqlite_logger/
│   └── requirements_node3.txt
├── evaluation/
├── Phase_0_Infrastructure/
├── datasets/
├── docs/
└── README.md
```

**Git strategy:** 3 branches — `main` (production, both review every merge, tagged per phase), `develop` (integration, requires end-to-end demo before merge to main), `feature/*` (one per component, e.g. `feature/fusion-engine`).

---

## 6. Layer 1 / Layer 2 / Layer 3 Diagrams — Cross-Reference to System Design

You provided three HTML architecture diagrams (visual build blueprints). They match System Design v1.2 closely, confirming the design is implementation-ready:

- **layer1.html** — Synthetic Ingestion → Fusion Engine. Shows: SEG → `raw.events` → Pydantic Validator (with invalid-event bypass straight down to `anomaly.detected`, matching Section 5.4 Step 2) → `validated.event` → ADM Runner + Feature Store → fanout to 5 detectors (`detect.cpu`, `detect.error`, `detect.throughput`, `detect.auth`, `detect.schema`) → `fusion.results` → Fusion Engine (3-second window) → `anomaly.detected`. **This is the layer currently being implemented (by Asim).**
- **layer2.html** — AI Control Plane on ai-brain-node (192.168.18.102). Shows: `anomaly.detected` → Triage Agent (Rule-Based + RAG, SLA ≤3s) → `triage.result` → Strategy Agent (**qwen3:1.7b**, SLA ≤25s, 7-field JSON) → `strategy.result` → Policy Agent (Tiered Routing Table, SLA ≤500ms) → `auto.execute` / `hitl.queue`. Also shows ChromaDB (`incident_history`) and Ollama API (serving qwen3:1.7b & qwen3:0.6b) as supporting services, and the feedback loop: `outcome.feedback` → Learning Agent (**qwen3:0.6b**, updates EMA threshold). **Confirms the model names are already correctly updated to qwen3 in the diagram — no lingering Phi-4 Mini references here.** This is the next layer to build (Adeel, once Layer 1 is handed off).
- **layer3.html** — HITL & Observability on gateway-node. Shows: `auto.execute` → Auto-Executor (runs remediation automatically); `hitl.queue` → Django Dashboard (operator review/override); both write to SQLite DB (Decision Log & State Management) → `outcome.feedback` (consumed by Node 2 Learning Agent). Separately: Prometheus scrapes Nodes 1 & 2 (ports 9100, 8010–8013) → Grafana dashboards (Latency, TPS, Node Health). Tracked metrics: Agent Latency (Triage, Strategy), LLM Tokens/sec, Hardware Limits (CPU/RAM), Queue Depths & Throughput.

**Build order implied by dependencies:** Layer 1 must exist first since it's the sole producer of `anomaly.detected`. Layer 2 depends on Layer 1's output queue and is next. Layer 3 depends on Layer 2's `auto.execute`/`hitl.queue` outputs and the `outcome.feedback` loop back into Layer 2's Learning Agent — so it's naturally last, though Prometheus/Grafana scraping infrastructure was already stood up in Phase 0 and doesn't need to wait.

---

## 7. Open Questions Requiring Resolution (from System Design v1.2, Section 11)

| # | Question | Resolution Method | Owner | Deadline |
|---|---|---|---|---|
| OQ1 | Does RAG context injection improve qwen3:1.7b risk-tier accuracy to ≥80%? (H1) | Augmented 30-prompt test with pre-populated ChromaDB | Both | 31 May 2026 |
| OQ2 | Actual Node 2 peak RAM under concurrent qwen3:1.7b + qwen3:0.6b + full agent load? | Run all 4 agents + both models, monitor `/proc/[PID]/status` peak RSS | Adeel | 21 May 2026 |
| OQ3 | Can sentence-transformers embedding and qwen3 inference run safely concurrently? | Concurrent load test | Adeel | 21 May 2026 |
| OQ4 | Optimal ChromaDB collection size before retrieval latency >1s? | Benchmark at 100/500/1000/2000/5000 docs | Asim | 30 Apr 2026 |
| OQ5 | Does qwen3:0.6b produce adequate summarisation quality for ChromaDB storage? | Evaluate 20 sample outcome summaries | Both | 30 Apr 2026 |
| OQ6 | Does the EMA confidence threshold converge over 1,950 events or oscillate? | Plot threshold vs. event number during Phase 5 run | Both | 31 Jul 2026 |
| OQ7 | Does Pydantic validation overhead add measurable latency at 10 events/sec? | Throughput benchmark with/without validator | Adeel | 30 Jun 2026 |
| OQ8 (new v1.2) | Does the Fusion Engine reduce false positives reaching Layer 2, and what's the compound detection rate? Is the 3s window overhead justified? | 200 CPU-spike events, Fusion Engine on/off; record FPR, CDR, MTTA delta | Asim | 30 Jun 2026 |

**Note:** several of these (OQ4, OQ5) are already past their stated deadline (30 Apr 2026) as of today (12 Jul 2026) — worth confirming status/results when you next sync with your supervisor, or updating the deadlines if not yet done.

---

## 8. Known Issues / Inconsistencies Log

Track and resolve these as you go — flagged during this consolidation:

1. **Model name drift across documents.** Literature Review (March 2026) and the original Phase 0 Execution Guide describe **Phi-4 Mini** as the Strategy Agent model. This was empirically rejected in the 25 April 2026 evaluation in favor of **qwen3:1.7b** (System Design v1.1/v1.2, layer2.html all correctly show qwen3). The Lit Review's contribution statements haven't been updated to reflect this — treat it as a historical Phase I snapshot; decide explicitly whether your final paper's positioning section restates the contribution with qwen3:1.7b or explicitly narrates the empirical model-selection process as a finding.
2. **IP typo in Phase 0 doc.** `http://192.168.1.103:...` appears several times for Prometheus/Grafana access URLs; actual gateway-node IP is `192.168.18.103`. Likely just a documentation typo, not a runtime error — worth a fix pass if this doc is extended.
3. **MTTA target has moved twice.** Lit Review references a "sub-10s MTTA" for Layer 1 alone (pre-Fusion-Engine framing); System Design v1.1 set end-to-end MTTA ≤30s; v1.2 revised it to ≤33s after adding the Fusion Engine's 3s window. Use ≤33s as current truth; the sub-10s figure is stale if quoted elsewhere.
4. **Checklist test vs. model-selection test discrepancy.** The Phase 0 checklist 30-prompt test (Section 3.4) reported an *overall pass* despite risk-tier classification failing its own 75% threshold (only 43.3% achieved). The April model-selection evaluation (Section 4) is the one that should be cited in the paper — it's methodologically stronger (adversarial "strict" variant) and it's the one that actually triggered the Phi-4 Mini → qwen3:1.7b switch.
5. **Ethernet cutover timing.** Per the Phase 0 doc, all paper-citable benchmark measurements require the Gigabit Ethernet cluster, scheduled to go live **15 July 2026** — three days from today. Confirm whether this has happened or is still pending before treating any new benchmark numbers as final/citable.
6. **Evaluation table gap (now fixed in this document).** System Design v1.2's Contribution C2 commits to a "single-agent baseline" comparison, but the Section 7 evaluation table didn't list it as a distinct test — added explicitly in Section 5.10 above, tied to C2.

---

## 9. Current Status & Immediate Next Steps

- **Layer 1 (stream-node):** in progress — Asim implementing SEG, Validator, Feature Store, 5 ADM detectors, Fusion Engine, dual-exchange RabbitMQ per `layer1.html` and System Design §2.4–2.7.
- **Layer 2 (ai-brain-node):** not started — Adeel to begin once Layer 1 is handed off and producing `anomaly.detected` events correctly. Build order: Triage Agent (rule-based + RAG) → Strategy Agent (qwen3:1.7b wrapper around Ollama, 7-field JSON contract) → Policy Agent (tiered routing table) → Learning Agent (qwen3:0.6b + ChromaDB + EMA).
- **Layer 3 (gateway-node):** not started at the application level (Django HITL, Auto-Executor, SQLite logger) — but Prometheus/Grafana monitoring infrastructure is already live from Phase 0.
- **Immediate open items:** confirm Ethernet cutover status (Issue #5 above); check on overdue OQ4/OQ5 (Section 7); decide how to handle the Phi-4 Mini legacy references in the Lit Review for the final paper (Issue #1).

---

## 10. Monitoring Plan — Prometheus Scrape Jobs & Grafana Dashboards

**Decision: two Grafana dashboards, not three.** Cluster hardware stays on its own dashboard; the Fusion Engine's metric lives with the Layer 2 agents rather than getting a separate dashboard — the Fusion Engine's suppression behavior directly shapes what reaches the agents, so it belongs in the same operational view rather than next to CPU/RAM panels.

### 10.1 Prometheus Scrape Jobs (two jobs)

**Job 1 — `fyp-cluster`** (Port 9100, Node Exporter, all 3 nodes: `stream-node`, `ai-brain-node`, `gateway-node`)
- CPU & RAM utilization — validates commodity-hardware / CPU-only LLM inference memory budgets, identifies peak usage constraints.
- Disk & Network I/O — monitors ChromaDB persistent store and inter-node RabbitMQ traffic latency.

**Job 2 — `fyp-agent-pipeline`** *(renamed from `fyp-layer2-agents` — now covers Layer 2 agents **and** the Layer 1 Fusion Engine, since it's scraped alongside the agents it directly feeds)*
- **Triage Agent (Port 8010):** `fyp_triage_latency_s` (execution time histogram), `fyp_triage_processed_total` (by anomaly type), `fyp_triage_timeout_total` (SLA misses).
- **Strategy Agent (Port 8011):** `fyp_strategy_latency_s` (LLM inference time), `fyp_strategy_schema_valid_total` / `fyp_strategy_schema_invalid_total` (JSON adherence), `fyp_strategy_timeout_total`, `fyp_strategy_tokens_per_s`.
- **Policy Agent (Port 8012):** `fyp_policy_latency_s`, `fyp_routing_decision_total` (split by auto-execute vs. HITL escalation reason).
- **Learning Agent (Port 8013):** `fyp_learning_outcomes_total`, `fyp_learning_threshold_updates_total` (EMA adjustments), `fyp_learning_chromadb_upserts_total`.
- **Fusion Engine (Layer 1, scraped here — not with cluster hardware):** `fusion_suppressed_total` (normal events filtered before reaching Layer 2), plus `fusion_confidence` distribution and `fusion_type` breakdown (single/compound/low_confidence) once instrumented — supports OQ8 (FSR/CDR) directly.

### 10.2 Grafana Dashboards (two, confirmed)

**Dashboard 1 — Node & Cluster Infrastructure** (mirrors `fyp-cluster` job)
- CPU load, memory thresholds, network throughput across all 3 nodes; NTP time-sync offsets.
- Purpose: commodity-hardware evidence (supports Contribution C4) and confirms Node 2 RAM headroom during concurrent LLM generation.

**Dashboard 2 — Agent Pipeline & Fusion Engine Performance** *(renamed from "AI Multi-Agent Pipeline Performance" to reflect the Fusion Engine addition; mirrors `fyp-agent-pipeline` job)*
- End-to-end MTTA tracking (target ≤33s), per-agent latency (Triage/Strategy/Policy/Learning), LLM token generation rate, schema validity %.
- Routing trends: auto-executed vs. escalated (and why — low confidence, timeout, fusion low-confidence override).
- **Fusion Engine panels (new):** suppression rate over time, compound vs. single vs. low-confidence event mix, fast-path (CRITICAL bypass) frequency — sitting next to Triage Agent latency so you can see, in one view, how much the Fusion Engine's filtering is shaping what Triage actually receives.

Rationale for keeping it at two dashboards: splitting hardware from application/pipeline metrics avoids digging through disk I/O panels to find an LLM timeout counter, while keeping Fusion Engine with the agents (rather than a third dashboard) keeps the full `anomaly.detected`-to-`outcome.feedback` story — including what got filtered out before Triage ever saw it — in a single operational view.

---

## 11. Paper Deliverables — Tables, Graphs, and Comparisons to Produce

Consolidated checklist of every table/figure/comparison implied by the System Design, evaluation methodology, and Phase 0 results — organized by where it lands in the paper. Use this as the master list when building the evaluation section; check items off as they're generated from real (post-Ethernet-cutover) data.

### 11.1 Phase 0 / Model Selection Tables (Related Work → Methodology transition)
- [ ] **Table — Head-to-head LLM comparison** (deepseek-r1:1.5b vs. qwen3:1.7b vs. phi4-mini:latest): JSON valid %, schema valid %, risk-tier LOW/HIGH counts, avg response time, tokens/sec, RAM footprint, viable-for-production verdict. (Already compiled in Section 4.2 of this document — ready to drop into the paper as-is.)
- [ ] **Table — qwen3:1.7b failure analysis** (3 non-passing responses): prompt, failure type, root cause, fix applied. (Section 4.4.)
- [ ] **Table — Severity-to-action calibration** for qwen3:1.7b: severity level → observed language pattern → action urgency → confidence range. (From Phase0_Evaluation_Summary §7.1.)
- [ ] **Table — Cluster hardware specification** (commodity-hardware evidence): node, hardware, OS, role, static IP. (Section 3.1 of this document.)
- [ ] **Table — Cluster baseline resource measurements**: idle free RAM per node, free RAM under Ollama load, NTP offsets, WiFi latency between nodes (Phase 0, pre-Ethernet). (Section 3.3.)

### 11.2 System Architecture Figures (System Design / Architecture section)
- [ ] **Figure — Three-layer architecture diagram** (Layer 1 → Layer 2 → Layer 3, node/hardware/role mapping). Can be adapted directly from `layer1.html`/`layer2.html`/`layer3.html`.
- [ ] **Figure — End-to-end data/message flow diagram** (SEG → Validator → Feature Store → Fusion Engine → Triage → Strategy → Policy → Auto-Execute/HITL → Learning Agent feedback loop), annotated with per-stage SLA/latency budget.
- [ ] **Table — Agent contracts summary**: agent, node/process, input→output queue, SLA, timeout behavior. (Section 5.6.)
- [ ] **Table — Policy Agent tiered routing table** (5 priority rules). (Section 5.6.)
- [ ] **Table — Fusion Engine per-model confidence weights** and **four-case decision logic table**. (Section 5.5.)
- [ ] **Table — Five ADM model specifications**: algorithm, dataset, hyperparameters, routing key. (Section 5.8.)
- [ ] **Table — Evaluation dataset composition** (1,950 events by category/severity/source dataset). (Section 5.9.)

### 11.3 Core Evaluation Results (Results section — the heart of the paper)
- [ ] **Table/Chart — Primary evaluation: agentic system vs. threshold-only baseline** across MTTA, MTTR, FER, FAR, RTA, SVR — the core "does agentic self-healing beat static rules" comparison.
- [ ] **Table/Chart — Single-agent baseline vs. full 4-agent pipeline** (supports Contribution C2 directly) — same metric set, isolates whether agent decomposition itself adds value.
- [ ] **Table/Chart — Fusion Engine on vs. off** (200 CPU-spike controlled test): false positive rate, compound detection rate, MTTA delta with/without the 3s window. Directly answers OQ8.
- [ ] **Chart — MTTA/MTTR distribution** (histogram or box plot) across the full 1,950-event run, split AUTO path vs. HITL path.
- [ ] **Chart — Learning Agent improvement over time**: Triage recall/accuracy, first 20% vs. last 20% of the 1,950-event run (tests whether ChromaDB accumulation actually helps).
- [ ] **Chart — RAG improvement test (H1)**: risk-tier accuracy with vs. without RAG context injection, targeting ≥80%.
- [ ] **Table — HITL latency distribution**: median/percentile time from `hitl.queue` arrival to operator decision (target <120s).
- [ ] **Chart — Throughput benchmark**: messages/sec at 1/5/10 events/sec, with and without Fusion Engine window (overhead visualization).
- [ ] **Table — Cohen's Kappa results** (Phase 2 target κ≥0.6) for Strategy Agent risk-tier vs. ground truth, and inter-rater agreement where applicable.

### 11.4 Hardware / Commodity Feasibility Evidence (supports Contribution C4)
- [ ] **Chart — Node 2 RAM usage over time** during a full evaluation run (idle → concurrent qwen3:1.7b + qwen3:0.6b + all 4 agents), annotated against the 8GB ceiling. Directly answers OQ2.
- [ ] **Table — Cross-node latency benchmark**: WiFi (Phase 0, informal) vs. Gigabit Ethernet (post 15 July, citable) — before/after cutover comparison.
- [ ] **Table/Chart — RabbitMQ throughput and queue depth** under load, both exchanges (`detection.fanout`, pipeline).
- [ ] **Chart — NTP drift stability** across the 3 nodes over the full evaluation window.
- [ ] **Grafana dashboard screenshots** — Dashboard 1 (cluster) and Dashboard 2 (agent+fusion pipeline) as supplementary/appendix figures, showing the live monitoring stack itself as evidence of observability (ties to the HITL/observability contribution).

### 11.5 Optional / Conditional (Contribution C5)
- [ ] **Table — qwen3:1.7b vs. GPT-4o-mini** on the same 30 curated AIOps prompts, same Cohen's Kappa rubric — only if API access obtained; otherwise state as Future Work in the paper.

### 11.6 Qualitative / Supporting Evidence
- [ ] **Selected reasoning examples table**: prompt → notable reasoning quality (e.g., THR_03 conditional restart, AUTH_05 scope-aware isolation, ERR_02 external-failure recognition). (Phase0_Evaluation_Summary §7.2 — already has strong candidates.)
- [ ] **Confidence score distribution summary**: range, most common value, low/high extremes, count of out-of-bounds responses. (§7.3.)

---

*End of consolidated reference. This single file captures: Literature Review → Phase 0 Infrastructure → Phase 0 LLM Evaluation (model switch resolved) → System Design v1.2 (current architecture, agent contracts, Fusion Engine, evaluation methodology including both baseline comparisons) → Layer diagram cross-reference → open questions → known issues → current build status → monitoring plan (Prometheus/Grafana) → full paper deliverables checklist (tables/graphs/comparisons). Update this file as Layer 1/2/3 implementation progresses and as evaluation results come in.*
