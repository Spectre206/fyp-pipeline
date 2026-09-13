# Layer 3 — Execution, Human Oversight & Observability Layer

**Project:** Distributed Multi-Agent Coordination for Self-Healing Data Pipelines
**Primary node:** Node 3, **gateway-node** — Ubuntu 24.04 Desktop, Intel Core i5, 8 GB RAM
**Authoritative experiment:** **wifi_cold_20260913_041045**

This log is the detailed technical reference for the frozen Layer 3
implementation. It is based on the active source, the versioned Grafana
dashboard, and the authoritative Wi-Fi experiment. The root
[Full_Rerun.md](../../Full_Rerun.md) remains the complete execution and
reproduction runbook.

## 1. Authority boundary and overall architecture

Layer 3 turns a route already selected by Layer 2 Policy into either controlled
automatic handling or persistent human review. It does not make an independent
risk or automation-eligibility decision.

- **Strategy** proposes structured actions.
- **Policy** deterministically authorises **AUTO** or **HITL**.
- **Auto Executor** handles only authorised AUTO messages.
- **HITL** persists and presents Policy escalations for a human decision.
- **Learning** consumes the resulting feedback.
- **Prometheus and Grafana** are observational, never part of a decision path.

~~~mermaid
flowchart LR
    classDef policy fill:#243b53,color:#fff,stroke:#0f172a,stroke-width:2px
    classDef auto fill:#14532d,color:#fff,stroke:#166534,stroke-width:2px
    classDef hitl fill:#7c2d12,color:#fff,stroke:#c2410c,stroke-width:2px
    classDef queue fill:#334155,color:#fff,stroke:#475569
    classDef data fill:#312e81,color:#fff,stroke:#4f46e5
    classDef learn fill:#075985,color:#fff,stroke:#0284c7

    STR[Layer 2 Strategy<br/>structured proposal] --> POL[Layer 2 Policy<br/>deterministic route]
    POL -->|AUTO authorised| AQ[(auto.execute)]
    POL -->|human review required| HQ[(hitl.queue)]
    AQ --> AE[Auto Executor]
    HQ --> HC[HITL consumer]
    HC --> HI[(HitlIncident<br/>persistent state)]
    HI --> HR[Human reviewer]
    AE --> OF[(outcome.feedback)]
    HR --> OF
    OF --> LA[Layer 2 Learning]
    class POL policy
    class AQ,HQ,OF queue
    class AE auto
    class HC,HR hitl
    class HI data
    class LA learn
~~~

## 2. Component map and broker contracts

| Component | Principal implementation | Responsibility |
|---|---|---|
| RabbitMQ helper | **rabbitmq/connection.py** | Layer 3 connections and persistent JSON publishing through the **fyp.events** exchange. |
| Auto Executor | **auto_executor/executor.py** | Consumes **auto.execute**, performs controlled simulated handling, logs a decision, and emits feedback. |
| SQLite decision logger | **sqlite_logger/logger.py** | Creates and appends decision records in **sqlite_logger/decisions.db** using WAL mode. |
| Django HITL application | **dashboard/hitl/** | Persists human-review work, serves the review views, and exports HITL metrics. |
| HITL consumer | **dashboard/hitl/management/commands/consume_hitl.py** | Moves **hitl.queue** messages into persistent **HitlIncident** records. |
| Grafana dashboard | **grafana/FYP_Hybrid_Agentic_Framework_Observability_v3_Node_Naming.json** | Versioned final research-observability dashboard. |

| Queue / exchange | Producer | Consumer | Purpose |
|---|---|---|---|
| **auto.execute** | Layer 2 Policy | Auto Executor | Policy-authorised automatic route. |
| **hitl.queue** | Layer 2 Policy | HITL management command | Policy escalation awaiting persistence and review. |
| **outcome.feedback** | Auto Executor or HITL views | Layer 2 Learning | Execution outcome or human-decision feedback. |
| **fyp.events** | Layer 3 publisher helper | RabbitMQ routing | Exchange used to publish persistent JSON. |

The shared connection helper reads host, port, credentials, and virtual host
from environment variables. The source defaults to **stream-node**, port
**5672**, and virtual host **fyp**. It publishes a persistent JSON message and
closes the publish connection. Those defaults describe the implementation, not a
replacement for environment setup in the root runbook.

## 3. AUTO execution path

**Implementation:** **auto_executor/executor.py**, class **AutoExecutor**
**Input:** Policy-authorised message from **auto.execute**
**Output:** an **AUTO_EXECUTE** SQLite decision and an **outcome.feedback** event
**Metrics endpoint:** port **8014**

The executor initialises the decision database and a Prometheus HTTP server. It
consumes with prefetch one, extracts Policy/Strategy actions from the routed
payload, runs the implementation's controlled simulated action handling, writes
the audit record, publishes feedback, and then acknowledges the broker message.

~~~mermaid
flowchart LR
    classDef policy fill:#243b53,color:#fff,stroke:#0f172a
    classDef queue fill:#334155,color:#fff,stroke:#475569
    classDef auto fill:#14532d,color:#fff,stroke:#166534
    classDef store fill:#312e81,color:#fff,stroke:#4f46e5
    classDef feedback fill:#075985,color:#fff,stroke:#0284c7

    P[Layer 2 Policy<br/>AUTO route] --> Q[(auto.execute)]
    Q --> E[Auto Executor]
    E --> X[Controlled simulated<br/>action handling]
    X --> D[(SQLite decisions<br/>AUTO_EXECUTE)]
    D --> F[Build execution outcome]
    F --> O[(outcome.feedback)]
    O --> L[Layer 2 Learning]
    E -. metrics :8014 .-> M[Prometheus]
    class P policy
    class Q,O queue
    class E,X auto
    class D store
    class F,L feedback
~~~

### 3.1 Internal execution and error behaviour

A non-empty action list follows the success branch, which is a controlled
0.5-second simulated action. An empty action list follows the explicit failure
branch with zero resolution time. Both branches record execution duration and
outcome before the SQLite write and feedback publication.

~~~mermaid
flowchart TD
    classDef process fill:#14532d,color:#fff,stroke:#166534
    classDef decision fill:#7c2d12,color:#fff,stroke:#c2410c
    classDef durable fill:#312e81,color:#fff,stroke:#4f46e5
    classDef broker fill:#334155,color:#fff,stroke:#475569
    classDef error fill:#991b1b,color:#fff,stroke:#dc2626

    A[Broker delivers AUTO message<br/>prefetch = 1] --> B[Increment AUTO attempts]
    B --> C[Extract Policy payload<br/>and recommended actions]
    C --> D{Action list non-empty?}
    D -->|yes| E[Simulate controlled execution<br/>0.5 seconds]
    D -->|no| F[Set failure outcome<br/>resolution time = 0]
    E --> G[Set success outcome]
    F --> H[Observe execution duration]
    G --> H
    H --> I[Write AUTO_EXECUTE<br/>decision row]
    I --> J[Publish outcome.feedback]
    J --> K[Increment feedback metric]
    K --> L[ACK auto.execute]
    C -. callback exception .-> N[NACK without requeue]
    I -. callback exception .-> N
    J -. callback exception .-> N
    class A,J,L broker
    class B,C,E,F,G,H,K process
    class D decision
    class I durable
    class N error
~~~

The final experiment's 170 AUTO outcomes were all observed on the success
branch. This does not make success universal: the empty-action failure branch
exists in source. A callback exception causes **NACK without requeue**. The
executor does not run arbitrary LLM code and does not decide whether an action
is safe to automate.

### 3.2 AUTO instrumentation

| Metric | Type / labels | Meaning |
|---|---|---|
| **fyp_auto_executor_attempts_total** | Counter | Automatic remediation attempts in the current process. |
| **fyp_auto_executor_outcomes_total{outcome}** | Counter | **SUCCESS** or **FAILURE** execution-path outcomes. |
| **fyp_auto_executor_execution_latency_seconds** | Histogram | Controlled action-handling duration, not a service-restoration measure. |
| **fyp_outcome_feedback_emitted_total** | Counter | Successfully emitted AUTO feedback messages. |

## 4. HITL ingestion and persistence

**Implementation:** **dashboard/hitl/management/commands/consume_hitl.py** and
**dashboard/hitl/models.py**
**Input:** Policy escalation on **hitl.queue**
**Persistent entity:** **HitlIncident**
**Initial workflow state:** **PENDING**

The management command consumes with prefetch one and calls
**persist_hitl_incident(data)**. It uses **get_or_create(event_id, ...)**. An
existing event is therefore a retained duplicate, not a reopened incident. A
successful create or duplicate handling is acknowledged; a persistence
exception is negatively acknowledged with **requeue=True**.

~~~mermaid
flowchart LR
    classDef broker fill:#334155,color:#fff,stroke:#475569
    classDef process fill:#7c2d12,color:#fff,stroke:#c2410c
    classDef data fill:#312e81,color:#fff,stroke:#4f46e5
    classDef error fill:#991b1b,color:#fff,stroke:#dc2626

    Q[(hitl.queue)] --> C[consume_hitl<br/>prefetch = 1]
    C --> P[persist_hitl_incident]
    P --> D{event_id exists?}
    D -->|no| I[(Create HitlIncident<br/>status PENDING)]
    D -->|yes| X[Keep existing incident<br/>do not reopen]
    I --> A[ACK broker message]
    X --> A
    P -. persistence error .-> R[NACK with requeue]
    class Q,A broker
    class C,P process
    class D decision
    class I,X data
    class R error
~~~

### 4.1 Persistent entities and time semantics

| Entity | Storage role | Relevant fields / semantics |
|---|---|---|
| **HitlIncident** | Django-managed human workflow | Unique **event_id**, **payload_json**, **status**, **arrived_at**, and nullable **decided_at**. Statuses are **PENDING**, **APPROVED**, **REJECTED**, and **MODIFIED**. |
| **Decision** | Unmanaged Django mapping to the shared **decisions** table | Audit record created by Auto Executor and HITL decision views. |
| **decisions table** | Direct SQLite writer target | Includes event/context, decision type/timestamp, action JSON, notes, and Auto outcome; WAL enabled. |

Human-decision latency means:

~~~text
persisted and available for review (arrived_at)
                  →
terminal human state stored (decided_at)
~~~

It measures the review-decision interval, never end-service restoration.

## 5. HITL human lifecycle

**Views/templates:** **dashboard/hitl/views.py** and
**dashboard/hitl/templates/hitl/**
**Queue page:** only persisted **PENDING** incidents
**Detail page:** supplied Triage, Strategy, and Policy reasoning data

A reviewer selects one terminal action for a PENDING incident. The source uses
an atomic conditional update from PENDING to the selected terminal state. A
stale second submission cannot create another authoritative state transition,
decision timestamp, or decision metric increment.

~~~mermaid
stateDiagram-v2
    [*] --> PENDING: consume_hitl persists event_id
    PENDING --> APPROVED: approve succeeds
    PENDING --> REJECTED: reject succeeds
    PENDING --> MODIFIED: modify succeeds
    APPROVED --> [*]
    REJECTED --> [*]
    MODIFIED --> [*]
    note right of PENDING
      Queue and detail views expose
      persisted PENDING rows only.
    end note
~~~

### 5.1 Approve, reject, and modify

None of the human paths calls the Auto Executor. Each is a decision/audit and
feedback path with its own ordered side effects.

~~~mermaid
flowchart TD
    classDef human fill:#7c2d12,color:#fff,stroke:#c2410c
    classDef data fill:#312e81,color:#fff,stroke:#4f46e5
    classDef queue fill:#334155,color:#fff,stroke:#475569
    classDef metric fill:#075985,color:#fff,stroke:#0284c7
    classDef warn fill:#991b1b,color:#fff,stroke:#dc2626

    P[(Persisted PENDING incident)] --> H{Reviewer action}
    H -->|APPROVE| A1[Write APPROVE decision<br/>original actions]
    H -->|REJECT| R1[Write REJECT decision<br/>empty actions]
    H -->|MODIFY| M1[Collect up to three<br/>non-empty edited action strings]
    M1 --> M2[Write MODIFY decision<br/>final edited actions]
    A1 --> A2[Publish HITL_APPROVED]
    R1 --> R2[Publish HITL_REJECTED]
    A2 --> A3[Set APPROVED + decided_at]
    R2 --> R3[Set REJECTED + decided_at]
    M2 --> M3[Set MODIFIED + decided_at]
    M3 --> M4[Best-effort publish<br/>HITL_MODIFIED]
    A3 --> AM[Update decision metrics]
    R3 --> RM[Update decision metrics]
    M3 --> MM[Update decision metrics]
    M4 -. broker failure is logged .-> W[MODIFIED state remains persisted]
    class P,A1,R1,M1,M2,A3,R3,M3 data
    class H human
    class A2,R2,M4 queue
    class AM,RM,MM metric
    class W warn
~~~

| Path | Stored action data | State and feedback behaviour |
|---|---|---|
| Approve | Strategy actions become final actions. | Writes **APPROVE**, publishes **HITL_APPROVED**, then conditionally persists **APPROVED** and metrics. It does not execute the action list. |
| Reject | Final action list is empty. | Writes **REJECT**, publishes **HITL_REJECTED**, then conditionally persists **REJECTED** and metrics. Rejections still enter feedback. |
| Modify | Up to three non-empty edited action strings and optional notes. | Writes **MODIFY**, conditionally persists **MODIFIED** and metrics, then best-effort publishes **HITL_MODIFIED**. Modified actions are recorded/forwarded, not automatically executed. |

The modify form does not impose a Layer 3 action allowlist or quantity
validation beyond its three editable action fields. The earlier deterministic
Policy route remains the authorisation boundary.

## 6. Feedback emission

Feedback contains the event identifier, outcome type, actual action list,
operator notes, resolution time, and full Policy result. AUTO feedback uses the
measured execution duration and the note **auto-executed**. HITL feedback uses
the human outcome and a zero resolution-time field.

~~~mermaid
flowchart LR
    classDef auto fill:#14532d,color:#fff,stroke:#166534
    classDef human fill:#7c2d12,color:#fff,stroke:#c2410c
    classDef event fill:#334155,color:#fff,stroke:#475569
    classDef learn fill:#075985,color:#fff,stroke:#0284c7

    AE[Auto Executor] -->|AUTO_EXECUTE_SUCCESS<br/>or AUTO_EXECUTE_FAILURE| B[Build feedback payload]
    HD[HITL decision view] -->|HITL_APPROVED<br/>HITL_REJECTED<br/>HITL_MODIFIED| B
    B --> E[(fyp.events exchange)]
    E --> Q[(outcome.feedback)]
    Q --> L[Layer 2 Learning]
    class AE auto
    class HD human
    class B,E,Q event
    class L learn
~~~

For AUTO, feedback publication precedes message acknowledgement. For approve and
reject, feedback publication precedes terminal-state persistence. For modify,
the terminal state is persisted first and feedback publication is best-effort:
a publish error is logged without reverting MODIFIED. These asymmetries describe
the frozen source behaviour exactly.

## 7. Persisted pending work versus RabbitMQ backlog

**HITL Pending** and **HITL Queue Backlog** are different operational states and
must not be interpreted interchangeably.

~~~mermaid
flowchart TB
    classDef broker fill:#334155,color:#fff,stroke:#475569
    classDef data fill:#312e81,color:#fff,stroke:#4f46e5
    classDef metric fill:#075985,color:#fff,stroke:#0284c7

    subgraph RMQ["RabbitMQ delivery state"]
        Q[(hitl.queue)] --> U[Messages not yet consumed]
        U --> QM[rabbitmq_queue_messages_ready<br/>queue = hitl.queue]
        QM --> QP[Grafana: HITL Queue Backlog]
    end
    subgraph DB["Django persistent workflow state"]
        I[(HitlIncident rows)] --> P[status = PENDING]
        P --> PG[fyp_hitl_pending_incidents<br/>database-backed scrape gauge]
        PG --> PP[Grafana: HITL Pending]
    end
    Q -->|consumer persists then ACKs| I
    class Q,U,QM broker
    class I,P data
    class PG,QP,PP metric
~~~

| Measure | Query / source | Correct interpretation |
|---|---|---|
| **HITL Queue Backlog** | **sum(rabbitmq_queue_messages_ready{queue="hitl.queue"})** | Messages still waiting for the Django consumer. |
| **HITL Pending** | **sum(fyp_hitl_pending_incidents)** | Persisted incidents whose workflow state is PENDING. |

The pending gauge counts **HitlIncident.objects.filter(status="PENDING")** at
scrape time. It is database-backed rather than process-local, so it remains
meaningful across a Django restart. Zero queue depth does not prove zero
unresolved human work.

## 8. HITL metrics

**Implementation:** **dashboard/hitl/metrics.py** and
**dashboard/hitl/views.py**
**Endpoint:** Django **/metrics** using the HITL-specific registry

| Metric | Type | Semantics |
|---|---|---|
| **fyp_hitl_pending_incidents** | Database-backed Gauge | Persisted PENDING incidents at scrape time. |
| **fyp_hitl_approved_total** | Counter | Successfully persisted APPROVED transitions in the current process. |
| **fyp_hitl_rejected_total** | Counter | Successfully persisted REJECTED transitions in the current process. |
| **fyp_hitl_modified_total** | Counter | Successfully persisted MODIFIED transitions in the current process. |
| **fyp_human_decision_latency_seconds** | Histogram | Non-negative aware **decided_at - arrived_at** duration. Buckets: 5, 10, 30, 60, 120, 300, 600, 900, 1800 seconds. |

The code intentionally does not invent observations when a timestamp is missing,
naive, or produces a negative duration. Counters are process-local; pending
state is queried from the database on demand.

## 9. Decision database and audit flow

**Database:** **layer3/sqlite_logger/decisions.db**
**Writer:** **sqlite_logger/logger.py**
**Django model:** unmanaged **Decision** mapped to **decisions**

AUTO and human decisions share one SQLite audit table, while **HitlIncident**
owns the separate human workflow state.

~~~mermaid
flowchart LR
    classDef auto fill:#14532d,color:#fff,stroke:#166534
    classDef human fill:#7c2d12,color:#fff,stroke:#c2410c
    classDef db fill:#312e81,color:#fff,stroke:#4f46e5
    classDef metric fill:#075985,color:#fff,stroke:#0284c7

    AE[Auto Executor] -->|AUTO_EXECUTE| DL[sqlite_logger.write_decision]
    HV[HITL views] -->|APPROVE / REJECT / MODIFY| DL
    DL --> DT[(decisions table<br/>SQLite WAL)]
    HC[HITL consumer] --> HI[(HitlIncident table)]
    HI -->|PENDING to terminal state<br/>arrived_at and decided_at| HM[HITL metrics]
    DT --> DM[Decision audit / accounting]
    class AE auto
    class HV,HC human
    class DL,DT,HI db
    class HM,DM metric
~~~

The decision audit stores incident identity/context, Strategy risk/confidence,
routing reason, decision type/timestamp, queue time, original/final action JSON,
operator notes, AUTO outcome, and creation time. Final database accounting was:

| Decision type | Count |
|---|---:|
| **APPROVE** | 325 |
| **AUTO_EXECUTE** | 170 |
| **MODIFY** | 1 |
| **REJECT** | 143 |
| **Total** | **639** |

The audit vocabulary intentionally differs from human workflow status:
**APPROVE** and **REJECT** in the decisions table correspond to **APPROVED** and
**REJECTED** in HitlIncident state.

## 10. Prometheus scrape architecture

Layer 3 centralises the final experiment's observability stack on
**gateway-node**. Prometheus scrapes exporters; Grafana queries Prometheus.

~~~mermaid
flowchart LR
    classDef node fill:#1e3a5f,color:#fff,stroke:#2563eb
    classDef app fill:#14532d,color:#fff,stroke:#166534
    classDef infra fill:#334155,color:#fff,stroke:#475569
    classDef obs fill:#7c2d12,color:#fff,stroke:#c2410c

    subgraph SN["stream-node"]
        N1[Node Exporter :9100]
        L1[Layer 1 exporters<br/>approximately :8002 to :8008]
    end
    subgraph AB["ai-brain-node"]
        N2[Node Exporter :9100]
        L2[Layer 2<br/>Triage :8010<br/>Strategy :8011<br/>Policy :8012<br/>Learning :8013]
    end
    subgraph GW["gateway-node"]
        N3[Node Exporter :9100]
        H[HITL Django :8000]
        A[Auto Executor :8014]
        R[RabbitMQ metrics :15692]
        P[Prometheus :9090]
        G[Grafana]
    end
    N1 --> P
    L1 --> P
    N2 --> P
    L2 --> P
    N3 --> P
    H --> P
    A --> P
    R --> P
    P --> G
    class N1,N2,N3 node
    class L1,L2,H,A app
    class R infra
    class P,G obs
~~~

The port map records the audited experimental deployment. No Prometheus
configuration file is versioned under **layer3/**, so the repository cannot
establish that every scrape target definition is itself under version control.

For the final experiment, target health was **19 UP / 0 DOWN / 19 total**. This
is experiment-specific, not an architectural constant.

## 11. Grafana observability architecture

**Versioned source:**
**layer3/grafana/FYP_Hybrid_Agentic_Framework_Observability_v3_Node_Naming.json**
**Dashboard title:** **Hybrid Agentic Framework — Final Research Observability**

~~~mermaid
flowchart TB
    classDef source fill:#1e3a5f,color:#fff,stroke:#2563eb
    classDef prom fill:#7c2d12,color:#fff,stroke:#c2410c
    classDef graf fill:#14532d,color:#fff,stroke:#166534
    classDef reader fill:#312e81,color:#fff,stroke:#4f46e5

    S[Three-node exporters<br/>RabbitMQ metrics<br/>Django and Auto metrics] --> P[Prometheus<br/>scrape and time series]
    P --> G[Grafana dashboard]
    G --> O[SYSTEM OVERVIEW]
    G --> L1[LAYER 1<br/>data plane]
    G --> L2[LAYER 2<br/>control plane]
    G --> L3[LAYER 3<br/>execution and HITL]
    G --> I[Infrastructure health]
    G --> H[Hardware/node resources]
    O --> R[Researcher / operator reads state]
    L1 --> R
    L2 --> R
    L3 --> R
    I --> R
    H --> R
    class S source
    class P prom
    class G,O,L1,L2,L3,I,H graf
    class R reader
~~~

Layer 3 panels and their correct meanings:

| Panel | Meaning |
|---|---|
| AUTO Attempts | Current-process automatic remediation attempts. |
| AUTO Outcomes | Success/failure execution-path counts; not service-restoration proof. |
| AUTO Latency | Histogram percentile of controlled Auto Executor action duration. |
| Feedback Emitted | Successfully emitted automatic outcome.feedback messages. |
| HITL Queue Backlog | Unconsumed RabbitMQ hitl.queue messages only. |
| HITL Decisions | Persisted approved, rejected, and modified human decisions. |
| Human Decision Latency | Persisted availability to recorded human decision. |
| Feedback Loop | Feedback processed by Learning across Policy, AUTO/HITL, feedback, and Learning. |

Grafana is observability only. It has no role in routing, approval, action
execution, or decision persistence.

## 12. Full AUTO/HITL feedback loop

~~~mermaid
flowchart TB
    classDef policy fill:#243b53,color:#fff,stroke:#0f172a
    classDef auto fill:#14532d,color:#fff,stroke:#166534
    classDef human fill:#7c2d12,color:#fff,stroke:#c2410c
    classDef queue fill:#334155,color:#fff,stroke:#475569
    classDef feedback fill:#075985,color:#fff,stroke:#0284c7

    P[Layer 2 Policy] -->|AUTO| AQ[(auto.execute)]
    P -->|HITL| HQ[(hitl.queue)]
    AQ --> AE[Auto Executor]
    AE --> AO[Execution outcome<br/>and AUTO_EXECUTE audit]
    HQ --> HC[HITL consumer]
    HC --> PI[Persisted PENDING incident]
    PI --> HD{Human decision}
    HD --> AP[APPROVE]
    HD --> RJ[REJECT]
    HD --> MD[MODIFY]
    AP --> HO[Human outcome<br/>and decision audit]
    RJ --> HO
    MD --> HO
    AO --> OF[(outcome.feedback)]
    HO --> OF
    OF --> LA[Layer 2 Learning]
    LA --> LE[Feedback processing<br/>and final learning records]
    class P policy
    class AQ,HQ,OF queue
    class AE,AO auto
    class HC,PI,HD,AP,RJ,MD,HO human
    class LA,LE feedback
~~~

## 13. Final cross-layer accounting

The final cold Wi-Fi experiment reconciles each hand-off from Layer 1 to
Learning. These independent counts make a missing branch visible.

~~~mermaid
flowchart LR
    classDef input fill:#1e3a5f,color:#fff,stroke:#2563eb
    classDef control fill:#243b53,color:#fff,stroke:#0f172a
    classDef auto fill:#14532d,color:#fff,stroke:#166534
    classDef hitl fill:#7c2d12,color:#fff,stroke:#c2410c
    classDef feedback fill:#075985,color:#fff,stroke:#0284c7

    L1[Layer 1<br/>539 fused + 100 structural<br/>= 639] --> L2[Layer 2<br/>639 Triage = Strategy = Policy]
    L2 --> A[170 AUTO]
    L2 --> H[469 HITL]
    A --> AO[170 execution outcomes]
    H --> HA[325 approved]
    H --> HR[143 rejected]
    H --> HM[1 modified]
    AO --> F[639 feedback events]
    HA --> F
    HR --> F
    HM --> F
    F --> L[Learning<br/>639 processed<br/>639 final ChromaDB documents]
    class L1 input
    class L2 control
    class A,AO auto
    class H,HA,HR,HM hitl
    class F,L feedback
~~~

| Accounting boundary | Calculation | Result |
|---|---|---:|
| Layer 1 population | 539 fused + 100 structural schema violations | 639 |
| Layer 2 control path | Triage = Strategy = Policy | 639 each |
| Policy routes | 170 AUTO + 469 HITL | 639 |
| Human decisions | 325 approved + 143 rejected + 1 modified | 469 |
| Layer 3 feedback | 170 AUTO + 469 HITL | 639 |
| Learning result | Feedback processed / final ChromaDB documents | 639 / 639 |

### 13.1 Final Layer 3 outcomes

| Measure | Final observed value |
|---|---:|
| AUTO attempts / outcomes | 170 / 170 |
| AUTO feedback emitted | 170 |
| AUTO latency p50 / p95 | approximately 625 ms / 738 ms |
| HITL routed | 469 |
| HITL approved / rejected / modified | 325 / 143 / 1 |
| Persisted HITL pending at completion | 0 |
| Human-decision latency p50 / p95 | approximately 20 s / 55.5 s |
| HITL feedback / total feedback | 469 / 639 |
| Prometheus health | 19 UP / 0 DOWN / 19 total |
| Dead-letter queue at completion | 0 |

The displayed latency families are distinct:

| Latency measure | Scope | Final result |
|---|---|---|
| AUTO execution latency | Controlled Auto Executor action duration | dashboard p50 approximately 625 ms; p95 approximately 738 ms |
| Human-decision latency | HitlIncident arrived_at to decided_at | dashboard p50 approximately 20 s; p95 approximately 55.5 s |
| Feedback-completion latency | Layer 2 Policy decision to outcome.feedback receipt | offline analyzer: mean 37.611 s, median 23.107 s, p95 126.545 s, p99 282.361 s, max 367.597 s |

Grafana percentile values are histogram-bucket approximations. The separate
Layer 2 offline feedback-completion measure must not be substituted for the
Layer 3 human-decision metric.

## 14. Experiment interpretation and limitations

The evidence supports these bounded conclusions:

- All 170 AUTO-routed incidents completed the implemented Auto Executor path.
- All 469 HITL incidents received a terminal human decision.
- No persisted HITL incident was pending at experiment completion.
- AUTO and HITL feedback reconciled to 639, matching the Policy population and
  Learning feedback/document count.
- Rejected incidents were represented in feedback rather than dropped.
- Relevant queues drained to **0 ready** and **0 unacknowledged**; the
  **dead.letters** queue was 0.
- Temporary queueing was observed, with the dominant bottleneck upstream in
  Layer 2 Strategy rather than Layer 3.

The experiment does not establish verified end-service restoration,
production-scale persistence, universal reviewer throughput, or universal
scalability. It uses a synthetic workload, one controlled reviewer workflow,
centralised observability on gateway-node, SQLite persistence, and controlled
simulated AUTO handling. Service recovery duration was not measured.

Qualitative dashboard observations showed ai-brain-node carrying the dominant
Strategy workload (roughly 50% CPU), observed memory around the 60–80% range,
temporary network spikes, and a brief temperature approach to approximately
80°C. These are graph-derived observations, not precision measurements.

## 15. Documentation consolidation

The former **layer3/User_Guide.md** contained still-useful deployment context,
component/queue relationships, verification concepts, and high-level flow.
Those concepts are consolidated into this log and **layer3/README.md**.
Commands and operational sequences are intentionally not duplicated because
the root runbook owns reproduction.

No **layer3/docs/diagrams/** directory existed during reconstruction. There
were no standalone diagram files to migrate or delete; the authoritative
architecture diagrams are now inline Mermaid diagrams in this log.
