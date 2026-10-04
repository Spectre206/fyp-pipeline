# Writing Source Map — Thesis and Research Paper

**Project:** Distributed Multi-Agent Coordination for Self-Healing Data Pipelines: A Human-in-the-Loop Approach on Commodity Hardware

**Repository basis:** current `develop`, inspected at `22310014c2c1fbc6311aa30bd4d9c2e6f2f89a31` on 2026-10-04. This is a writing/navigation guide, not thesis prose, a new experiment, or a replacement for frozen evidence. It records the authority and limits of each source. For a later paper, retain the same denominators, run identities and limitations while compressing the chapter plan into Introduction, Related Work, Method, Experimental Setup, Results and Discussion.

## 1. How to use this map

Write implementation claims from executable code and effective configuration; write experimental claims from the execution revision, frozen contract and completed result record. Current integration HEAD identifies this map's inspection basis, **not** any experiment's execution revision. Use [R02] for the final comparison, [R03]/[R04] for baseline closeout and [R01]'s Ethernet and later routing sections for Proposed. Do not silently upgrade historical plans into implemented or measured achievements.

Source IDs below link directly to repository paths and are classified in the final source index. The compact category codes in chapter tables have these exact meanings:

| Code | Source classification | Appropriate use |
|---|---|---|
| I | IMPLEMENTATION SOURCE | Executable behavior/configuration; inspect named function rather than trusting comments alone |
| M | METHODOLOGY SOURCE | Study design, metric contract and design rationale; check amendment/scope |
| E | EXPERIMENTAL EVIDENCE | Preserved measured artifact or screenshot, with its provenance and inspection limits |
| R | RESULT SOURCE | Curated finalized numerical result/closeout or comparison |
| D | DISCUSSION SUPPORT | Literature leads and bounded reasoning, not independent proof of results |
| H | HISTORICAL CONTEXT | Superseded plans, old conditions or historical observations, explicitly scoped |
| A | APPENDIX / REPRODUCIBILITY SOURCE | Runbook, environment, monitoring or verification details |

Every mapped ID has one primary classification. A mixed document may contain historical passages even when its primary category is M or R. The index specifies those limits. Directory entries are bounded collections, not an endorsement of every contained file. Local evidence links exist in this checkout but may not be tracked or present in a clean clone; preserve the node-local inventory for publication reproducibility. No services, experiments, evaluators or tests were run for this map, and no database was opened or modified.

### Verified writing invariants

- Exactly **three completed formal Ethernet controller conditions**: **Proposed Adaptive**, **Threshold-only**, **Single-Agent**. One completed formal Mode B run per condition. Wi-Fi is a separate historical Proposed transport reference, not a fourth controller condition [R02], [H02].
- Proposed is heterogeneous: deterministic Triage normalizes/maps protocols and retrieves context [I18], [I19]; Strategy alone uses local `qwen3:1.7b` through Ollama [I20], [I21], [I22], [I23]; deterministic Policy authorizes AUTO or HITL [I24]; deterministic Learning summarizes outcomes, updates memory and bounded EMA [I25], [I26]. “Multi-agent” does not mean four LLMs.
- Layer 1 is the **Real-Time Statistical Data Plane**, using active statistical/rule-based detectors [I09], [I10], [I11], [I12], [I13], [I14], [I15]. Historical ML experiments [H05] are not runtime components. The schema value-shift detector checks a synthetic marker; do not call it a general drift estimator.
- Layer 3 supplies persistent human decisions, simulated automatic execution, feedback and observability [I27], [I28], [I29], [I30], [A08], [A09]. Use **policy-bounded autonomous self-healing** with the explicit simulation limitation; do not imply unrestricted LLM execution or verified production repair.
- The frozen input has 1,950 events; the observed controller population is 639, including 630 anomalies and nine NORMAL cases. Source events, detector evaluations, fused incidents and decisions are different units [R01], [R02], [R03], [R04].

### Contradictions, ambiguities and source precedence

| Issue found during inspection | Writing resolution; sources retained unchanged |
|---|---|
| [M01] names the Wi-Fi execution revision/experiment as authoritative and still describes Ethernet as future work | Use its design/rationale sections after code checking; its numerical results are historical Wi-Fi. [R02] controls final Ethernet scope and identities. |
| [M04] still names a fourth fixed-threshold/EMA condition and upcoming comparisons | Treat those scope sentences as superseded planning. Retain its v2 label translation, retrospective disclosure and corrected FER; exactly three conditions in [R02], [M03]. No fourth result or pending fourth experiment. |
| [M02] retains prospective language, Mode A and optional ablations; [D01] retains planned comparisons/network work | Final scope amendment and [R02] control completed work. These sources do not prove Mode A, repeated trials or an adaptation ablation happened. |
| [H02] preserves the original blank-label FAR/FER analysis | Final Proposed v2 results [E01], [R01], [R02] supersede Ethernet metric unavailability only; do not rewrite historical Wi-Fi numbers. |
| [H01] proposes Learning LLMs, historical models/targets and broad novelty | Do not cite these as implemented facts. [I18], [I20], [I24], [I25] establish current responsibilities. Prior-art/novelty claims require external literature. |
| [I10]'s header mentions a Z-score threshold of 3; executable setting/configuration is 2.0 | Cite `detect`, `Z_SCORE_THRESHOLD` and [I14], not the header. No implementation change is implied. |
| PSI language persists in [I04], [I06], while [I13] checks `distribution_shift_marker` | Separate stored/computed features from the active detector. State synthetic-marker limitation and do not describe a runtime PSI/ML detector without executable evidence. |
| Generic calibrator defaults differ from the active call site | [I08] passes 20; [I05] updates before gating, so first 19 accepted events per cold component are withheld and the 20th can pass. [A10] tests the same boundary with n=3. |
| “End-to-end” can be read as source-to-recovery time | [I24] records Triage-timestamp-to-Policy time; [I38] aggregates that field. Baseline callback `processing_seconds` is another boundary [M03], [I33]. Before any cross-condition latency claim, inspect frozen execution code/records for exact timestamps. No matched latency winner or MTTR follows. |
| Proposed provenance is layered: early README Node 1/2 values were summary-attributed; later routing artifacts are now local | This map directly checked saved Proposed routing summary [E01] and Threshold Fusion snapshot [E02]. Other results are retained from formal closeout records; no claim of newly auditing all remote native artifacts. |
| Native analyzers handle invalid existing routes differently | [I38] separates absent Policy IDs from invalid existing records; [I37] reports all unscoreable expected-AUTO IDs plus integrity issues. Final runs have clean applicable records and matching 240/380 coverage, but do not equate malformed records with physical upstream loss in a future partial run. |

These are writing cautions, not authorization to edit source/evidence. If a thesis claim depends on unresolved historical implementation detail or installed runtime state, obtain the archived execution revision/artifact rather than inferring it from today's checkout.

## 2. Chapter 1 — Introduction

This chapter should establish the incident-handling coordination problem, why constrained local inference and human authority matter, and what this project actually investigates. It answers “What problem is addressed, within what scope, and what will the thesis demonstrate?” It should lead to the literature gap in Chapter 2 and testable design/evaluation choices in Chapters 3–5 without presenting outcomes as proof of novelty.

| Must-have section/subsection | Best sources and classification | Extract and writing caution |
|---|---|---|
| 1.1 Background and context | [D01] D; [M01] M | Pipeline reliability, detection versus repair, asynchronous control and governance; broad prevalence/industry claims need academic citations. |
| 1.2 Problem statement | [M01] M; [I24], [I27] I | Need to connect incidents, proposals, authorization, human review and outcomes without unrestricted model execution. Explain prototype boundaries. |
| 1.3 Motivation: commodity hardware and local AI | [R01] R; [I20], [I23] I; [D01] D | Three 8-GB Ubuntu nodes and CPU-local proposal generation; privacy, cost and energy advantages are not measured comparative findings. |
| 1.4 Research gap | [D01] D; [M02] M | Scoped gap in evaluating this policy-bounded architecture on modest distributed hardware; avoid “first ever” or “no prior system exists.” |
| 1.5 Research aim | [M02] M; [R02] R | Implement and evaluate a heterogeneous controller against deterministic and single-model alternatives under a common routing contract. |
| 1.6 Research objectives | [I05], [I15], [I20], [I24], [I25], [I29] I; [M03] M | Build detection/control/oversight integration; preserve bounded authority; perform reproducible three-condition Mode B comparison. Do not promise verified autonomous repair. |
| 1.7 Research questions | [M02] M; [R02] R | RQ1: How are responsibilities and authority separated? RQ2: What routing-quality and HITL-workload differences were observed? RQ3: What deployment/measurement limits constrain interpretation? These are proposed thesis formulations, not a claim of preregistration. |
| 1.8 Scope and exclusions | [R02] R; [M03] M; [H02] H | Synthetic corpus, three nodes, three controllers, one formal Ethernet run each; historical transport pair separate; simulated execution and limited generalization. |
| 1.9 Contributions | [R02] R; [I17], [I24], [I37] I | Implemented integration, deterministic authorization boundary, frozen comparative metric/evidence contract and observed results. State demonstrable artifacts, not unverified novelty or universal superiority. |
| 1.10 Thesis organization | This map | Seven chapters; References and Appendices are separate, not Chapters 8/9. Explain design → setup → observations → interpretation. |

## 3. Chapter 2 — Literature Review / Related Work

This chapter should build the academic argument for the design choices and identify what prior work does and does not establish. It answers “Why are this separation of responsibilities and this evaluation necessary?” Use the existing targeted review as a starting point, then check primary papers and develop a critical synthesis that motivates Chapter 3 rather than retroactively claiming literature proves the experimental result.

| Must-have section/subsection | Best sources and classification | Extract, external work required and caution |
|---|---|---|
| 2.1 Review scope and method | [D01] D | Existing targeted search description and inclusion criteria; update actual search dates/process when research is performed. Do not invent systematic-review screening counts. |
| 2.2 Self-healing/autonomic data pipelines | [D01] D; [I27] I | Existing autonomic/AIOps leads; distinguish monitoring, diagnosis, proposal, execution and verified recovery. Repository implements only a bounded prototype. |
| 2.3 Statistical/rule-based anomaly detection | [D01] D; [I09], [I10], [I11], [I12], [I13], [I14], [I15] I | Justify transparent low-cost detection and structural/value distinction. Treat detector code as design context, not literature evidence. |
| 2.4 Local language models for remediation proposals | [D01] D; [I20], [I21], [I22], [I23] I | Structured generation, local resource constraints and action vocabulary; independently verify publications behind model/cost/performance claims. |
| 2.5 Multi-agent coordination and asynchronous messaging | [D01] D; [I17], [I18], [I24] I | Heterogeneous role decomposition and queue decoupling; no automatic superiority from more agents. |
| 2.6 Deterministic policy and safety control | [D01] D; [I21], [I24] I | External enforcement as motivation; this implementation is not a formally verified runtime shield. |
| 2.7 Human-in-the-Loop automation | [D01] D; [I28], [I29], [I30] I | Levels of automation, persistence, reviewer workload and accountability; approval is not independent ground truth. |
| 2.8 Feedback, retrieval and adaptive thresholds | [D01] D; [I19], [I25], [I26] I | Memory/context reuse and EMA; distinguish adaptation from model training and measured benefit. |
| 2.9 Observability and distributed reliability | [D01] D; [I17], [I36] I; [A08] A | Queues, acknowledgment, measurement boundaries and evidence; observability is not proof of fault tolerance. |
| 2.10 Commodity-hardware/local-AI constraints | [D01] D; [R01] R; [I35] I | Existing CPU-inference literature leads, memory and latency constraints; fitting a model does not establish sustained throughput. |
| 2.11 Comparative synthesis and research gap | [D01] D; [M02], [M03] M | Compare scope, authority boundaries and evaluation rigor; derive justified requirements and open questions, not a tool-shopping list. |

### Proposed literature comparison matrix

Use the following schema; do not populate new study rows from memory or repository implementation facts. [D01] contains candidate studies and a bibliography, but every final row should be traceable to the original publication. No bibliography was newly verified for this map.

| Column | Record |
|---|---|
| Study; Year | Verified author/title/venue or persistent identifier; publication year |
| Domain | Streaming, data engineering, AIOps or other workload |
| Detection approach | Structural, statistical, rules, learned models or not reported |
| Remediation approach | Recommendation, scripted action, verified repair or conceptual design |
| LLM / SLM use | Model role and local/cloud assumptions; explicit not-reported state |
| Multi-agent coordination | Roles and communication; distinguish multiple processes from demonstrated coordination benefit |
| Deterministic policy control | Authority boundary, checks and any actual formal guarantee |
| HITL | Review decision, modification, feedback and measured human work |
| Feedback / adaptation | Memory, threshold update, training or none; evidence of benefit |
| Self-healing capability | Proposed versus implemented versus experimentally verified recovery |
| Deployment assumptions | Hardware, network, resource dependencies and scale |
| Evaluation approach | Datasets, ground truth, baselines, runs, uncertainty and metric boundaries |
| Main limitation | Limitation established by the paper or clearly marked reviewer inference |
| Relevance to our work | Specific requirement supported and unresolved question |

The synthesis must justify: separating rapid detection from slow inference; structural bypass and correlation; Strategy/Policy authority separation; persistent human oversight; feedback memory and bounded adaptation; CPU-local deployment; and comparisons against simpler controllers. Literature need not uniquely mandate RabbitMQ, Chroma, Django or this exact three-node arrangement. Existing optional adaptation-ablation discussion is rationale for future research, not a fourth completed condition.

## 4. Chapter 3 — Methodology and System Design

This chapter should make the implemented system reproducible at the level of responsibilities, algorithms, state and interfaces. It answers “How does a source event become a bounded decision and an outcome?” Distinguish design methodology from experimental controls (Chapter 4), and use code for behavior while using diagrams and rationale to connect the components.

| Must-have section/subsection | Best sources and classification | Extract and writing caution |
|---|---|---|
| 3.1 Research/design methodology | [M01], [M02] M; [D01] D | Design–implementation–evaluation sequence; label retrospective narration and do not invent an adopted formal research methodology. |
| 3.2 Requirements and design goals | [D01] D; [M01] M | R1–R6 traceability to observation, bounded planning, oversight, decoupling, adaptation and evaluation; distinguish goals from proven outcomes. |
| 3.3 Overall logical architecture | [R01] R; [I17], [I24], [I29] I | Three layers, asynchronous handoffs, authority and outcome loop; label local calls versus RabbitMQ edges. |
| 3.3.1 Physical deployment | [R01] R; [A05], [A06], [A07] A | Node 1 stream/RabbitMQ; Node 2 control/Ollama/Chroma; Node 3 execution/HITL/monitoring. Hardware measurements belong in Chapter 4. |
| 3.3.2 Event/message lifecycle | [I01], [I02], [I03], [I04], [I08], [I17] I | Source IDs, structural bypass, fan-out, Fusion incidents and common anomaly.detected boundary. Labels are offline, not runtime routing inputs. |
| 3.4 Layer 1 — Real-Time Statistical Data Plane | [I03], [I05], [I08] I | Validation, feature enrichment and detection independence from LLM inference. “Real-Time” is a role name, not a proven hard deadline. |
| 3.4.1 Event validation and structural bypass | [I03], [I04] I | Pydantic structural failure routes directly to anomaly.detected through anomaly.schema_drift, bypassing calibration/Fusion. |
| 3.4.2 Calibration and rolling features | [I05], [I06], [I07], [I08] I; [A10] A | Per-component baseline versus per-node/component rolling window; n=20 update-before-gate behavior. First 19 accepted events withheld; 20th eligible. |
| 3.4.3 Five detector rules | [I09], [I10], [I11], [I12], [I13], [I14] I | CPU/memory, error, throughput, authentication, synthetic schema marker; extract actual expressions/settings. Do not turn detector event counts into TP/FP. |
| 3.4.4 Detection fusion | [I15], [I16] I | Correlation by event ID, 3.0 s primary and 0.75 s recovery, confidence/weights, suppression and compound incidents. Fast Path is not early finalization. |
| 3.5 Layer 2 — Multi-Agent AI Control Plane | [I18], [I19], [I20], [I21], [I22], [I23], [I24], [I25], [I26] I | Heterogeneous deterministic/generative responsibilities; only Strategy uses an LLM in Proposed. |
| 3.5.1 Triage and retrieval | [I18], [I19] I | Normalize incidents, rule-map protocols, retrieve positive outcome context; cold retrieval may be empty. Do not describe diagnosis as an LLM step. |
| 3.5.2 Strategy proposals and structured output | [I20], [I21], [I22], [I23] I | Seven-field schema, three distinct allowed actions, severity/risk binding, bounded retry and local model request. Validity is a contract property. |
| 3.5.3 Deterministic Policy authorization | [I24] I; [I21] I | Timeout/parse/schema/action/risk/confidence checks; HIGH risk or low confidence → HITL; LOW valid confidence meeting threshold → AUTO. Policy consumes Strategy validation status. |
| 3.5.4 Learning, memory and EMA | [I25], [I26], [I19] I | Deterministic summaries, Chroma persistence and t′ = clip(αt + (1−α)s, 0.60, 0.90), α=0.9, cold t=0.65. Outcome signals are engineered values; no trained weights or demonstrated optimality. |
| 3.6 Layer 3 — Execution, Human Oversight & Observability Layer | [I27], [I28], [I29], [I30] I; [A08], [A09] A | Human authority, simulated execution, persistent state and monitoring; use the full official layer name consistently. |
| 3.6.1 Auto Executor | [I27] I | Nonempty action list produces simulated success after 0.5 s; empty list fails. No real service restoration experiment. |
| 3.6.2 HITL workflow and authoritative state | [I28], [I29], [I30] I | Arrival, PENDING, approve/reject/modify, decided_at and duplicate-safe incident persistence. Empty hitl.queue is not zero pending humans. |
| 3.6.3 Outcome feedback | [I25], [I29] I; [I36] I | Human/AUTO outcomes and downstream learning or baseline accounting; persisted decisions and feedback delivery require separate reconciliation. |
| 3.6.4 Prometheus/Grafana | [A08], [A09] A; [R01] R | Agent/detector/queue/hardware observations and names; measurement windows, scrape rates and histogram limits. |
| 3.7 RabbitMQ architecture | [I17] I | detection.fanout, fyp.events topic, fyp.dlx direct, fyp vhost, consumer ownership and dead.letters; draw topology without secrets. |
| 3.8 Safety boundaries and failure handling | [I21], [I24], [I29], [I30], [I36] I; [M03] M | Fail-to-HITL conditions, durable state, acknowledgment and record checks. No formal safety or exactly-once/end-to-end availability guarantee. |
| 3.9 Baseline designs | [I31], [I32], [I33], [I34], [I35] I; [R04], [R05] R | Threshold fixed rules versus Single-Agent accepted model route with generic validation; same Layer 1/3 interface, no invented Proposed agent stages. |
| 3.10 Constraints and design rationale | [D01] D; [M01], [M02] M; [R02] R | CPU generation, serial queues, synthetic markers, engineered feedback and autonomy limits. Architecture is implemented; isolated component benefit is unmeasured. |

### Diagram reuse plan

Prefer source-editable Mermaid in [R01] (full architecture) and [M01] (physical deployment, logical layers, message flow and Policy decision flow); [M02] supplies Mode A/B and controller-comparison flows, and [D01] supplies literature-to-requirements/architecture derivation. Redraw with Ethernet IPs and final three-condition scope. Check every queue edge against [I17], every authority edge against [I24], and label simulated execution. Do not reuse historical diagram artwork merely because it looks finished. A screenshot of a dashboard is an observation, not an architecture diagram.

## 5. Chapter 4 — Experimental Setup

This chapter should specify the conditions under which the reported observations were produced. It answers “What was held fixed, what differed, what was measured, and which runs count?” Keep implementation algorithms in Chapter 3; here record actual execution identities, workload, independent labels, cold state, monitoring, lifecycle and fairness limits before presenting results.

| Must-have section/subsection | Best sources and classification | Extract and writing caution |
|---|---|---|
| 4.1 Evaluation design and unit of analysis | [M02], [M03] M; [R02] R | Completed Mode B source-to-controller full pipeline; Mode A identical-incident study remains distinct. One formal run/condition. |
| 4.2 Hardware environment | [R01] R; [M01] M; [A05] A | Three commodity 8-GB machines; AMD Ryzen 5 on Nodes 1/2, Intel Core i5 on Node 3; Ubuntu 24.04 Desktop/Server roles. Exact CPU SKU/storage and run-time resource claims require inventories, not historical master-reference detail alone. |
| 4.3 Software environment | [I20], [I23], [I35] I; [R04] R; [A01], [A02], [A03] A | Python/dependency snapshots, Ollama/model identity and execution hashes. SA records Ollama 0.18.0/model digest; do not assign that version/digest to all conditions without their evidence. |
| 4.4 Network topology and Ethernet environment | [A05], [A06], [A07], [A08] A; [M03] M | 10.10.10.11/.12/.13, switch/cables, no Ethernet default gateway, Wi-Fi retained for Internet, broker sockets and effective scrape configuration. Hostname/aggregate graph alone does not prove transport. |
| 4.5 Frozen workload and composition | [I01], [I02] I; [R01], [R03] R; [M03] M | 1,000 NORMAL; 200 each CPU/memory, error, throughput, auth; 150 schema; same source/config/IDs/order/hashes and speed 1. Fresh UUID/timestamp generation is not a matched corpus. |
| 4.6 Cold state and startup | [A01], [A02], [A03] A; [I05], [I08], [I25] I | Applicable empty queues/Feature Store/gateway state, fresh journals; Proposed Chroma empty and EMA 0.65/0 updates. Baselines do not acquire Chroma/EMA merely for symmetry. |
| 4.7.1 Proposed Adaptive condition | [R01], [R02] R; [I18], [I19], [I20], [I21], [I22], [I23], [I24], [I25], [I26] I | Native four-stage control plane and adaptive state, exact run/revision below. |
| 4.7.2 Threshold-only condition | [R03] R; [I31], [I32] I; [A02] A | Fixed deterministic rules, no model-attempt sidecar, no confidence/learning additions. |
| 4.7.3 Single-Agent condition | [R04] R; [I33], [I34], [I35] I; [A03] A | Monolithic model route, schema retry/fallback, real attempt evidence, preload and fixed non-measured inference. |
| 4.8 Shared contract and fairness | [M03] M; [R02] R | Common inputs/labels/Layer 1/Layer 3 and explicit architecture differences; different warmup and stochastic/human/adaptive states prevent matched latency/isolated causal claims. |
| 4.9 Ground truth/routing-label policy | [M04] M; [I02], [I39] I; [A12] A | Original risk/action → v2 eligibility; NORMAL excluded; preserve source IDs/order; retrospective for Proposed, frozen before baselines. |
| 4.10 Metrics and equations | [M03] M; [I37], [I38] I | Use equations below, numerator/denominator, undefined cases and invalid-record handling; do not use legacy common analyzer [H06]. |
| 4.11 Evidence capture and observability | [A01], [A02], [A03], [A08], [A09] A; [E01], [E02], [E03], [E04], [E05] E | Native agent/journal evidence, offline summaries, protocol/process/queue/transport state, inventories and screenshot windows. Condition-specific exports are legitimate. |
| 4.12 Reproducibility controls | [I40] I; [M03] M | Actual execution and deployment/evaluator revisions, manifest hashes, model/dependencies, clocks, reviewed inputs; manifest checks do not establish completeness or human approval. |
| 4.13 Valid/invalid run criteria | [M03] M; [A02], [A03] A; [H04] H | Worker death after replay → failed/incomplete; same-ID worker restart → RESUMED_INVALID_FOR_FORMAL_COMPARISON. Preserve evidence, use new ID/cold state; controller integrity alone cannot certify continuity. |
| 4.14 Threats to experimental validity | [R02], [R03], [R04] R; [M03], [M04] M; [H02] H | Single run, fixed order, model/warmup/reviewer differences, synthetic labels, retrospective translation and limited hardware. Chapter 6 evaluates consequences. |

### Frozen metric definitions for writing equations

Let U be all corpus IDs; E ⊆ U the 380 independently expected-AUTO anomalies; V the IDs with valid AUTO/HITL decisions; A and H the actual AUTO/HITL subsets of V; L the nonblank authoritative eligibility-label IDs; and F the IDs labeled `safe_to_auto=false`. NORMAL is excluded from routing labels. Report ratios and their populations explicitly:

| Metric | Definition | Boundary/caution |
|---|---|---|
| FAR | \|A ∩ F\| / \|A ∩ L\| | Error among labeled actual AUTO decisions, not among all unsafe incidents; benchmark eligibility, not a safety certificate |
| Routing FER | \|H ∩ E\| / \|V ∩ E\| | Routing-stage decision error, conditional on reaching a scoreable route |
| Expected-AUTO controller coverage | \|V ∩ E\| / \|E\| | Eligible corpus reaching a scoreable controller decision; not actual automation share |
| Missing before routing | \|E − V\| / \|E\| | Unscoreable eligible corpus; final clean runs' 140 cases are upstream attrition, not extra false escalations |
| Risk accuracy | Correct reported risk / scoreable independently risk-labeled anomalies | Report actual denominators; not Strategy confidence calibration or action correctness |
| Feedback completion | Accepted matching required outcomes / observed decisions requiring feedback | Final exhaustive review gives 639/639; partial-run perfect feedback is not full experiment completion |
| Human workload | Actual HITL count, outcome distribution and pending count | Route volume is not measured cognitive effort or reviewer correctness |

Zero denominator means `not_computable`/null, never zero error. Proposed analysis reports invalid existing Policy records separately from absent ones [I38]; the baseline scorer excludes invalid/conflicting decisions from V and records integrity issues [I37]. Describe those distinctions when discussing anything other than the clean final runs. Threshold has no LLM invocation/retry stage and no `attempt.jsonl`; Single-Agent preserves real attempts; Proposed has native agent/stage evidence. Never fabricate empty sidecars to homogenize evidence.

### Minimum evidence packet for a thesis claim

For each condition, retain the source/config/original-label/derived-label hashes, run/revision identity, controller/stage records, evaluator and verification outputs, Layer 1 reconciliation, Layer 3 outcomes, process/lifecycle evidence, clock/transport checks and per-node inventories. [R03], [R04] report that formal closeout verified native evidence; gateway absence of those native files is not proof of missing evidence. For an independently reproducible paper supplement, obtain approved copies with their inventories and redact secrets rather than claiming this map has newly reverified all of them.

## 6. Chapter 5 — Evaluation, Results and Analysis

This chapter should report observed outcomes with correct populations and provenance, then offer restrained analysis. It answers “What happened in the completed runs?” Start with source-to-incident reconciliation, present shared routing metrics, human outcomes and integrity, then condition-specific observations. Keep explanations that exceed direct measurement for Chapter 6.

| Must-have section/subsection | Best sources and classification | Extract and caution |
|---|---|---|
| 5.1 Runs and evidence completeness | [R02], [R03], [R04] R; [E01], [E03], [E04] E | Exact identities and closeout scope; excluded run [H04] is history, not a replicate. |
| 5.2 Layer 1 accounting | [R01], [R03], [R04] R; [E02] E | Input, valid, bypass, calibration, detector/Fusion and controller counts; overlapping Fusion attributes are not extra incidents. |
| 5.3 Routing distributions and cross-tabs | [R02], [R03], [R04] R; [E01] E | AUTO/HITL including NORMAL versus anomaly-only expected/actual cross-tabs. |
| 5.4 FAR, FER and eligible coverage | [R02] R; [I37], [I38] I; [E01] E | Exact fractions; keep 140 missing separate from 240 scoreable eligible decisions. |
| 5.5 Risk and structured validity | [R01], [R04] R; [R02] R | 513/630, 449/630, 443/630 risk accuracy; Proposed schema-valid 639/639 and SA 639 initial valid responses; no model SVR for Threshold. |
| 5.6 Human workload and feedback | [R01], [R03], [R04] R | HITL 464/471/638; outcomes/pending and feedback; reviewer behavior is not an independent correctness test. |
| 5.7 Integrity and lifecycle | [M03] M; [R03], [R04] R; [I37] I | Record integrity, reconciliation and uninterrupted baseline closeout are complementary evidence, not interchangeable. |
| 5.8 Condition-specific timing/resources | [R01], [R04] R; [M03] M; [E05] E | Proposed offline latency/resource context and SA warmup caveat; omit an unsupported three-way latency ranking. |
| 5.9 Historical Wi-Fi/Ethernet observations | [H02] H; [R01] R | Optional clearly separate subsection: one Proposed transport pair, fixed order, different outputs/reviewer outcomes; no network causality. |
| 5.10 Findings summary | [R02] R | Observed lower Proposed FAR/FER than Threshold, conservative SA, common coverage and distinct human workload; no universal winner. |

### Results master table — identities and populations

Column sources apply to every cell unless a row gives a more specific source. P = [R01], [R02] and saved final summary [E01]; T = [R02], [R03]; S = [R02], [R04]. Fractions are authoritative; displayed percentages are rounded. Do not substitute the integrated `develop` revision for the execution revisions.

| Metric | Proposed Adaptive | Threshold-only | Single-Agent | Authority |
|---|---|---|---|---|
| Formal Run ID | ethernet_cold_20261002_023108 | threshold-ethernet-full-20261003-084252 | single-agent-ethernet-full-20261004-035637 | [R02], respective closeout records |
| Execution revision | c595459ce64a479a2bf725df2fbffb7142d6f66b | c1cdbd70e66e8a70b68d22c2eec539e70515cfdb | c09160c506686234d65041cbb83ea63a0ecd575c | [R01], [R02], [R03], [R04] |
| Completed formal runs in comparison | 1 | 1 | 1 | [R02] |
| Controller decisions | 639 | 639 | 639 | P / T / S |
| Anomaly / NORMAL decisions | 630 / 9 | 630 / 9 | 630 / 9 | P / T / S |
| Actual AUTO | 175 | 168 | 1 | P / T / S |
| Actual HITL | 464 | 471 | 638 | P / T / S |
| Excluded NORMAL AUTO / HITL | 1 / 8 | 9 / 0 | 0 / 9 | P / T / S |
| Expected AUTO → AUTO | 136 | 109 | 1 | [R02], [E01] and baseline cross-tabs |
| Expected AUTO → HITL | 104 | 131 | 239 | [R02], [E01] and baseline cross-tabs |
| Expected HITL → AUTO | 38 | 50 | 0 | [R02], [E01] and baseline cross-tabs |
| Expected HITL → HITL | 352 | 340 | 390 | [R02], [R03], [R04] |

### Results master table — scores and human outcomes

| Metric | Proposed Adaptive | Threshold-only | Single-Agent | Authority |
|---|---:|---:|---:|---|
| FAR numerator | 38 | 50 | 0 | [R02], [R03], [R04], [E01] |
| FAR denominator | 174 | 159 | 1 | [R02], [R03], [R04], [E01] |
| FAR % | 21.8390804598% | 31.4465408805% | 0% | [R02] |
| Routing FER numerator | 104 | 131 | 239 | [R02], [R03], [R04], [E01] |
| Routing FER denominator | 240 | 240 | 240 | [R02], [R03], [R04], [E01] |
| Routing FER % | 43.3333333333% | 54.5833333333% | 99.5833333333% | [R02] |
| Expected-AUTO controller coverage | 240/380 = 63.1578947368% | 240/380 = 63.1578947368% | 240/380 = 63.1578947368% | [R02] |
| Missing before routing | 140/380 = 36.8421052632% | 140/380 = 36.8421052632% | 140/380 = 36.8421052632% | [R02] |
| Risk accuracy | 513/630 = 81.4285714286% | 449/630 = 71.2698412698% | 443/630 = 70.3174603175% | [R02], [E01] |
| Feedback completion | 639/639 = 100% | 639/639 = 100% | 639/639 = 100% | [R01], [R02], [R03], [R04] |
| HITL approved | 463 | 469 | 636 | [R01], [R03], [R04] respectively |
| HITL rejected | 0 | 1 | 1 | [R01], [R03], [R04] |
| HITL modified | 1 | 1 | 1 | [R01], [R03], [R04] |
| HITL pending at completion | 0 | 0 | 0 | [R01], [R03], [R04] |
| Structured model evidence | 639/639 Strategy schema-valid responses | Not applicable: no model stage | 639 initial structured-valid outputs; no validation retry required | [R01], [R03], [R04] |

FAR denominators differ because NORMAL is excluded: Proposed 175−1=174; Threshold 168−9=159; SA 1−0=1. FER is 104/240, 131/240 and 239/240, **not** a fraction of all 380 expected-AUTO corpus IDs. Coverage measures controller reach, not the proportion actually automated. Neither 639 feedback nor no record errors proves every source event should have produced a decision.

### Layer 1 accounting table

| Accounting item | Proposed Adaptive | Threshold-only | Single-Agent | Authoritative source and scope |
|---|---:|---:|---:|---|
| Corpus/input events | 1,950 | 1,950 | 1,950 | [R01], [R03], [R04] |
| Validator valid | 1,850 | 1,850 | 1,850 | [R01], [R03], [R04] |
| Structural schema bypass | 100 | 100 | 100 | [R01], [R03], [R04] |
| Cold calibration withheld | 323 | 323 | 323 | [R03] states count; P/S arithmetic 1,850−1,527, consistent with [I05], [I08] |
| Detector/Fusion eligible, per detector | 1,527 | 1,527 | 1,527 | [R01], [R03], [R04] |
| Fusion published | 539 | 539 | 539 | [R01], [R03], [R04] |
| Fusion suppressed | 988 | 988 | 988 | [R01], [E02], [R04] |
| Compound incidents | 43 | 43 | 43 | [R01], [E02], [R04] |
| Fast Path count | 83 | 83 | 83 | [R01], [E02], [R04] |
| Total controller incidents | 639 | 639 | 639 | 539 Fusion + 100 bypass, [R01], [R02], [R03], [R04] |

Accounting: 1,850−323=1,527; 539+988=1,527; 539+100=639. Compound and Fast Path overlap the publication population; never add them to 539. The 323 calibration-withheld source events and the 140 missing expected-AUTO incidents are different populations, not interchangeable counts. Matching totals alone do not establish per-ID identity, false-positive rates or continuous system reliability.

### Result notes: observation before explanation

1. **Observed:** Proposed FAR and routing FER were lower than Threshold's in these completed runs. **Not established:** which architecture component caused the difference or whether it generalizes.
2. **Observed:** SA routed only one incident AUTO, yielding 0/1 FAR and 239/240 FER. **Interpretation:** conservative routing with a large review workload; zero FAR is not evidence it is safest/best.
3. **Observed:** all three share 240/380 eligible coverage and 140/380 missing-before-routing. **Boundary:** upstream reconciliation is required to explain IDs; controller rules cannot score absent incidents.
4. **Observed:** HITL workload is 464, 471 and 638 cases. **Boundary:** these are case counts, not reviewer effort/time measurements; reviewer choices differ.
5. **Observed:** final feedback completes for observed decisions. **Boundary:** this does not establish real repair, upstream continuity or absence of historical interruption.

### Figure and screenshot plan

Use [E05]'s seven Proposed Ethernet images for qualitative illustration with condition, run ID and time-window captions. Filename checks confirm this collection; visual claims should be checked against the actual image when selecting the final thesis figure. Do not extrapolate these Proposed screenshots to either baseline.

| Existing figure within [E05] | Useful illustration | Cannot prove |
|---|---|---|
| system_overview.png | Overall dashboard and stage/routing activity | Event-level completeness, independent correctness or causal comparison |
| layer1_data_plane.png | Detector/Fusion runtime observations | Precision/recall or trained ML detector quality |
| layer2_control_plane.png | Strategy, Policy, Learning and plotted timing | Complete-run tail latency; [R01] records visual E2E clipping near 30 minutes versus offline p95 ≈131.10 minutes |
| layer3_execution_hitl.png | AUTO/HITL state, decisions and feedback | Verified restoration or human decision correctness |
| infrastructure_health.png | Exporter/queue/DLQ health at observation time | Uninterrupted operation throughout the run |
| hardware_node_resources.png | CPU/memory/network observations | Hardware equality across every runtime or measured energy/cost advantage |
| queues_final_zero.png | Final ready/unacknowledged queue counts | No earlier backlog/loss or zero pending database-backed human work by itself |

Redraw the master routing table as a numerator-labelled FAR/FER plot and a separate AUTO/HITL workload plot only when preparing figures; do not merge their denominators. A source→calibration→Fusion→controller flow is supported by the accounting table. No new plots or measurements were generated here. Wi-Fi images [E06] belong only in the explicitly historical transport subsection.

## 7. Chapter 6 — Discussion

This chapter should connect observations to architectural trade-offs and research questions while distinguishing plausible explanations from established findings. It answers “What do the results mean, and how far can those conclusions travel?” Use the following themes to interpret Chapter 5 and motivate the bounded conclusions and future work in Chapter 7.

### Discussion themes table

| Observation | Evidence | Likely interpretation (hypothesis unless directly implemented) | Supported conclusion | What cannot be concluded | Thesis section |
|---|---|---|---|---|---|
| Proposed FAR/FER lower than Threshold | [R02], [R03] R | Context, schema/risk binding and authorization may influence routing | Lower observed errors under this benchmark contract | Policy/RAG/EMA independently caused improvement; statistical superiority | 6.1 Architectural comparison |
| SA 0/1 FAR but 239/240 FER | [R04] R | Valid model routes were overwhelmingly conservative | Zero FAR accompanied almost universal escalation | Safest controller, best utility or effective autonomous recovery | 6.2 Conservatism and FAR/FER trade-off |
| AUTO totals 175/168/1; coverage all 240/380 | [R02] R | Routing choice differs after a shared upstream filter | Automation volume and eligible controller coverage measure different things | Equal coverage means equal useful automation or equal per-ID detections | 6.3 Automation versus reach |
| HITL cases 464/471/638 | [R01], [R03], [R04] R | SA places more cases before a reviewer | Measured review-case burden differs | Measured labor savings, cognitive burden or superior human decisions | 6.4 Human oversight/workload |
| Strategy output passes deterministic checks | [I21], [I24] I | External checks bound proposal authority | LLM proposals do not directly execute unrestricted commands | Formal safety certificate, universally appropriate actions | 6.5 Policy authority |
| Four specialized Proposed roles, only one generative | [I18], [I20], [I24], [I25] I | Heterogeneous decomposition makes responsibilities explicit | Implemented separation of planning, authorization and feedback | More agents inherently improve quality or reliability | 6.6 Coordination and decomposition |
| EMA changes with 639 feedback updates | [R01] R; [I25] I | Engineered outcome signals affect later thresholds | Bounded deterministic adaptation occurred | Learning improved outcomes, converged optimally or rejection always tightens safety | 6.7 Adaptation and memory |
| Commodity three-node deployment completed runs | [R01], [R02], [R03], [R04] R | Local deployment is feasible for this workload | Demonstrated operation on these three 8-GB machines | Production throughput, low energy, cheaper-than-cloud claim or arbitrary scale | 6.8 Hardware feasibility |
| Proposed serial Strategy timing/queueing; unequal warmup | [R01], [R04] R; [M03] M | CPU generation constrains processing; initialization confounds timing | Explicit local-model and measurement limits | Baseline latency ranking, matched residency or universal network irrelevance | 6.9 Local SLM constraints |
| 323 calibration-withheld; 140 eligible absent | [R03] R; [I05], [I08] I; [R02] R | Cold-start/filtering affects corpus-to-controller reach | Must report upstream coverage separately from FER | All absence is lost delivery; all eligible inputs were considered by Policy | 6.10 Cold-start attrition |
| Labels from a synthetic fixed workload | [I01], [I02], [I39] I; [M04] M | Benchmark specifies intended eligibility | Reproducible benchmark routing evaluation | Universal operational safety or real production-data validity | 6.11 Construct validity |
| V2 translated retrospectively for Proposed | [M04] M; [R02] R | Source intent predates runs but explicit eligibility policy did not | Disclose timing and freeze before baseline scoring | Prospective blinding for Proposed | 6.12 Internal validity |
| One formal run per controller | [R02] R | Stochastic/reviewer/order variability remains unestimated | Descriptive evidence only | Significance, confidence intervals from independent replicates or universal best | 6.13 Generalizability |
| AUTO executes a simulation | [I27] I | Workflow exercise, not validated intervention | Routing/execution/feedback integration was demonstrated | MTTR, successful service restoration or production readiness | 6.14 Recovery scope |
| Clean controller exports can coexist with invalid run history | [H04] H; [I37] I; [M03] M | Controller evidence cannot see every upstream restart | Lifecycle/process evidence is needed in addition to offline integrity | Complete feedback rehabilitates a resumed experiment | 6.15 Experimental reliability |

### Threats to Validity

| Required subsection | Source map | What to discuss |
|---|---|---|
| 6.16.1 Internal validity | [R02], [R04] R; [M03], [M04] M; [H02] H | Fixed condition order, unequal warmup, stochastic generation, human decisions, adaptive state and retrospective translation; no isolated component ablations. |
| 6.16.2 Construct validity | [I13], [I27], [I37], [I38] I; [M04] M | Synthetic schema marker, benchmark eligibility rather than safety, schema validity versus quality, feedback versus recovery, non-equivalent timing boundaries. |
| 6.16.3 External validity | [R01], [R02], [R03], [R04] R; [D01] D | One synthetic corpus, three commodity machines and one local model family; no production/large-cluster/general fault-domain claim. |
| 6.16.4 Reproducibility/reliability limitations | [M03] M; [I40] I; [E01], [E02], [E03], [E04] E | Node-local artifacts, execution versus integration revisions, effective model defaults, installed state, clock evidence, partial/resumed runs and snapshot limits. |

## 8. Chapter 7 — Conclusion and Future Work

This chapter should answer the research questions using only established implementation and observations, state the project contributions within their limits, and identify the next evidence needed. It answers “What has this thesis established, and what remains open?” It should close the argument from Chapter 1 without adding results, broad safety claims or retrospective novelty claims.

| Must-have section/subsection | Best sources and classification | Extract and caution |
|---|---|---|
| 7.1 Thesis summary | [M01], [M03] M; [R02] R | Bounded architecture, three-condition Mode B evaluation and workflow closure. |
| 7.2 Answers to research questions | [I18], [I20], [I24], [I25] I; [R02] R | RQ1 responsibility separation; RQ2 measured routing/workload differences; RQ3 resource, timing and validity limits. Do not answer a prospective latency question with unsupported comparable evidence. |
| 7.3 Main contributions | [I17], [I24], [I37] I; [R02] R | Implemented distributed coordination and authorization, reproducible metric contract and completed comparative observations. |
| 7.4 Main findings | [R02], [R03], [R04] R; [E01] E | Lower observed Proposed FAR/FER than Threshold, conservative SA, common coverage and distinct HITL volume; one run each. |
| 7.5 Limitations | [R02] R; [M03], [M04] M; [I27] I | Synthetic labels/workload, retrospective policy, unequal warmup, simulation, reviewers and small deployment. |
| 7.6 Future work | [R01], [R02] R; [D01] D; [M02] M | New studies below are proposed work, not completed features or a pending fourth formal condition in this comparison. |
| 7.7 Closing statement | [R02] R; [I24], [I27] I | Demonstrated policy-bounded coordination on modest hardware with quantified benchmark trade-offs; no universal safety/production-readiness claim. |

Future-study plan: repeated balanced trials and statistical analysis; real datasets and new faults; stronger action-safety validation and controlled real remediation; separate retrieval/adaptation ablations; broader model/warmup comparisons; larger clusters and long-duration failure studies. These follow limitations in [R01], [R02], [M02], [D01] and do not constitute results. A future adaptation experiment would need a new reviewed protocol; the present final comparison remains exactly three conditions.

## 9. References — planning, not a thesis chapter

Repository sources support implementation, protocol and result claims; they are not substitutes for academic references. Chapter 2 needs peer-reviewed primary literature and a documented search/selection process. [D01]'s references and comparison framework are leads to verify, not permission to copy unverified bibliographic fields or numerical claims. [H01]'s stronger novelty/performance assertions are historical and must not supply the final gap argument.

Use official tool documentation for API/architecture claims about RabbitMQ, Ollama, ChromaDB, Django, Prometheus and Grafana where relevant; record versions and retrieval dates according to the required university/publication style. This map does not assert current external product behavior or supply fabricated bibliography entries. Keep in-text citations and bibliography consistent in author/year/title/venue/DOI. Preserve repository execution commits and artifact hashes in the reproducibility record separately from academic citations.

## 10. Appendices — supporting material

| Proposed appendix | Mapped sources/category | Extract; omit |
|---|---|---|
| A. Detailed architecture and message topology | [R01] R; [M01] M; [I17] I | Redrawn logical/physical/queue diagrams; omit credentials and historical unlabeled artwork. |
| B. Node/software/network inventory | [R01], [R04] R; [A05], [A06], [A07], [A08] A; [E03], [E04] E | Per-run hardware/software/model/revision facts and network verification; no fabricated uniform versions. |
| C. Event schema and detector rules | [I02], [I03], [I04], [I05], [I06], [I07], [I08], [I09], [I10], [I11], [I12], [I13], [I14], [I15], [I16] I | Representative runtime schema, active rules/settings, calibration boundary; no dump of all source code or secret configuration. |
| D. Agent contracts/prompts and baseline specifications | [I21], [I22], [I31], [I32], [I33], [I34], [I35] I | Selected exact academic-relevant schema/prompt/rule excerpts, versions and differences. |
| E. Formal procedures and lifecycle | [A01], [A02], [A03] A; [M03] M; [H04] H | Summarized cold-run/checklist and invalid-run exclusion, linked full procedure. Demo [A04] stays separately labeled. |
| F. Metrics/routing ground truth | [M03], [M04] M; [I37], [I38], [I39] I; [A11], [A12] A | Equations, ID join, v2 translation and denominator worked example; identify superseded scopes/formulas. |
| G. Observability configuration and figures | [A08], [A09] A; [E05] E | Relevant scrape/label settings and selected captioned screenshots; no entire dashboard JSON dump. |
| H. Supplementary results/provenance | [R02], [R03], [R04] R; [E01], [E02], [E03], [E04] E | Cross-tabs, per-node inventory references, execution hashes and independently verified analysis artifacts where available. |

## 11. Results and Discussion Quick Reference

### A. Final three-condition comparison

All scores below come from [R02], corroborated by [R03], [R04] and saved Proposed analysis [E01]. Full identities/provenance are in the master tables.

| Measure | Proposed Adaptive | Threshold-only | Single-Agent |
|---|---:|---:|---:|
| AUTO / HITL | 175 / 464 | 168 / 471 | 1 / 638 |
| FAR | 38/174 = 21.84% | 50/159 = 31.45% | 0/1 = 0% |
| Routing FER | 104/240 = 43.33% | 131/240 = 54.58% | 239/240 = 99.58% |
| Expected-AUTO controller coverage | 240/380 = 63.16% | 240/380 = 63.16% | 240/380 = 63.16% |
| Missing before routing | 140/380 = 36.84% | 140/380 = 36.84% | 140/380 = 36.84% |
| Risk accuracy | 513/630 = 81.43% | 449/630 = 71.27% | 443/630 = 70.32% |
| Feedback completion | 639/639 | 639/639 | 639/639 |

### B. Layer 1 accounting

| Shared recorded count | Value | Source |
|---|---:|---|
| Corpus | 1,950 | [R01], [R03], [R04] |
| Validator valid / structural bypass | 1,850 / 100 | [R01], [R03], [R04] |
| Cold calibration withheld | 323 | [R03]; also 1,850−1,527 |
| Detector/Fusion eligible | 1,527 | [R01], [R03], [R04] |
| Fusion published / suppressed | 539 / 988 | [R01], [E02], [R04] |
| Compound / Fast Path | 43 / 83 | [R01], [E02], [R04] |
| Controller incidents | 639 | 539+100, [R01], [R02], [R03], [R04] |

### C. Key observations

Proposed has lower observed FAR/FER than Threshold. SA structured validity coexists with near-total escalation. Eligible controller coverage is equal in aggregate; automation volume differs. HITL volume is highest for SA. All three complete feedback for their observed decisions. These are separate observations, not a single overall ranking.

### D. Interpretation cautions

Always give denominators; contextualize SA zero FAR with one AUTO and 239/240 FER. Exclude NORMAL from authoritative routing labels, not from total route counts. Keep expected-AUTO reach distinct from actual automation. Human approval and simulated success are not repair correctness. Compound/Fast Path counts overlap incident counts. Warmup/timing boundaries and study order prevent simple latency or causality claims.

### E. Main limitations

One formal run/condition; fixed order; synthetic workload and marker detector; local-model and reviewer variability; adaptive state; unequal dedicated warmup; retrospective Proposed routing translation; retrospective Wi-Fi source manifest; simulated remediation; three small machines; incomplete central availability of native node-local evidence. No adaptation-only ablation or repeated matched-network study was completed in this comparison.

### F. Claims we CAN safely make

- The implemented Policy deterministically bounds the authority of Strategy proposals [I24].
- The final active Layer 1 path uses statistical/deterministic rules, with a synthetic schema-marker limitation [I09], [I10], [I11], [I12], [I13], [I14], [I15].
- The architecture operated on the documented three commodity 8-GB machines for these completed runs [R01], [R02], [R03], [R04].
- Proposed achieved lower **observed** FAR and routing FER than Threshold in this completed benchmark comparison [R02].
- SA was highly conservative: one AUTO, 638 HITL and 239/240 routing FER [R04].
- Final feedback completion is 639/639 for observed decisions, subject to the separate lifecycle and upstream evidence requirements [R02], [M03].

### G. Claims we MUST NOT make

Do not claim universal safety, statistical significance, best/safest SA from 0/1 FAR, production readiness, arbitrary real-pipeline generalization, validated MTTR, precision/recall from counters, real service restoration from simulation, or isolated benefit of EMA/RAG/decomposition. Do not claim identical effective model state or a three-way latency winner. Do not count the resumed Threshold run as a formal replicate. Do not turn historical Wi-Fi values or superseded fourth-condition planning into final Ethernet evidence.

## 12. Recommended Writing Order

1. **Methodology and System Design:** strongest implementation support; pin correct responsibilities and interfaces before making research claims.
2. **Experimental Setup:** establish actual modes, execution identities, metric populations and validity limits before reading scores as conclusions.
3. **Evaluation/Results:** transfer the frozen tables with provenance and explicit fractions; select supporting figures.
4. **Discussion:** distinguish observed differences from hypotheses using the completed tables and limitations.
5. **Conclusion:** answer only what the implemented/evaluated work supports.
6. **Introduction:** align scope, research questions and contributions with the established body.
7. **Literature Review/Related Work:** complete the critical synthesis and external citation verification; start collecting/reading primary papers early even if final drafting is later.
8. **Abstract later:** condense the final problem, method, principal fractions and limits without introducing new claims.

Chapters 3–5 have strong repository support, although full independent reproduction requires the node-local artifact packet. Chapters 6–7 have bounded support from those observations, not evidence of general superiority. Chapters 1–2 need substantial external literature and careful novelty/positioning work. For a paper, prioritize shared routing results and the authority design; keep historical transport observations separate or supplementary.

### Evidence still needed or requiring verification before submission

- Obtain accessible approved Node 1/2 native records, reconciliation, verification outputs and inventories for all conditions if the thesis/paper promises an independently inspectable supplement. Local absence is not missing formal closeout evidence.
- Check exact hardware SKU, software/dependency/model versions and effective model settings against each run's inventory; do not infer uniformity from current code or historical planning.
- Verify selected images/captions and offline timing definitions against frozen execution artifacts; no matched cross-condition latency winner is established here.
- Verify primary academic publications, APA/institutional formatting and any external tool/version claims; this documentation audit did not perform a new literature search.
- Repeated trials, production datasets, verified repairs, reviewer-effort measurements and isolated adaptation/retrieval benefit are new research needs, not missing values to fill by inference.

## 13. Authoritative source index

The classifications below apply to references throughout this map. “Authority” is claim-specific: implementation source governs code behavior, while the frozen execution record governs a historical result. No source is authoritative for claims outside its inspected scope.

| ID / Repository path | Classification | Thesis chapter(s) | Purpose | Authority level / caution |
|---|---|---|---|---|
| **R01** — [README.md](../README.md) | RESULT SOURCE | 1, 3–7 | Project scope, hardware, Proposed Ethernet results and revised routing analysis | Mixed Wi-Fi/Ethernet sections: retain run IDs; later routing analysis supersedes blank-label availability. |
| **R02** — [evaluation/baselines/COMPARISON.md](../evaluation/baselines/COMPARISON.md) | RESULT SOURCE | 1, 4–7 | Final three-condition scope, identities, cross-tabs and metric fractions | Primary comparative synthesis; curated closeout, not a new raw-data analysis. |
| **R03** — [evaluation/baselines/threshold_only/results/ETHERNET_RESULTS.md](../evaluation/baselines/threshold_only/results/ETHERNET_RESULTS.md) | RESULT SOURCE | 4–7 | Threshold formal identity, reconciliation, metrics and HITL outcomes | Final completed run only; native Node 1/2 provenance distinguished from gateway checks. |
| **R04** — [evaluation/baselines/single_agent/README.md](../evaluation/baselines/single_agent/README.md) | RESULT SOURCE | 3–7 | Single-Agent architecture, final results, model identity, warmup and evidence paths | Formal closeout verified native evidence; documentation audit did not independently reopen all Node 2 files. |
| **R05** — [evaluation/baselines/threshold_only/README.md](../evaluation/baselines/threshold_only/README.md) | RESULT SOURCE | 3–7 | Threshold architecture and finalized result overview | Prefer R03 for detailed final-result citation. |
| **M01** — [docs/System_Design_and_Methodology.md](../docs/System_Design_and_Methodology.md) | METHODOLOGY SOURCE | 1, 3, 4, 6, 7 | Design rationale, physical/logical/message/Policy diagrams and validity framework | Implementation-oriented prose is useful; experiment/results refer to historical Wi-Fi revision, not final controller comparison. |
| **M02** — [evaluation/baselines/BASELINE_EXPERIMENT_DESIGN.md](../evaluation/baselines/BASELINE_EXPERIMENT_DESIGN.md) | METHODOLOGY SOURCE | 1, 3–7 | Research question, Mode A/B distinction, shared conditions and final amendment | Prospective sections and optional ablations are historical planning; no completed Mode A or repeated trials implied. |
| **M03** — [evaluation/baselines/ETHERNET_SHARED_EXPERIMENT_CONTRACT.md](../evaluation/baselines/ETHERNET_SHARED_EXPERIMENT_CONTRACT.md) | METHODOLOGY SOURCE | 3–7 | Final metrics, matched inputs, condition-specific evidence, run lifecycle and timing | Final three-condition contract overrides older comparison scope and common-analyzer definitions. |
| **M04** — [layer2/evaluation/ROUTING_LABEL_POLICY.md](../layer2/evaluation/ROUTING_LABEL_POLICY.md) | METHODOLOGY SOURCE | 4–6 | V2 source-label translation, retrospective timing, final denominator correction and hashes | Formula/label sections remain useful; fourth-condition and upcoming-run prose is superseded by R02/M03. |
| **D01** — [docs/Literature_Review.md](../docs/Literature_Review.md) | DISCUSSION SUPPORT | 1–3, 6, 7, References | Targeted review, thematic synthesis, requirements R1–R6, comparison matrix and bibliography leads | Existing literature is a starting point; prospective experiments/ablation/network statements are not final results. |
| **H01** — [docs/FYP_MASTER_REFERENCE.md](../docs/FYP_MASTER_REFERENCE.md) | HISTORICAL CONTEXT | 1, 2, Appendices | July planning evolution and earlier model/agent plans | Explicit archive: no current milestone, Learning-LLM, latency-target or novelty claim is authoritative. |
| **H02** — [docs/WIFI_VS_ETHERNET_COMPARISON.md](../docs/WIFI_VS_ETHERNET_COMPARISON.md) | HISTORICAL CONTEXT | 4–6 | Separate Proposed-only transport pair and fixed-order/network limitations | Retains original blank-label analysis; later R01/R02 routing results supersede Ethernet FAR/FER unavailability. |
| **H03** — [Full_Rerun.md](../Full_Rerun.md) | HISTORICAL CONTEXT | 4, Appendices | Historical Wi-Fi operational procedure | Do not substitute for current condition-specific Ethernet runbooks. |
| **H04** — [evaluation/baselines/threshold_only/HISTORICAL_RUNS.md](../evaluation/baselines/threshold_only/HISTORICAL_RUNS.md) | HISTORICAL CONTEXT | 4, 6, Appendices | Interrupted then resumed Threshold run and exclusion | Run ending 053739 is invalid for formal comparison even if exports appear clean. |
| **H05** — [layer1/evaluation/historical](../layer1/evaluation/historical) | HISTORICAL CONTEXT | 2, 3, Appendices | Earlier Random Forest/Isolation Forest detector experiments | Not active Layer 1 implementation or formal detector-quality evidence. |
| **A01** — [Ethernet_Full_Rerun.md](../Ethernet_Full_Rerun.md) | APPENDIX / REPRODUCIBILITY SOURCE | 4, Appendices | Proposed cold state, corpus reuse, startup, transport and evidence capture | Formal execution procedure and diagnostic mode differ; historical execution revision must stay explicit. |
| **A02** — [evaluation/baselines/threshold_only/ETHERNET_FULL_RUN.md](../evaluation/baselines/threshold_only/ETHERNET_FULL_RUN.md) | APPENDIX / REPRODUCIBILITY SOURCE | 4, Appendices | Threshold reset, readiness, lifecycle and offline evaluation | No attempt sidecar; new cold run after worker failure, never resume for formal evidence. |
| **A03** — [evaluation/baselines/single_agent/ETHERNET_FULL_RUN.md](../evaluation/baselines/single_agent/ETHERNET_FULL_RUN.md) | APPENDIX / REPRODUCIBILITY SOURCE | 4, Appendices | Single-Agent freeze, model/warmup, readiness and attempt evidence | Actual model-attempt evidence is condition-specific; not a fourth condition. |
| **A04** — [docs/ETHERNET_DEMO_RUNBOOK.md](../docs/ETHERNET_DEMO_RUNBOOK.md) | APPENDIX / REPRODUCIBILITY SOURCE | Appendices | Short future demonstration workflow | Demo outputs are not formal experimental evidence; never use as formal reset/scoring protocol. |
| **A05** — [deployment/ethernet/README.md](../deployment/ethernet/README.md) | APPENDIX / REPRODUCIBILITY SOURCE | 3, 4, Appendices | Three-node IP/interface map, environments, sockets and monitoring deployment | Template/instructions do not prove live state; per-node environment paths require verification. |
| **I01** — [layer1/seg/seg.py](../layer1/seg/seg.py) | IMPLEMENTATION SOURCE | 3, 4 | Generate/replay, UUID IDs, label stripping, replay timing | Read generate_corpus, _strip_ground_truth, save_corpus and replay logic; generation is not byte-identical reuse. |
| **I02** — [layer1/seg/event_templates.py](../layer1/seg/event_templates.py) | IMPLEMENTATION SOURCE | 3, 4 | Original severity, risk/action labels and synthetic fault construction | Ground truth precedes routing translation; runtime action identifiers are a different vocabulary. |
| **I03** — [layer1/validator/validator.py](../layer1/validator/validator.py) | IMPLEMENTATION SOURCE | 3, Appendices | Pydantic event contract, validation and valid/bypass routing | Schema validation is structural, not anomaly precision or recovery success. |
| **I04** — [layer1/validator/schema_drift_router.py](../layer1/validator/schema_drift_router.py) | IMPLEMENTATION SOURCE | 3 | Structural bypass, identity preservation and severity mapping | Opening PSI description is stale; executable bypass logic and I13 define active behavior. |
| **I05** — [layer1/feature_store/feature_store.py](../layer1/feature_store/feature_store.py) | IMPLEMENTATION SOURCE | 3, 4 | FeatureStore.process, per-component calibration and rolling window | Update precedes gate: the calibration-completing event is forwarded. |
| **I06** — [layer1/feature_store/baseline_calibrator.py](../layer1/feature_store/baseline_calibrator.py) | IMPLEMENTATION SOURCE | 3, 4 | BaselineCalibrator.update, freeze and persistence | Default constructor/comment is not active ADM setting; PSI comments do not establish an active PSI detector. |
| **I07** — [layer1/feature_store/feature_computers.py](../layer1/feature_store/feature_computers.py) | IMPLEMENTATION SOURCE | 3, Appendices | Feature calculations, rolling rates and standardized deviations | A computed feature is not necessarily consumed by an active detector. |
| **I08** — [layer1/adm/adm_runner.py](../layer1/adm/adm_runner.py) | IMPLEMENTATION SOURCE | 3, 4 | FeatureStore(calibration_n=20), on_message and fan-out | Acknowledges withheld events; cold calibration is not unexplained transport loss. |
| **I09** — [layer1/adm/detectors/cpu_spike.py](../layer1/adm/detectors/cpu_spike.py) | IMPLEMENTATION SOURCE | 3, Appendices | CPU/memory standardized and raw-threshold detection | Statistical rules; no active Isolation Forest. |
| **I10** — [layer1/adm/detectors/error_rate.py](../layer1/adm/detectors/error_rate.py) | IMPLEMENTATION SOURCE | 3, Appendices | Error-rate standardized and raw-threshold detection | Header says Z > 3; active setting is 2.0. Cite executable comparison plus I14. |
| **I11** — [layer1/adm/detectors/throughput_drop.py](../layer1/adm/detectors/throughput_drop.py) | IMPLEMENTATION SOURCE | 3, Appendices | Moving-average/raw throughput and silence rules | Worker failure invalidity is separate from detector semantics. |
| **I12** — [layer1/adm/detectors/auth_flood.py](../layer1/adm/detectors/auth_flood.py) | IMPLEMENTATION SOURCE | 3, Appendices | Authentication-rate and rate-change rules | No active Random Forest classification. |
| **I13** — [layer1/adm/detectors/schema_drift.py](../layer1/adm/detectors/schema_drift.py) | IMPLEMENTATION SOURCE | 3, 6 | SchemaDetector.detect checks distribution_shift_marker | Synthetic marker equality, not general PSI/distribution-shift inference. |
| **I14** — [layer1/adm/config/detector_config.json](../layer1/adm/config/detector_config.json) | IMPLEMENTATION SOURCE | 3, Appendices | Effective detector rule settings | Pair with detector consumers; do not copy credentials from neighboring configuration files. |
| **I15** — [layer1/fusion_engine/fusion_engine.py](../layer1/fusion_engine/fusion_engine.py) | IMPLEMENTATION SOURCE | 3, 4 | Correlation, late recovery, _fuse, confidence suppression and compound output | Fast Path marks priority; not proof of immediate finalization or recovery speed. |
| **I16** — [layer1/fusion_engine/config/fusion_config.json](../layer1/fusion_engine/config/fusion_config.json) | IMPLEMENTATION SOURCE | 3, Appendices | 3.0 s primary + 0.75 s recovery, weights and confidence gate | Extract non-secret settings only; distinguish configuration from measured timing. |
| **I17** — [layer1/rabbitmq/setup_topology.py](../layer1/rabbitmq/setup_topology.py) | IMPLEMENTATION SOURCE | 3, Appendices | Exchanges, bindings, queues, vhost and DLX | Read only; topology declaration is not proof of exactly-once delivery. Omit credentials. |
| **I18** — [layer2/agents/triage_agent.py](../layer2/agents/triage_agent.py) | IMPLEMENTATION SOURCE | 3 | classify, _normalize_event, retrieve_rag_context and payload | Deterministic protocol mapping; not an LLM decision agent. |
| **I19** — [layer2/chromadb_utils/query.py](../layer2/chromadb_utils/query.py) | IMPLEMENTATION SOURCE | 3, 6 | Cold retrieval, positive outcome filtering and context formatting | Do not claim measured retrieval benefit or guaranteed risk-tier balance from intent comments. |
| **I20** — [layer2/agents/strategy_agent.py](../layer2/agents/strategy_agent.py) | IMPLEMENTATION SOURCE | 3 | qwen3:1.7b structured generation, validation, retry and timing | Only Proposed LLM stage; schema-valid is not action-correct. |
| **I21** — [layer2/agents/schema_validator.py](../layer2/agents/schema_validator.py) | IMPLEMENTATION SOURCE | 3, Appendices | Seven fields, action vocabulary, severity-bound risk schema and validation | Stricter than Single-Agent generic validation; preserve architectural difference. |
| **I22** — [layer2/prompts/strategy_system_prompt.txt](../layer2/prompts/strategy_system_prompt.txt) | IMPLEMENTATION SOURCE | 3, Appendices | Proposal contract and severity/risk instructions | Prompt is an implemented constraint, not a guarantee of model compliance. |
| **I23** — [layer2/ollama/client.py](../layer2/ollama/client.py) | IMPLEMENTATION SOURCE | 3, 4 | Local Ollama HTTP request/options/schema forwarding | Do not infer effective runtime defaults or installed model digest from client code alone. |
| **I24** — [layer2/agents/policy_agent.py](../layer2/agents/policy_agent.py) | IMPLEMENTATION SOURCE | 3, 6 | PolicyAgent.route, threshold loading and measured latency boundaries | Deterministic AUTO/HITL authority; no formal safety proof; E2E field starts at Triage timestamp. |
| **I25** — [layer2/agents/learning_agent.py](../layer2/agents/learning_agent.py) | IMPLEMENTATION SOURCE | 3, 6 | Deterministic summary, outcome signals, bounded EMA and memory update | No LLM summarization or weight training; rejection signal can lower threshold. |
| **I26** — [layer2/chromadb_utils/upsert.py](../layer2/chromadb_utils/upsert.py) | IMPLEMENTATION SOURCE | 3 | Incident persistence and outcome metadata | Stored memory/upsert count does not measure quality or retrieval effectiveness. |
| **I27** — [layer3/auto_executor/executor.py](../layer3/auto_executor/executor.py) | IMPLEMENTATION SOURCE | 3, 6 | execute_actions simulation, outcome feedback and metrics | Nonempty actions simulate success after 0.5 s; not real repair or MTTR. |
| **I28** — [layer3/dashboard/hitl/models.py](../layer3/dashboard/hitl/models.py) | IMPLEMENTATION SOURCE | 3 | HitlIncident identity, status, arrival and decided_at | Persisted pending human work differs from RabbitMQ ready messages. |
| **I29** — [layer3/dashboard/hitl/views.py](../layer3/dashboard/hitl/views.py) | IMPLEMENTATION SOURCE | 3, 6 | Terminal decision persistence, approve/reject/modify and feedback | Database state and feedback delivery are separate; no atomic distributed exactly-once claim. |
| **I30** — [layer3/dashboard/hitl/management/commands/consume_hitl.py](../layer3/dashboard/hitl/management/commands/consume_hitl.py) | IMPLEMENTATION SOURCE | 3 | get_or_create persistence and acknowledgement | Duplicate delivery should not reopen a completed human decision. |
| **I31** — [evaluation/baselines/threshold_only/rules.py](../evaluation/baselines/threshold_only/rules.py) | IMPLEMENTATION SOURCE | 3, 4 | decide first-match precedence, risk/actions and routes | Fixed deterministic baseline; no confidence gate, model or feedback adaptation. |
| **I32** — [evaluation/baselines/threshold_only/rules.json](../evaluation/baselines/threshold_only/rules.json) | IMPLEMENTATION SOURCE | 3, 4, Appendices | Versioned rule/action specification | Retain reviewed settings; do not tune to observed results. |
| **I33** — [evaluation/baselines/single_agent/controller.py](../evaluation/baselines/single_agent/controller.py) | IMPLEMENTATION SOURCE | 3, 4 | Controller.decide, real attempts, accepted route, fallback and journal | At most two model calls for eligible validation retry; valid route is not overridden by Proposed Policy. |
| **I34** — [evaluation/baselines/single_agent/schema.py](../evaluation/baselines/single_agent/schema.py) | IMPLEMENTATION SOURCE | 3 | Generic output validity, action count/enums and uniqueness | Does not impose Proposed confidence/risk routing rules. |
| **I35** — [evaluation/baselines/single_agent/llm_client.py](../evaluation/baselines/single_agent/llm_client.py) | IMPLEMENTATION SOURCE | 3, 4 | qwen3:1.7b, options, transport errors, identity and warmup | Installed defaults/residency require actual run evidence; model-family match is insufficient. |
| **I36** — [evaluation/baselines/common/journal.py](../evaluation/baselines/common/journal.py) | IMPLEMENTATION SOURCE | 3, 4 | Native SQLite journal, prepare/confirm and exports | Durability/accounting mechanism, not proof of uninterrupted upstream execution. |
| **I37** — [evaluation/baselines/shared/evaluate.py](../evaluation/baselines/shared/evaluate.py) | IMPLEMENTATION SOURCE | 4, 5 | load_labels, normalize, evaluate and main; cross-tab verification | Offline baseline scorer; optional supplied artifacts must exist; no lifecycle certification. |
| **I38** — [layer2/evaluation/analyze_run.py](../layer2/evaluation/analyze_run.py) | IMPLEMENTATION SOURCE | 4, 5 | Proposed native stage analysis, automation_metrics, risk and timing | Invalid existing Policy records are separated from absent Policy records. |
| **I39** — [layer2/evaluation/generate_routing_labels.py](../layer2/evaluation/generate_routing_labels.py) | IMPLEMENTATION SOURCE | 4 | routing_label and deterministic separate-output generation | Use original ground-truth fields only; do not regenerate during thesis writing. |
| **I40** — [evaluation/baselines/shared/verify_revision.py](../evaluation/baselines/shared/verify_revision.py) | IMPLEMENTATION SOURCE | 4, Appendices | Revision/inventory hashes, branch and clean-tree checks | Verifies supplied inventory, not inventory completeness, human approval or installed state. |
| **A06** — [deployment/ethernet/node2.env.sh](../deployment/ethernet/node2.env.sh) | APPENDIX / REPRODUCIBILITY SOURCE | 3, 4 | Ethernet broker endpoint and localhost Ollama | Environment export affects newly launched processes only. |
| **A07** — [deployment/ethernet/node3.env.sh](../deployment/ethernet/node3.env.sh) | APPENDIX / REPRODUCIBILITY SOURCE | 3, 4 | Gateway Ethernet broker endpoint | Does not alter SQLite/Chroma locations or prove effective sockets. |
| **A08** — [deployment/ethernet/prometheus.ethernet.yml](../deployment/ethernet/prometheus.ethernet.yml) | APPENDIX / REPRODUCIBILITY SOURCE | 3, 4, Appendices | Jobs, ports, logical labels and scrape intervals | Template is not proof of the running server configuration. |
| **A09** — [layer3/grafana/FYP_Hybrid_Agentic_Framework_Observability_v3_Node_Naming.json](../layer3/grafana/FYP_Hybrid_Agentic_Framework_Observability_v3_Node_Naming.json) | APPENDIX / REPRODUCIBILITY SOURCE | 3–5, Appendices | Current Proposed panels, PromQL and display choices | Panel estimates/time windows are not full-run offline aggregates. |
| **A10** — [layer1/feature_store/test_feature_store.py](../layer1/feature_store/test_feature_store.py) | APPENDIX / REPRODUCIBILITY SOURCE | 3, 4 | Calibration test with n=3: first two withheld, third forwarded | Test inspected, not executed for this map; generalize using actual n=20 call site. |
| **A11** — [evaluation/baselines/shared/tests/test_evaluate.py](../evaluation/baselines/shared/tests/test_evaluate.py) | APPENDIX / REPRODUCIBILITY SOURCE | 4, Appendices | Metric, partial-run, NORMAL, optional evidence and integrity regression cases | Tests explain contract intent; not formal experiment evidence or a new test-pass claim. |
| **A12** — [layer2/tests/test_routing_labels.py](../layer2/tests/test_routing_labels.py) | APPENDIX / REPRODUCIBILITY SOURCE | 4, Appendices | Source-field preservation, denominator and invalid-route tests | Tests inspected only; distinguish absent records from invalid existing records. |
| **E01** — [experiment_runs/ethernet_cold_20261002_023108/offline_eval_inputs/evaluation_summary.json](../experiment_runs/ethernet_cold_20261002_023108/offline_eval_inputs/evaluation_summary.json) | EXPERIMENTAL EVIDENCE | 5, 6 | Saved final v2 Proposed routing/risk/coverage summary | Read directly for this map; preserved output, not regenerated. Local artifact may be absent in a fresh clone. |
| **E02** — [experiment_runs/threshold-ethernet-full-20261003-084252/metrics/10.10.10.11:8003-final.prom](../experiment_runs/threshold-ethernet-full-20261003-084252/metrics/10.10.10.11:8003-final.prom) | EXPERIMENTAL EVIDENCE | 5 | Threshold Fusion publications/suppression/compound/fast-path counters | Directly read final snapshot; not event-level proof, continuous trace or precision/recall. |
| **E03** — [experiment_runs/single-agent-ethernet-full-20261004-035637](../experiment_runs/single-agent-ethernet-full-20261004-035637) | EXPERIMENTAL EVIDENCE | 4, 5, Appendices | Local gateway protocol, inventory, metric and human-state evidence location | Existence/inventory checked; not a fresh audit of every native Node 2 result or database. |
| **E04** — [experiment_runs/threshold-ethernet-full-20261003-084252](../experiment_runs/threshold-ethernet-full-20261003-084252) | EXPERIMENTAL EVIDENCE | 4, 5, Appendices | Local gateway protocol, inventory, metrics and preserved state location | Node-local copy; missing Node 1/2 files are not evidence of missing closeout. |
| **E05** — [docs/experiment_results/ethernet](../docs/experiment_results/ethernet) | EXPERIMENTAL EVIDENCE | 5, Appendices | Seven Proposed Ethernet screenshots | Visual support only; condition/time window required, no baseline metrics inferred. |
| **E06** — [docs/experiment_results/wifi](../docs/experiment_results/wifi) | HISTORICAL CONTEXT | 5, Appendices | Historical Wi-Fi screenshots | Do not use as final Ethernet figures. |
| **H06** — [evaluation/baselines/common/analyze_comparison.py](../evaluation/baselines/common/analyze_comparison.py) | HISTORICAL CONTEXT | 4, Appendices | Older Mode A comparison analyzer | Its FAR/FER denominators are superseded for final Ethernet Mode B. |

<!-- Reference definitions: repository-relative paths verified at the inspection revision. -->
[R01]: ../README.md
[R02]: ../evaluation/baselines/COMPARISON.md
[R03]: ../evaluation/baselines/threshold_only/results/ETHERNET_RESULTS.md
[R04]: ../evaluation/baselines/single_agent/README.md
[R05]: ../evaluation/baselines/threshold_only/README.md
[M01]: ../docs/System_Design_and_Methodology.md
[M02]: ../evaluation/baselines/BASELINE_EXPERIMENT_DESIGN.md
[M03]: ../evaluation/baselines/ETHERNET_SHARED_EXPERIMENT_CONTRACT.md
[M04]: ../layer2/evaluation/ROUTING_LABEL_POLICY.md
[D01]: ../docs/Literature_Review.md
[H01]: ../docs/FYP_MASTER_REFERENCE.md
[H02]: ../docs/WIFI_VS_ETHERNET_COMPARISON.md
[H03]: ../Full_Rerun.md
[H04]: ../evaluation/baselines/threshold_only/HISTORICAL_RUNS.md
[H05]: ../layer1/evaluation/historical
[A01]: ../Ethernet_Full_Rerun.md
[A02]: ../evaluation/baselines/threshold_only/ETHERNET_FULL_RUN.md
[A03]: ../evaluation/baselines/single_agent/ETHERNET_FULL_RUN.md
[A04]: ../docs/ETHERNET_DEMO_RUNBOOK.md
[A05]: ../deployment/ethernet/README.md
[I01]: ../layer1/seg/seg.py
[I02]: ../layer1/seg/event_templates.py
[I03]: ../layer1/validator/validator.py
[I04]: ../layer1/validator/schema_drift_router.py
[I05]: ../layer1/feature_store/feature_store.py
[I06]: ../layer1/feature_store/baseline_calibrator.py
[I07]: ../layer1/feature_store/feature_computers.py
[I08]: ../layer1/adm/adm_runner.py
[I09]: ../layer1/adm/detectors/cpu_spike.py
[I10]: ../layer1/adm/detectors/error_rate.py
[I11]: ../layer1/adm/detectors/throughput_drop.py
[I12]: ../layer1/adm/detectors/auth_flood.py
[I13]: ../layer1/adm/detectors/schema_drift.py
[I14]: ../layer1/adm/config/detector_config.json
[I15]: ../layer1/fusion_engine/fusion_engine.py
[I16]: ../layer1/fusion_engine/config/fusion_config.json
[I17]: ../layer1/rabbitmq/setup_topology.py
[I18]: ../layer2/agents/triage_agent.py
[I19]: ../layer2/chromadb_utils/query.py
[I20]: ../layer2/agents/strategy_agent.py
[I21]: ../layer2/agents/schema_validator.py
[I22]: ../layer2/prompts/strategy_system_prompt.txt
[I23]: ../layer2/ollama/client.py
[I24]: ../layer2/agents/policy_agent.py
[I25]: ../layer2/agents/learning_agent.py
[I26]: ../layer2/chromadb_utils/upsert.py
[I27]: ../layer3/auto_executor/executor.py
[I28]: ../layer3/dashboard/hitl/models.py
[I29]: ../layer3/dashboard/hitl/views.py
[I30]: ../layer3/dashboard/hitl/management/commands/consume_hitl.py
[I31]: ../evaluation/baselines/threshold_only/rules.py
[I32]: ../evaluation/baselines/threshold_only/rules.json
[I33]: ../evaluation/baselines/single_agent/controller.py
[I34]: ../evaluation/baselines/single_agent/schema.py
[I35]: ../evaluation/baselines/single_agent/llm_client.py
[I36]: ../evaluation/baselines/common/journal.py
[I37]: ../evaluation/baselines/shared/evaluate.py
[I38]: ../layer2/evaluation/analyze_run.py
[I39]: ../layer2/evaluation/generate_routing_labels.py
[I40]: ../evaluation/baselines/shared/verify_revision.py
[A06]: ../deployment/ethernet/node2.env.sh
[A07]: ../deployment/ethernet/node3.env.sh
[A08]: ../deployment/ethernet/prometheus.ethernet.yml
[A09]: ../layer3/grafana/FYP_Hybrid_Agentic_Framework_Observability_v3_Node_Naming.json
[A10]: ../layer1/feature_store/test_feature_store.py
[A11]: ../evaluation/baselines/shared/tests/test_evaluate.py
[A12]: ../layer2/tests/test_routing_labels.py
[E01]: ../experiment_runs/ethernet_cold_20261002_023108/offline_eval_inputs/evaluation_summary.json
[E02]: ../experiment_runs/threshold-ethernet-full-20261003-084252/metrics/10.10.10.11:8003-final.prom
[E03]: ../experiment_runs/single-agent-ethernet-full-20261004-035637
[E04]: ../experiment_runs/threshold-ethernet-full-20261003-084252
[E05]: ../docs/experiment_results/ethernet
[E06]: ../docs/experiment_results/wifi
[H06]: ../evaluation/baselines/common/analyze_comparison.py
