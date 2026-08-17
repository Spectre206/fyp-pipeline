# Layer 1 — Real-Time Data Plane

> **Node:** stream-node — `192.168.18.101`
> **Hardware:** AMD Ryzen 5 7340U, 8 GB RAM, 256 GB NVMe, Ubuntu 24.04 Desktop

---

## What This Layer Does

Layer 1 is the entry point of the entire pipeline. It generates a fixed, labeled
synthetic corpus of 1 950 system‑health events, enforces schema validity, computes
derived feature vectors over per‑component rolling windows, runs five independent
anomaly detectors in parallel, and fuses their results into a single decision
published to `anomaly.detected`. Layer 1 has no runtime dependency on Nodes 2 or 3.

---

## Components

| Component | Directory | Role |
|:----------|:----------|:-----|
| **Synthetic Event Generator** | `seg/` | Generates the 1 950‑event corpus and replays events into the live pipeline at configurable speed. Seeds are fixed for reproducibility. |
| **RabbitMQ Topology** | `rabbitmq/` | One‑time setup script that declares all exchanges, queues, and bindings. |
| **Pydantic Validator** | `validator/` | Schema enforcement gate. Structural failures (missing fields, type mutations) are immediately published as `schema_drift` anomalies — they bypass the Feature Store and ADM Runner and go directly to `anomaly.detected`. |
| **Feature Store** | `feature_store/` | Stateful in‑process library. Maintains per‑`(node, component)` rolling windows and per‑`component` calibration baselines. Computes Z‑scores, moving averages, rate‑of‑change, spike counts, PSI scores, silence duration, and auth failure rate for all five detectors. |
| **ADM Runner + Detectors** | `adm/` | ADM Runner fans out enriched events to `detection.fanout`. Five standalone detectors consume from their own queues and publish to `fusion.results`. |
| **Fusion Engine** | `fusion_engine/` | Correlates detector results by `event_id`, suppresses normal events, and publishes fused anomalies to `anomaly.detected`. Exposes Prometheus metrics on port 8003. |

---

## Data Flow

```
SEG ──► Validator
           │
           ├─ [structural violation] ──────────────────────────► anomaly.detected (100)
           │
           └─ [valid event] ──► Feature Store + ADM Runner
                                      │
                                      └──► detection.fanout
                                              │
                                              ├──► detect.cpu       ──┐
                                              ├──► detect.error     ──┤
                                              ├──► detect.throughput──┼──► fusion.results
                                              ├──► detect.auth      ──┤
                                              └──► detect.schema    ──┘
                                                      │
                                                      ▼
                                              Fusion Engine
                                                      │
                                                      ├─ [all normal] → suppress (995)
                                                      └─ [≥1 anomaly] → anomaly.detected (532 fused)
```

Final `anomaly.detected` queue count: **100 bypass + 532 fused = 632 messages**.

![Layer 1 Data Flow](docs/layer1_data_flow.png)

---

## RabbitMQ Topology

| Exchange | Type | Purpose |
|:---------|:-----|:--------|
| `fyp.events` | Topic | Shared bus — raw events, validated events, fusion results, anomaly decisions, and Layer 2/3 agent communication |
| `detection.fanout` | Fanout | Broadcasts each enriched event to all five detector queues simultaneously |
| `fyp.dlx` | Direct | Dead Letter Exchange — failed deliveries routed to `dead.letters` |

| Queue | Bound To | Routing Key | Consumer |
|:------|:---------|:------------|:---------|
| `raw.events` | `fyp.events` | `event.raw` | Validator |
| `validated.event` | `fyp.events` | `event.valid` | ADM Runner |
| `detect.cpu` | `detection.fanout` | `""` (fanout) | CPU/Memory Spike Detector |
| `detect.error` | `detection.fanout` | `""` (fanout) | Error Rate Surge Detector |
| `detect.throughput` | `detection.fanout` | `""` (fanout) | Throughput Drop Detector |
| `detect.auth` | `detection.fanout` | `""` (fanout) | Auth Failure Flood Detector |
| `detect.schema` | `detection.fanout` | `""` (fanout) | Schema Drift Detector |
| `fusion.results` | `fyp.events` | `fusion.result` | Fusion Engine |
| `anomaly.detected` | `fyp.events` | `anomaly.#` | Layer 2 Triage Agent |
| `dead.letters` | `fyp.dlx` | `dead` | Manual inspection |

---

## Detectors Summary

| # | Detector | Algorithm | Queue | Target Class | TP | FP | Precision | Recall |
|---|----------|-----------|-------|--------------|----|----|-----------|--------|
| 1 | CPU/Memory Spike | Z‑Score + raw threshold | `detect.cpu` | `cpu_memory_spike` (200) | 188 | 9 | 95.4% | 94.0% |
| 2 | Error Rate Surge | Z‑Score + step‑change | `detect.error` | `error_rate_surge` (200) | 148 | 2 | 98.7% | 74.0% |
| 3 | Throughput Drop | Moving Avg + raw threshold | `detect.throughput` | `throughput_drop` (200) | 141 | 0 | 100% | 70.5% |
| 4 | Auth Failure Flood | Rate‑Gate + Random Forest | `detect.auth` | `auth_failure_flood` (200) | 124 | 0 | 100% | 62.0% |
| 5 | Schema Drift | PSI + Shift Marker | `detect.schema` | `schema_drift` value_shift (50) | 31 | 0 | 100% | 62.0% |

*TP = true positives on target class. FP = false positives. Recall is on the target anomaly type only; false negatives include other anomaly types correctly passed by each detector.*

---

## Fusion Engine Summary (v1.7)

| Metric | Value |
|--------|-------|
| Total processed | 1 527 |
| Published | 532 |
| Suppressed | 995 |
| Compound | 43 |
| Fast Path published | 78 |
| Errors | 0 |
| Missing `ingestion_time` | 0 |
| Queue backlog | 0 |

- **Primary correlation window:** 5 seconds
- **Late‑arrival recovery window:** 0.75 seconds
- **Effective maximum wait:** 5.75 seconds
- **Fast path:** triggers on CRITICAL + high‑weight model but does **not** finalize early. The event remains eligible for full correlation.

---

## Timestamp Propagation

Layer 1 now propagates two timestamps end‑to‑end:

| Field | Meaning |
|-------|---------|
| `timestamp` | Original synthetic event occurrence time (from corpus generation) |
| `ingestion_time` | Real UTC time when the event entered `raw.events` during replay |
| `fused_at` | Time when Fusion Engine produced the final fused decision |

`ingestion_time` is added in SEG replay, preserved by Validator and Feature Store, included in every detector result, and carried into the fused event. It is used by Layer 2 for accurate MTTA/MTTR calculation.

---

## Prometheus Metrics

Only the **Fusion Engine** exports Prometheus metrics (port **8003**):

| Metric | Description |
|:-------|:------------|
| `fyp_fusion_published_total` | Total fused anomalies published to `anomaly.detected` |
| `fyp_fusion_suppressed_total` | Events where all detectors returned normal (suppressed) |
| `fyp_fusion_compound_total` | Compound incidents (≥2 detectors flagged the same event) |
| `fyp_fusion_fast_path_total` | Events fast‑pathed (CRITICAL with high‑weight model) |
| `fyp_fusion_fast_path_triggered_total` | Events where a qualifying CRITICAL result triggered fast path |
| `fyp_fusion_latency_seconds` | Fusion decision computation latency histogram |
| `fyp_fusion_correlation_wait_seconds` | Time an event waited in correlation before finalization |
| `fyp_fusion_detectors_received` | Number of unique detectors received at finalization |
| `fyp_fusion_late_recovery_total` | Events finalized during the late‑arrival recovery window |
| `fyp_fusion_errors_total` | Fusion processing errors |

Prometheus on `gateway-node` (port 9090) scrapes `stream-node:8003`.  
Grafana dashboard "Agent Pipeline & Fusion Engine" visualises these metrics.

---

## Setup

See **[User Guide](User_Guide.md)** for full installation, configuration, and
step‑by‑step run instructions. All Python dependencies are in
`requirements_node1.txt`.

For a complete cold‑start run from scratch, follow the command sequence in
**Section 12** of the User Guide.

This version now reflects the final Fusion Engine v1.7, timestamp propagation, and actual cold‑start results.