# System Design and Methodology

**Project:** Distributed Multi-Agent Coordination for Self-Healing Data Pipelines: A Human-in-the-Loop Approach on Commodity Hardware
**Authoritative implementation:** commit **377250945c253b9c9da233d84391d1458d181fc9**
**Authoritative experiment:** **wifi_cold_20260913_041045**

This document is the research-oriented companion to the root
[README](../README.md). It records system-design rationale, methodology,
experimental protocol, metric semantics, and validity boundaries for later
thesis, paper, and defence work. The operational procedure is maintained
separately in [Full_Rerun.md](../Full_Rerun.md).

Throughout this document:

- **Implemented fact** means supported by frozen source/configuration.
- **Experimental result** means observed in the authoritative Wi-Fi run or its
  offline analyzer.
- **Interpretation** means a bounded conclusion drawn from those facts and
  results.

## 1. Research context

Self-healing data pipelines require more than detecting unusual measurements.
A practical response loop must connect detection, context gathering,
recommendation, safety enforcement, execution or human review, outcome capture,
and adaptation. These tasks have different latency, safety, and reliability
requirements.

This project investigates a distributed architecture in which heterogeneous
components coordinate these responsibilities on three commodity machines. The
design uses bounded local AI for remediation planning but keeps detection,
authorisation, execution control, human workflow, learning updates, and
observability deterministic or explicitly controlled.

## 2. Problem definition

The engineering problem is to coordinate incident handling across a streaming
pipeline without granting generative output direct execution authority. The
research prototype must:

- detect multiple kinds of abnormal or structurally invalid input;
- reduce duplicate/noisy detector output before expensive reasoning;
- provide relevant history to planning;
- constrain a local LLM response to a validated action contract;
- deterministically decide whether automatic handling is permitted;
- preserve a human escalation path;
- retain every outcome for adaptive feedback; and
- make the distributed process measurable.

No formal numbered research questions are asserted here. The system instead
supports evaluation questions about structured-output reliability, routing
safety, handling/feedback completeness, and the latency cost of local
commodity-hardware inference.

## 3. Research objectives

The implemented objectives are to:

1. design a distributed detection, control, execution, and oversight
   architecture;
2. combine statistical, deterministic, retrieval-assisted, and LLM-assisted
   components without treating them as equivalent agents;
3. enforce a deterministic safety boundary around policy-bounded automation;
4. evaluate controlled AUTO handling and human-in-the-loop fallback;
5. measure structured-output validity, routing, latency, and feedback
   completeness; and
6. preserve a repeatable cold-state experimental procedure.

## 4. Design principles

The [Literature Review](Literature_Review.md#8-literature-derived-design-requirements)
derives the detection, authorization, oversight, messaging, adaptation, and
measurement requirements behind this decomposition.

| Principle | Design response |
|---|---|
| Separation of concerns | Layer 1 detects, Layer 2 reasons/authorises, and Layer 3 handles/observes. |
| Asynchronous coordination | RabbitMQ decouples producers and consumers. |
| Heterogeneous agents | Only Strategy is LLM-backed; other components use deterministic/statistical logic. |
| Deterministic safety boundary | Strategy validates its output contract; Policy checks that status and its own eligibility rules before routing. |
| Local inference | Ollama runs qwen3:1.7b on CPU-only commodity hardware. |
| Human oversight | Escalated incidents are persisted before review and terminal decision. |
| Feedback-driven adaptation | Learning records outcome feedback in ChromaDB and updates an EMA threshold. |
| Observability | Prometheus/Grafana expose process, queue, HITL, and infrastructure state. |
| Reproducibility | Frozen source, cold-state reset, run identity, and preserved artifacts support reruns. |

## 5. Physical system architecture

**Implemented fact.** The deployment separates data-plane, control-plane, and
execution/observability responsibilities across three Ubuntu 24.04 nodes.

~~~mermaid
flowchart LR
    classDef node fill:#1e3a5f,color:#fff,stroke:#2563eb,stroke-width:2px
    classDef service fill:#14532d,color:#fff,stroke:#166534
    classDef broker fill:#334155,color:#fff,stroke:#475569
    classDef obs fill:#7c2d12,color:#fff,stroke:#c2410c

    subgraph N1["Node 1 — stream-node<br/>AMD Ryzen 5, 8 GB, Ubuntu Desktop"]
        L1["Layer 1 — Real-Time Statistical Data Plane"]
        RMQ[(RabbitMQ)]
        NE1[Node Exporter :9100]
        L1 <--> RMQ
    end
    subgraph N2["Node 2 — ai-brain-node<br/>AMD Ryzen 5, 8 GB, Ubuntu Server"]
        L2["Layer 2 — AI Control Plane"]
        OLL[Ollama CPU inference]
        CHR[(ChromaDB)]
        NE2[Node Exporter :9100]
        L2 <-->|"Strategy only"| OLL
        L2 <--> CHR
    end
    subgraph N3["Node 3 — gateway-node<br/>Intel Core i5, 8 GB, Ubuntu Desktop"]
        L3["Layer 3 — Execution, Human Oversight & Observability Layer"]
        PR[Prometheus :9090]
        GR[Grafana]
        NE3[Node Exporter :9100]
        L3 -. "metrics" .-> PR
        PR -. "query results" .-> GR
    end
    L2 <--> RMQ
    L3 <--> RMQ
    NE1 -. "scraped metrics" .-> PR
    NE2 -. "scraped metrics" .-> PR
    NE3 -. "scraped metrics" .-> PR
    class L1,L2,L3 service
    class RMQ broker
    class PR,GR obs
    class N1,N2,N3 node
~~~

The hardware is deliberately modest. This makes local inference and queueing
costs measurable, but it also limits external generalisation to larger or
accelerated deployments.

## 6. Logical architecture

**Implemented fact.** The logical architecture contains three named layers:

1. **Layer 1 — Real-Time Statistical Data Plane**
2. **Layer 2 — AI Control Plane**
3. **Layer 3 — Execution, Human Oversight & Observability Layer**

~~~mermaid
flowchart LR
    classDef data fill:#0c4a6e,color:#fff,stroke:#0369a1
    classDef control fill:#7c2d12,color:#fff,stroke:#c2410c
    classDef exec fill:#14532d,color:#fff,stroke:#166534
    classDef queue fill:#334155,color:#fff,stroke:#475569
    classDef store fill:#312e81,color:#fff,stroke:#4f46e5

    subgraph L1["Layer 1 — Real-Time Statistical Data Plane"]
        SEG[SEG] --> VAL[Validator]
        VAL -->|valid| FS[Feature Store and ADM]
        FS --> DET[Five detectors]
        DET --> FUS[Fusion]
        VAL -->|structural bypass| AN[(anomaly.detected)]
        FUS --> AN
    end
    subgraph L2["Layer 2 — AI Control Plane"]
        TRI[Triage] -->|"RabbitMQ: triage.result"| STR[Strategy]
        STR -->|"RabbitMQ: strategy.result"| POL[Policy]
        LEA[Learning]
        MEM[(ChromaDB)]
        TRI <--> MEM
        LEA --> MEM
        LEA -->|"persisted EMA threshold"| POL
    end
    subgraph L3["Layer 3 — Execution, Human Oversight & Observability Layer"]
        AUT[Auto Executor]
        HIT[Django HITL]
        AUD[(SQLite audit and<br/>persistent HITL state)]
        AUT --> AUD
        HIT --> AUD
    end
    AN --> TRI
    POL -->|auto.execute| AUT
    POL -->|hitl.queue| HIT
    AUT -->|outcome.feedback| LEA
    HIT -->|outcome.feedback| LEA
    class SEG,VAL,FS,DET,FUS data
    class TRI,STR,POL,LEA control
    class AUT,HIT exec
    class AN queue
    class MEM,AUD store
~~~

Inter-agent arrows denote RabbitMQ handoffs; ChromaDB and threshold arrows
denote local retrieval/persistence. These diagrams summarize responsibilities,
not direct inter-agent function calls.

The authority relation is one-way: **Strategy proposes; Policy authorises or
escalates; Layer 3 performs the already-selected branch.**

## 7. Event-driven communication architecture

**Implemented fact.** RabbitMQ on stream-node provides the asynchronous
backbone. The topic exchange **fyp.events** carries most cross-stage events;
the fanout exchange **detection.fanout** distributes eligible enriched events to
the five detector queues without routing-key selection.

| Message route | Source | Destination | Methodological role |
|---|---|---|---|
| event.raw → raw.events | SEG | Validator | Corpus ingress |
| event.valid → validated.event | Validator | ADM Runner | Validated data-plane processing |
| detection.fanout | ADM Runner | Five detector queues | Parallel detector observation |
| fusion.result → fusion.results | Detectors | Fusion | Correlation input |
| anomaly.# → anomaly.detected | Fusion / Schema Drift Router | Triage | Incident boundary into Layer 2 |
| triage.result | Triage | Strategy | Normalised context and retrieval |
| strategy.result | Strategy | Policy | Proposed structured remediation |
| auto.execute | Policy | Auto Executor | Authorised automatic path |
| hitl.queue | Policy | Django HITL consumer | Persisted human-review path |
| outcome.feedback | Layer 3 | Learning | Outcome/adaptation input |

Asynchrony prevents Layer 1 from blocking on Strategy inference. It also means
end-to-end decision latency can include queue wait rather than only local
component processing.

## 8. Layer 1 methodology

### 8.1 Event generation, validation, and structural bypass

**Implemented fact.** The Synthetic Event Generator (SEG) provides a
deterministic seeded workload definition. Pydantic validation accepts
structurally valid events. Missing-field and type-mutation schema cases produce
structural violations and are routed through the Schema Drift Router directly
to **anomaly.detected**. They do not enter Feature Store or Fusion.

Value-shift schema cases remain structurally valid. They therefore continue
through Feature Store, detector fan-out, and Fusion like other valid events.

### 8.2 Feature Store and ADM Runner

The Feature Store maintains rolling component-level context and cold-state
calibration. Calibration uses **20** accepted events per component. The first **19** are
withheld; the twentieth completes calibration and can be fanned out to detectors. This deliberate stateful gating
explains the authoritative count change from 1,850 valid events to 1,527
fusion-eligible events; it is not data loss.

The ADM Runner enriches eligible events and publishes them to the fanout
exchange. Active detection is statistical/deterministic Python logic, not the
historical supervised/unsupervised ML experiment material.

### 8.3 Detector family and Fusion

Five active detectors cover CPU/memory spikes, error-rate surges, throughput
drops, authentication floods, and schema drift. Fusion correlates their results
with a **3.0-second** primary window and **0.75-second** recovery window. It
suppresses individual or duplicate output where appropriate, marks compound
incidents, and publishes fused incidents for Layer 2.

Historical Random Forest and Isolation Forest scripts remain in
**layer1/evaluation/historical/** with an intentionally separate requirements
file. They are not part of the active runtime path.

## 9. Layer 2 methodology

### 9.1 Triage and retrieval

**Implemented fact.** Triage is deterministic protocol mapping plus ChromaDB
retrieval. It normalises detector/fusion context, selects a response protocol,
and supplies formatted historical context to Strategy. It is not an LLM agent.

### 9.2 Strategy structured generation

Strategy uses local **qwen3:1.7b** via Ollama. It produces a required
seven-field object:

~~~text
anomaly_type, severity, affected_component, recommended_actions,
confidence, risk_tier, reasoning
~~~

The response contract requires exactly three distinct actions from an enumerated
allowlist, a confidence between 0 and 1, and no extra fields. For each input,
the output schema binds severity to the incoming Triage severity and binds
risk tier as follows:

| Triage severity | Required risk tier |
|---|---|
| LOW | LOW |
| MEDIUM | LOW |
| HIGH | HIGH |
| CRITICAL | HIGH |

The Python validator remains authoritative. On a failed deterministic
validation, Strategy may make one complete regeneration; the implementation
therefore allows at most **two generation attempts** per incident. It does not
run an unbounded repair loop.

### 9.3 Policy safety and routing

Policy is deterministic and fail closed. It routes to HITL for timeout,
parse failure, schema failure, invalid risk tier/confidence, unsupported
actions, retained low-confidence Fusion payloads, high risk, or confidence below
the persisted threshold. Only a schema-valid LOW-risk response meeting the
threshold and action constraints routes to AUTO.

~~~mermaid
flowchart LR
    classDef proposal fill:#7c2d12,color:#fff,stroke:#c2410c
    classDef safety fill:#243b53,color:#fff,stroke:#0f172a
    classDef auto fill:#14532d,color:#fff,stroke:#166534
    classDef hitl fill:#991b1b,color:#fff,stroke:#dc2626

    S[Strategy proposal] --> V[Deterministic Policy authorization checks]
    V -->|timeout, parse/schema/action failure| H[HITL]
    V -->|HIGH risk or low confidence| H
    V -->|LOW risk, valid actions,<br/>confidence >= threshold| A[AUTO]
    class S proposal
    class V safety
    class A auto
    class H hitl
~~~

### 9.4 Learning and adaptation

Learning is deterministic. It consumes feedback, stores outcome metadata in the
ChromaDB **incident_history** collection, and updates the Policy confidence
threshold with an EMA under bounded configuration values. It has no active LLM
generation role.

## 10. Layer 3 methodology

### 10.1 Controlled AUTO handling

The Auto Executor consumes only **auto.execute** messages already authorised by
Policy. A non-empty action set takes the controlled simulated action path; an
empty set has an explicit failure branch. It writes an **AUTO_EXECUTE** audit
record, emits **outcome.feedback**, and exposes metrics on port 8014.

An AUTO success is an execution-path outcome. It does not verify that a real
service was restored.

### 10.2 Persistent human workflow

The HITL consumer transfers **hitl.queue** events into persistent
**HitlIncident** rows. Status moves from PENDING to APPROVED, REJECTED, or
MODIFIED through a conditional state transition. The dashboard displays
persisted PENDING items and the supplied reasoning data.

Approve records a decision and feedback but does not invoke Auto Executor.
Reject records an empty action set and still emits feedback. Modify records up
to three non-empty edited action strings, persists MODIFIED, and performs
best-effort feedback publication.

### 10.3 Pending workload and queue backlog

A broker message awaiting consumption and a persisted unresolved incident are
different state spaces:

| Measure | Meaning |
|---|---|
| HITL Queue Backlog | RabbitMQ **hitl.queue** messages not yet consumed. |
| HITL Pending | Database-backed **fyp_hitl_pending_incidents** count of persisted PENDING rows. |

The human-decision metric measures **arrived_at → decided_at** for a persisted
incident. It is a review-decision interval, not a recovery interval.

### 10.4 Feedback and observability

Both AUTO and HITL paths emit **outcome.feedback** for Learning. Prometheus
scrapes exporter/application metrics and Grafana reads Prometheus; Grafana does
not direct decisions or execution.

## 11. Data and workload design

**Implemented fact.** The final corpus contains 1,950 synthetic events:

| Class | Count |
|---|---:|
| NORMAL | 1,000 |
| CPU/memory spike | 200 |
| Error-rate surge | 200 |
| Throughput drop | 200 |
| Authentication-failure flood | 200 |
| Schema drift | 150 |
| **Total** | **1,950** |

The schema-drift class consists of 50 missing-field, 50 type-mutation, and 50
value-shift events. A synthetic workload enables repeatable timing, class
composition, and controlled cold-state testing; it does not represent
production traffic exhaustively.

## 12. Ground truth

**Implemented fact.** SEG generates evaluation labels in **labels.csv**. Its
default output directory is `evaluation/`; the runbook uses a run-specific
output directory and copies labels for offline analysis. These labels are not
exposed to runtime components. The runtime receives event content
and produces detector, Strategy, Policy, and handling outputs independently.

This separation prevents labels from becoming hidden runtime hints. It also
limits certain downstream metrics: the available labels do not provide
authoritative safe-to-auto or expected-route truth for every routed incident.

## 13. Experimental protocol

**Methodological fact.** The authoritative Wi-Fi experiment used a cold-memory
start:

1. clear Layer 1 calibration baselines and disposable result state;
2. reset experiment queues without changing broker topology;
3. clear Layer 2 Chroma persistence;
4. reset the EMA threshold to its cold baseline;
5. create a fresh evaluation run identity;
6. clear persisted HITL workflow/decision state;
7. start fresh processes from the frozen commit;
8. replay the fixed corpus at the documented speed;
9. complete the human decisions for every persisted HITL item; and
10. run the offline analyzer against the recorded artifacts.

The conceptual protocol is documented here; exact safe commands are in
[Full_Rerun.md](../Full_Rerun.md).

## 14. Controlled conditions and planned comparison

For **wifi_cold_20260913_041045**, the intended controlled conditions were:

- fixed frozen implementation;
- fixed three-node commodity hardware;
- fixed corpus-generation configuration and replay procedure;
- cold Layer 1, Chroma, queue, EMA, and HITL state; and
- Wi-Fi as the recorded network medium.

An Ethernet comparison is future work unless and until its own completed
experiment evidence is recorded. It is not presented as a completed result.

## 15. Evaluation metrics

### 15.1 Layer 1

| Measure | Definition |
|---|---|
| Validator received / valid / structural violations | Ingress and structural-validation accounting. |
| Detector evaluations | Fusion-eligible events processed by each active detector. |
| Runtime detections | Operational detector outputs; not true positives. |
| Fusion published / suppressed | Incident publication and suppression counts. |
| Compound / Fast Path / late recovery | Fusion behaviours under current configuration. |
| Layer 1 timing | Exported processing telemetry, interpreted separately from Layer 2 queues. |

### 15.2 Layer 2

| Measure | Definition |
|---|---|
| Strategy schema-validity rate | Schema-valid non-timeout Strategy responses divided by non-timeout responses. |
| Timeout count/rate | Strategy model timeouts recorded by the agent. |
| AUTO/HITL distribution | Deterministic Policy routes. |
| Risk-tier accuracy | Analyzer comparison where the relevant risk truth is available. |
| Control-plane processing latency | Triage + Strategy + Policy excluding inter-agent queue wait. |
| End-to-end decision latency | Triage timestamp to Policy decision, including queue wait. |
| Feedback completion latency | Policy decision to feedback receipt. |
| Learning processing latency | Learning-agent handling time. |

### 15.3 Layer 3

| Measure | Definition |
|---|---|
| AUTO attempts/outcomes | Automatic execution-path attempt and outcome counters. |
| AUTO execution latency | Controlled Auto Executor action duration. |
| HITL decisions | Persisted APPROVED, REJECTED, and MODIFIED transitions. |
| Human-decision latency | Persisted incident arrival to recorded human decision. |
| Pending incidents | Database-backed PENDING count at scrape time. |
| Feedback | Emitted/completed outcome feedback across both branches. |

### 15.4 Infrastructure

Target health, RabbitMQ ready/unacknowledged depth, dead-letter queue state,
NTP/clock observations, and node resource telemetry are infrastructure
observations. The final target count is experiment-specific rather than an
architectural constant.

## 16. Metrics not available

The following must not be fabricated from the current data:

- **FAR** is not computable from available ground truth.
- **FER** is not computable from available ground truth.
- A verified service-recovery duration was not measured.
- Feedback completion, human decision, or AUTO duration must not be relabelled
  as verified service recovery.
- Runtime detector output counts must not be labelled true positives.

## 17. Final experimental results

### 17.1 Layer 1

| Final result | Value |
|---|---:|
| Validator received / valid / structural violations | 1,950 / 1,850 / 100 |
| Each detector evaluations | 1,527 |
| CPU / error / auth / schema / throughput detections | 197 / 150 / 124 / 31 / 141 |
| Fusion published / suppressed | 539 / 988 |
| Compound / Fast Path / late recovery | 43 / 83 / 0 |

### 17.2 Layer 2

| Final result | Value |
|---|---:|
| Strategy incidents; valid/invalid JSON | 639; 639 / 0 |
| Schema-valid / schema-invalid | 493 / 146 |
| Strategy schema-validity rate | 77.15% |
| Timeouts | 0 |
| AUTO / HITL | 170 / 469 |
| HIGH_RISK / LOW_CONFIDENCE / LOW_RISK_HIGH_CONFIDENCE / SCHEMA_INVALID | 258 / 65 / 170 / 146 |
| Risk-tier accuracy | 513 / 630 = 81.43% |
| Final EMA threshold / updates | 0.7291 / 639 |
| Chroma documents | 639 |

### 17.3 Layer 3 and infrastructure

| Final result | Value |
|---|---:|
| AUTO attempts / outcomes / feedback emitted | 170 / 170 / 170 |
| HITL approved / rejected / modified | 325 / 143 / 1 |
| HITL pending at completion | 0 |
| Total feedback / Learning updates | 639 / 639 |
| Prometheus target health | 19 UP / 0 DOWN |
| Relevant queues at completion | 0 ready / 0 unacknowledged |
| Dead-letter queue | 0 |

## 18. Cross-layer accounting

~~~mermaid
flowchart LR
    classDef l1 fill:#0c4a6e,color:#fff,stroke:#0369a1
    classDef l2 fill:#7c2d12,color:#fff,stroke:#c2410c
    classDef l3 fill:#14532d,color:#fff,stroke:#166534
    classDef feedback fill:#312e81,color:#fff,stroke:#4f46e5

    A[539 fused] --> C[639 Layer 2 incidents]
    B[100 structural bypass] --> C
    C --> D[170 AUTO]
    C --> E[469 HITL]
    D --> F[170 AUTO feedback]
    E --> G[325 approved<br/>143 rejected<br/>1 modified]
    G --> H[469 HITL feedback]
    F --> I[639 feedback]
    H --> I
    I --> J[639 Learning updates<br/>639 Chroma documents]
    class A,B l1
    class C l2
    class D,E,G l3
    class F,H,I,J feedback
~~~

~~~text
539 + 100 = 639
170 + 469 = 639
325 + 143 + 1 = 469
639 feedback = 639 Learning updates = 639 Chroma documents
~~~

**Interpretation.** The matching counts provide evidence of complete
experiment-path accounting across the detected/bypassed incident population.
They do not alone prove remediation correctness or restored services.

## 19. Latency analysis

| Measure | Mean | Median | p95 | Maximum |
|---|---:|---:|---:|---:|
| Strategy processing | 13.0546 s | 11.142 s | 19.409 s | 22.084 s |
| Control-plane processing | 13.0606 s | 11.17 s | 19.41 s | 22.085 s |
| End-to-end decision | 68.4 min | 68.5 min | 131.7 min | 139.2 min |
| Feedback completion | 37.611 s | 23.107 s | 126.545 s | 367.597 s |
| Learning processing | 58.97 ms | 46.09 ms | 77.73 ms | — |

**Experimental result.** The offline Layer 2 analyzer provides the authoritative
aggregate end-to-end values. It is preferred over a visually clipped dashboard
histogram panel.

**Interpretation.** Approximately 639 serial Strategy operations at about 13.05
seconds each are consistent with the observed approximately 139-minute maximum
end-to-end latency. The dominant cause is Strategy queue accumulation during
CPU-only local inference, not evidence of lost events.

Layer 3 metrics are separate: dashboard AUTO p50/p95 was approximately
625/738 ms; human-decision p50/p95 was approximately 20/55.5 s. They measure
different process segments and do not replace feedback-completion latency.

## 20. Safety analysis

The safety model is layered rather than dependent on prompt compliance alone:

1. Strategy receives an explicit structured schema and severity/risk binding.
2. The Python validator independently checks required fields, types, confidence,
   exact action count, distinctness, allowlist membership, and risk mapping.
3. One bounded regeneration may follow validation failure.
4. Policy rejects timeout, parse, schema, action, confidence, and risk failures.
5. Policy sends high-risk and insufficient-confidence proposals to HITL.
6. Auto Executor consumes only the authorised AUTO queue.
7. HITL provides a terminal human decision and audit trail.

The final run demonstrates the practical value of this boundary: all 146
schema-invalid Strategy outputs were routed to HITL rather than AUTO.

## 21. Learning and adaptation method

Learning treats feedback as event history rather than self-authorising control.
It upserts outcome metadata into ChromaDB for subsequent Triage retrieval and
updates a persisted EMA confidence threshold within configured hard bounds. The
final threshold of 0.7291 after 639 updates is an experiment outcome, not a
fixed default or a proof that the learned threshold is optimal.

## 22. Observability method

Prometheus collects Layer 1, Layer 2, Layer 3, RabbitMQ, and node telemetry;
Grafana displays it across system overview, three layer sections,
infrastructure health, and hardware/resource sections. Metrics distinguish
process-local counters from durable/database-backed state where implemented.
For example, **fyp_hitl_pending_incidents** is authoritative persisted PENDING
work, while RabbitMQ queue-ready depth measures undelivered messages.

## 23. Reproducibility

Reproducibility rests on:

- the frozen commit and branch recorded above;
- the cold-state method;
- fixed corpus configuration and generated-label separation;
- a new run identifier and preserved experiment directory;
- source-aligned behavior across all three nodes; and
- the complete operational runbook in [Full_Rerun.md](../Full_Rerun.md).

The existing screenshots under **docs/experiment_results/wifi/** are preserved
evidence for the authoritative Wi-Fi run.

## 24. Threats to validity

### Internal validity

The workload, one controlled reviewer workflow, local configuration, and
cold-state reset influence measured results. Queue state and process restarts
must be controlled for comparable reruns.

### External validity

Three commodity nodes, CPU-only local inference, laboratory networking, and
synthetic traffic do not establish behavior under production traffic, different
hardware, or larger deployment topologies.

### Construct validity

Feedback completion is not service restoration. Schema validity is not
remediation correctness. Runtime detector counts are not true positives. Human
decision completion is not a repaired-service verification.

### Measurement validity

Prometheus histogram percentiles are bucket approximations. Dashboard panels
can be visually clipped; the offline analyzer is used for authoritative final
end-to-end aggregates. Available ground truth does not support FAR or FER.

## 25. Limitations

The final Wi-Fi result is one controlled experiment. Key limitations include
synthetic workload composition; CPU-only Strategy throughput; a 77.15%
schema-validity rate; 146 schema-invalid proposals; controlled human-review
timing; unavailable FAR/FER; no verified service-restoration measurement; and
experimental-scale SQLite/HITL persistence. Centralised observability on
gateway-node is also an infrastructure dependency.

These limitations bound the conclusions but do not erase the observed complete
feedback/accounting result.

## 26. Future work

Reasonable future work includes:

- a controlled Ethernet-versus-Wi-Fi comparison;
- faster or parallel local Strategy workers;
- improved constrained structured generation;
- broader, more realistic workloads;
- authoritative safe-to-auto and expected-route labels;
- direct verification of service restoration;
- richer deterministic Policy rules; and
- replicated/higher-availability persistence.

These are future directions, not completed capabilities.
