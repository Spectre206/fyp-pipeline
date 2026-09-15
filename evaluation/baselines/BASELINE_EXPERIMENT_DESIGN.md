# Baseline Experiment Design

**Project:** Distributed Multi-Agent Coordination for Self-Healing Data Pipelines: A Human-in-the-Loop Approach on Commodity Hardware

## 1. Purpose and Research Question

This document establishes the comparative-evaluation protocol for three control-plane conditions:

1. **Baseline 0 — Threshold-Only**
2. **Baseline 1 — Single-Agent LLM**
3. **Proposed System — Heterogeneous Multi-Agent Architecture**

The primary research question is:

> How does the proposed heterogeneous, policy-bounded control architecture compare with a deterministic threshold controller and a monolithic single-agent LLM controller in decision quality, governance behavior, latency, reliability, human workload, and resource consumption?

The comparison does not assume that the proposed system will outperform simpler alternatives. Lower processing latency for Threshold-Only is a hypothesis, not a result. Separation of responsibilities is an architectural property; any improvement in decision quality or governance outcomes must be measured.

The protocol is prospective. Dataset selection, independent labels, controller specifications, run counts, and analysis settings must be recorded and frozen before formal comparative outputs are inspected. The outstanding freeze items are listed in Section 18. No baseline implementation or completed comparative result is established by this document.

## 2. Experimental Conditions

### 2.1 Baseline 0 — Threshold-Only

A deterministic controller replaces the complete proposed Layer 2 control plane:

```text
Layer 1 incident → fixed rules → AUTO / HITL → shared Layer 3
```

The controller uses only information available in the incoming `anomaly.detected` incident. It has no LLM inference, Ollama dependency, ChromaDB retrieval, separate Triage/Strategy/Policy agents, Learning, or EMA adaptation. Routing and action selection follow a predefined rule table.

Rules, thresholds, precedence, action mappings, and missing-input behavior must be specified before formal evaluation. They must not be fitted to Proposed Policy decisions, Strategy outputs, final human decisions, or baseline predictions. Development smoke cases must be identified separately from the formal evaluation set.

### 2.2 Baseline 1 — Single-Agent LLM

One monolithic generative controller replaces the heterogeneous Layer 2 architecture:

```text
Layer 1 incident → Single-Agent qwen3:1.7b
                 → generic output validation
                 → accepted route recommendation or invalid-output escalation
                 → shared Layer 3
```

The controller uses local Ollama inference to interpret the incident, propose actions, assess risk, and recommend AUTO or HITL. The primary condition has no separate Triage or Policy agent, ChromaDB retrieval, persistent conversational memory, Learning, or EMA adaptation.

A generic deterministic validator checks structured output, required fields, enums, types, ranges, and the shared action vocabulary. It must not impose the proposed system's risk/confidence routing rules or severity-to-risk binding. Valid route recommendations are retained for evaluation, including recommendations that independent labels later identify as inappropriate.

Malformed output, invalid actions, and exhausted generation failures are recorded explicitly and escalated to HITL. This is a contract-failure fallback, not an implementation of the proposed Policy. Record the raw recommendation, validation outcome, and final dispatched route separately; fallback escalation must not be counted as successful model output.

### 2.3 Proposed System

The existing heterogeneous architecture remains behaviorally unchanged:

```text
Layer 1 incident → Triage → Strategy → Policy → AUTO / HITL
                                                   ↓
                                               shared Layer 3
                                                   ↓
                                                feedback → Learning
```

- **Triage:** deterministic protocol mapping and ChromaDB retrieval.
- **Strategy:** the only LLM-backed agent, using `qwen3:1.7b` through local Ollama.
- **Policy:** deterministic authorization using Strategy validation status and routing rules.
- **Learning:** deterministic feedback retention, memory updates, and bounded EMA threshold adaptation.

Strategy proposes; Policy authorizes or escalates. A run must identify the exact proposed-system implementation and configuration revision used.

## 3. Shared Components and Comparison Boundary

### 3.1 Layer 1 — Real-Time Statistical Data Plane

Keep SEG/replay, Pydantic validation, Feature Store, ADM Runner, the five statistical/deterministic detectors, Fusion, structural schema bypass, and RabbitMQ publication unchanged. Do not tune detection or Fusion separately for a baseline.

All controllers begin at the **`anomaly.detected` incident boundary**. Logical incident identities and original boundary information must be preserved.

### 3.2 Layer 3 — Execution, Human Oversight & Observability Layer

Use the same Auto Executor, Django approve/reject/modify workflow, persistence, feedback publication, and observability infrastructure across conditions. AUTO handling remains simulated; none of the controllers receives unrestricted control of real infrastructure.

The current Layer 3 expects a nested decision payload. Baseline adapters may package their outputs for this interface, but must not fabricate Triage/Strategy inference, invoke the proposed Policy, or change baseline decisions. Preserve controller identity, actual reasoning, original input, and validation/fallback status in evaluation records. Freeze the adapter contract before formal runs.

Run one controller condition at a time against shared queues and Layer 3 state. A different metrics port or run ID does not isolate RabbitMQ consumers. Verify that inactive controllers and gateway processes cannot consume the run's messages or publish stale feedback.

## 4. Evaluation Modes

### 4.1 Mode A — Primary Control-Plane Comparison

Replay the same captured incident population into each controller. Layer 1 is not rerun separately for each condition.

```text
Identical frozen incident file
    ├── Threshold-Only
    ├── Single-Agent LLM
    └── Proposed System
```

This fixes detector output, calibration effects, Fusion composition, and incident count. Also freeze incident ordering and the replay arrival schedule. Identical records replayed at different rates do not constitute an equivalent latency workload.

Retain original incident timestamps as provenance. Record fresh replay publication and controller timestamps for each run so historical capture times are not mistaken for queue waiting time.

### 4.2 Mode B — Secondary Full-Pipeline Comparison

Replay the same original event corpus through Layer 1, the selected controller, and shared Layer 3. Use identical Layer 1 settings, cold-state procedures, arrival rate, hardware, and network condition.

This mode evaluates complete-system effects. Record the actual incident population produced in every run; do not assume it is identical merely because the original event corpus is identical. Report differences rather than forcing reconciliation to a previous run's counts.

Analyze Mode A and Mode B separately.

## 5. Frozen Incident Dataset

Capture actual Layer 1 incident payloads in a versioned JSONL dataset, with a manifest recording its checksum, source run, capture boundary, record count, unique identifiers, ordering, and replay schedule.

Preserve available information, including:

- Event/incident identity, anomaly type, severity, and affected component.
- Original timestamps and logical node labels.
- Detector/Fusion context and confidence fields actually present at the boundary.
- Structural-bypass or fused origin where available.

Do not invent missing fields or add Proposed Triage, Strategy, Policy, or human-decision outputs to baseline input. Evaluation labels must remain inaccessible to every runtime controller.

Use the exact same file in all Mode A conditions. Do not assume that the dataset necessarily contains 639 incidents; that count belongs to an earlier recorded run and must be verified for the selected capture.

If compute constraints require a subset, select it before comparative evaluation. Stratify by anomaly family, structural/fused origin, and relevant severity categories; record the selection procedure, seed, final counts, and exclusions. Do not reduce or rebalance the dataset in response to a controller's performance.

## 6. Independent Ground Truth

Existing experiment labels are insufficient to establish all controller routing and action-quality metrics. Prepare independent incident-level labels before inspecting comparative outputs.

| Field | Meaning |
|---|---|
| `incident_id` | Exact identity matching the frozen incident record. |
| `expected_route` | Independently justified AUTO or HITL disposition. |
| `safe_to_auto` | Whether automatic handling is acceptable under the stated experimental assumptions. |
| `expected_risk` | Independently assessed risk using a frozen category definition. |
| `acceptable_actions` | Set of acceptable identifiers from the common vocabulary. |

Record annotation rationale, ambiguity, and adjudication where needed. Optional labels may specify required action categories or prohibited actions. Define whether acceptable actions are exhaustive and whether safety depends on choosing a particular acceptable action set.

Labels must not be derived from current Policy outputs, Strategy responses, final human decisions, or baseline predictions. Annotators should assess the incident and explicit task assumptions without access to evaluated outputs. Resolve disagreements and inconsistent labels before scoring. In particular, an unsafe incident must not simultaneously be labeled AUTO-eligible.

Keep ambiguous or incompletely labeled incidents visible in workload and completion accounting. Freeze their metric-specific inclusion rules, and report coverage and excluded counts. Do not silently discard difficult cases.

## 7. Action-Space Fairness

Use the proposed system's action vocabulary, frozen from [the Strategy contract](../../layer2/agents/schema_validator.py), for all conditions. Use the same three-distinct-action constraint for valid action proposals; invalid-output escalations remain separately identified.

Do not use the complete Strategy validator unmodified for the primary Single-Agent baseline: it contains a severity/risk relationship specific to the proposed system. Share vocabulary and generic structural constraints without importing that decision constraint.

Score action sets without requiring exact ordering. Report:

- Vocabulary and cardinality validity.
- Relevance of selected actions against independent acceptable-action labels.
- Coverage of independently required actions or categories, where annotated.
- Selection of explicitly prohibited actions, where annotated.

A list of alternative acceptable actions is not automatically a list of required actions. Freeze action-scoring rules and denominators before evaluation.

## 8. Routing and Decision-Quality Metrics

The following definitions are common to every condition. Report numerators, denominators, label coverage, and missing-decision counts alongside percentages. A zero denominator is **not computable**, not zero error.

| Metric | Definition |
|---|---|
| Route accuracy | Correct final AUTO/HITL decisions divided by all incidents with an unambiguous expected-route label. Missing decisions do not count as correct. |
| False Automation Rate (FAR) | Incidents labeled unsafe that receive AUTO divided by all incidents labeled unsafe. |
| False Escalation Rate (FER) | Safe AUTO-eligible incidents receiving HITL divided by all incidents labeled both safe and expected AUTO. |
| Risk-tier accuracy | Correct risk classifications divided by incidents with an unambiguous expected-risk label; missing/invalid classifications are not correct. |
| Decision completion | Unique incidents with a final dispatched AUTO/HITL decision divided by all expected incident IDs. |

The FAR denominator is the **unsafe population**, not all AUTO decisions. These quantities must not be relabeled or changed after results are observed. Missing decisions do not enter FAR/FER error numerators, so both rates must be interpreted together with completion and label coverage.

Report raw model route quality separately from dispatched-route quality when generic validation changes the Single-Agent route to HITL. Likewise, distinguish proposal risk from final routing. Proposed Strategy's risk output is constrained by its existing schema; risk accuracy is therefore not an isolated measure of unconstrained LLM reasoning.

Record malformed output, schema/contract failures, action quality, and completion independently. JSON validity is not semantic correctness, and a valid allowlisted action is not proof of suitability or repair.

## 9. Human Workload and Feedback

Report HITL and AUTO counts, proportions, persisted pending incidents, review latency, and approve/reject/modify counts. Distinguish RabbitMQ backlog from persisted cases awaiting review.

Freeze the human-review procedure, reviewer allocation, review window, and completion criterion across conditions. Prefer condition-blinded review where feasible. If review is sampled rather than exhaustive, predefine the sample and make feedback denominators reflect that choice. Human outcomes are observations, not retrospective ground-truth labels.

Only the proposed condition runs Learning. Baseline feedback is retained for accounting without updating thresholds, retrieval memory, or model state. Define an accounting consumer for baseline feedback so shared feedback queues do not accumulate unobserved messages or feed a later proposed-system run.

For the proposed condition, record when feedback becomes available, since review timing can affect subsequent memory and threshold values. Lower HITL volume or greater AUTO volume alone does not establish improvement.

## 10. Performance, Reliability, and Resources

### 10.1 Timing

Record common timestamp boundaries for replay publication, controller receipt, decision publication, Layer 3 receipt, and terminal handling. Use these to separate input queue wait, controller residence time, downstream wait, and handling time. Record clock synchronization and use monotonic timing for local durations.

Controller residence time includes the proposed system's internal handoffs and waits. Component processing and model-generation time are additional measures, not interchangeable substitutes. The existing proposed-system Triage-to-Policy metric must not be directly compared against a differently bounded baseline metric.

Report latency distributions, throughput, elapsed run duration, incomplete observations at the cutoff, and queue drain time. For LLM conditions, also report timeouts, generation attempts, retries, and tokens per second where available. Timeout and failure cases must not disappear from reliability reporting because a latency statistic includes only completed requests.

### 10.2 Reliability

Reconcile expected IDs with received incidents, decisions, Layer 3 records, and feedback. Record missing and duplicate deliveries, repeated decisions, malformed messages, timeouts, dead letters, ready/unacknowledged messages, and pending human work. Deduplicated totals must not conceal duplicate side effects.

### 10.3 Resources

Measure CPU, memory, network traffic, node health, and model-server utilization where applicable. Report per-component and whole-node measurements, with active processes and idle resource use identified. Keep monitoring intervals and instrumentation overhead comparable; do not run unused model or learning workloads in a baseline condition without documenting them.

## 11. Hardware and Network Controls

| Logical node | Fixed role |
|---|---|
| `stream-node` | Layer 1 and RabbitMQ |
| `ai-brain-node` | Selected control-plane condition |
| `gateway-node` | Shared Layer 3 and observability |

Use the same physical machines, software versions, power settings, and background-service configuration across the primary architecture comparison. That comparison initially uses **Wi-Fi**.

Ethernet is a separate later infrastructure comparison. Hold architecture and physical hosts constant when comparing network media. If a replacement gateway laptop is required, use it for both matched network conditions or explicitly report that host replacement and network transport are confounded.

Preserve logical node labels independently of physical machine names. Record actual endpoint configuration, negotiated links, and routes for each network experiment.

## 12. LLM Controls

For Single-Agent and Proposed Strategy, hold model identity (`qwen3:1.7b`), model digest, Ollama version, Node 2 hardware, generation settings, action vocabulary, incident set, and network condition constant where applicable.

Freeze and record prompts, structured-output schemas, context/output limits, generation timeout, retry eligibility, maximum attempts, sampling settings, and model warm-up policy before formal evaluation. Use the same maximum generation-attempt budget where applicable and document unavoidable differences. Do not grant additional retries after observing poor results.

The primary comparison intentionally differs in retrieval, prompt structure, deterministic governance, and feedback adaptation. It evaluates complete controller packages; it cannot attribute all differences solely to the number of components or to an LLM's reasoning ability.

## 13. Initial State and Run Isolation

Before each run, establish a documented initial state:

- Identical frozen workload, labels, order, and arrival schedule for the selected mode.
- Fresh controller processes and separate run outputs.
- Empty relevant queues, with no stale publishers or competing consumers.
- Fresh shared Layer 3 decision/HITL state for a cold run.
- Consistent model-loading/warm-up and monitoring procedures.

For the proposed condition, reset ChromaDB and EMA state according to the frozen cold-state procedure. Threshold-Only has no adaptive state; Single-Agent has no persistent memory in the primary condition. Mode B additionally resets Layer 1 calibration and other state consistently.

Archive prior evidence before resetting state. A run identifier selects output records; it does not by itself isolate shared broker queues, databases, or ChromaDB. Runs are sequential unless independent infrastructure and state isolation are explicitly established.

## 14. Repetition and Analysis

Freeze the number of repetitions, controller order, seeds where supported, and run completion/timeout rules before formal outputs are inspected. Use balanced or randomized condition order to reduce time-of-day, thermal, and background-load effects.

Threshold-Only should produce the same decisions for identical inputs and rules, but its measured latency and resources can still vary. LLM output and adaptive feedback can also vary. Record repeated runs separately, report variation, and use a prespecified uncertainty-analysis method. Do not treat repeated observations of the same incident as independent workload samples without accounting for that structure.

Predefine infrastructure-failure handling and rerun criteria. Preserve failed runs with their exclusion reasons. No controller's poor quality or slow completion is grounds for retrospective dataset changes or selective reruns.

## 15. Secondary Ablations

These optional studies do not replace the primary three-condition comparison:

| Ablation | Purpose and control |
|---|---|
| Single-Agent + identical Policy | Separate deterministic-governance effects from the primary monolithic baseline; hold other Single-Agent settings constant. |
| Proposed fixed threshold versus adaptive EMA | Evaluate threshold adaptation while holding retrieval configuration and initial state constant. |

If retrieval benefit is studied, vary it independently and label it as an additional condition. Bounded adaptation alone does not establish beneficial or conservative behavior. Record feedback ordering and state availability when interpreting adaptation results.

## 16. Evidence and Reproducibility

Retain workload and label checksums, code/configuration revisions, rule tables, prompts, model metadata, environment versions, timestamps, raw controller outputs, validation outcomes, dispatched decisions, Layer 3 records, feedback, and monitoring exports for every run.

Keep proposed-system metrics and dashboards unchanged. Baseline instrumentation must identify its controller and metric meaning without presenting Threshold-Only processing as Strategy inference. Dashboard display values do not replace common offline definitions and raw evidence.

## 17. Interpretation and Success Criteria

The experiment succeeds if it supports defensible answers about decision quality, unsafe automation, human workload, action suitability, reliability, latency, and resource cost under the same workload. A simpler baseline performing as well as or better than the proposed system is a valid outcome.

The evidence must distinguish:

- Incident handling from verified service recovery.
- Schema validity from semantic correctness.
- Simulated AUTO completion and human approval from successful remediation.
- Feedback timestamps from mean time to recovery (MTTR).
- Runtime detection counts from independently measured true/false positives.
- Wi-Fi observations from Ethernet results.
- Commodity-hardware feasibility from production readiness or universal scalability.

FAR/FER remain unavailable until independent labels support the definitions in Section 8. Do not infer superiority from a single run or attribute a complete-system difference exclusively to decomposition when governance, retrieval, and adaptation also differ.

## 18. Pre-Evaluation Freeze Checklist

Before formal comparative outputs are inspected, record and approve:

- [ ] Exact implementation/configuration revisions and adapter contracts for all conditions.
- [ ] Threshold rule table, precedence, action mappings, and invalid-input behavior.
- [ ] Single-Agent prompt/schema, generic validation boundary, failure fallback, and generation budget.
- [ ] Dataset checksum, full-set/subset decision, incident IDs, counts, order, and arrival schedule.
- [ ] Independent labels, annotation rubric, adjudication, ambiguity, and exclusion rules.
- [ ] Action-scoring definitions and all metric denominators and timestamp boundaries.
- [ ] Human-review procedure, feedback-accounting path, and completion criterion.
- [ ] Hardware/network configuration, model metadata, dependencies, and initial-state procedure.
- [ ] Repetition count, condition order, warm-up policy, cutoff/rerun rules, and uncertainty analysis.
- [ ] Evidence capture, consumer isolation, and reconciliation checks validated on a separate smoke set.

Any later protocol amendment must be versioned, justified, and disclosed together with whether results had already been observed. Do not silently revise comparison criteria after seeing outcomes.
