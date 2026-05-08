# Layer 1 — Real-Time Data Plane

> **Node:** stream-node — `192.168.18.101`
> **Hardware:** AMD Ryzen 5, 8GB RAM, Ubuntu 24.04 Desktop

---

## What This Layer Does

Layer 1 is the entry point of the entire pipeline. It generates or ingests raw events, enforces schema validity, computes derived feature vectors over per-component rolling windows, and runs five independent anomaly detection models in parallel. When any model flags an anomaly, Layer 1 publishes the full event — enriched with feature vectors and detection metadata — to the RabbitMQ Topic Exchange for Layer 2 to consume. Layer 1 has no runtime dependency on Nodes 2 or 3.

---

## Components

| Component | Directory | Role |
|:----------|:----------|:-----|
| Synthetic Event Generator | `seg/` | Generates the 1,950-event corpus and replays events into the live pipeline at configurable speed. Seeds are fixed for reproducibility. |
| Pydantic Validator | `validator/` | Schema enforcement gate. Structural failures (missing fields, type mutations) are immediately published as `schema_drift` anomalies — they bypass the Feature Store and go directly to `anomaly.detected`. |
| Feature Store | `feature_store/` | Stateful in-memory rolling windows per (node, component) pair. Computes Z-scores, moving averages, rate-of-change, spike counts, PSI scores, and silence duration for all five detectors. |
| Anomaly Detection Module | `adm/` | Five detectors running in parallel: Isolation Forest (CPU/memory), Z-Score (error rate), Moving Average (throughput), Rate-gate + Random Forest (auth flood), PSI Detector (schema drift). |
| RabbitMQ Producer | `rabbitmq/` | Publishes anomaly events to the `anomaly.detected` queue on the Topic Exchange. Handles connection retries and message persistence. |

---

## Data Flow

```
SEG  ──► Pydantic Validator
              │
              ├─ [structural violation] ───────────────────────► anomaly.detected
              │                                                   (schema_drift type)
              └─ [valid event] ──► Feature Store
                                        │
                                        └──► ADM Runner (5 detectors in parallel)
                                                  │
                                                  └─ [anomaly flagged] ──► RabbitMQ Producer
                                                                               │
                                                                               └──► anomaly.detected
```

---

## Implementation Order (Phase 1)

| Week | Component | Key Dependency |
|:-----|:----------|:---------------|
| 1 | SEG + Pydantic Validator | None — these are the foundation |
| 1 | Feature Store + Baseline Calibrator | Valid events from Validator |
| 2 | Isolation Forest — CPU/Memory Spike (Model 1) | Feature vectors + NAB dataset |
| 2 | Z-Score — Error Rate Surge (Model 2) | Feature vectors |
| 3 | Moving Average Deviation — Throughput Drop (Model 3) | Feature vectors |
| 4 | Rate-gate + Random Forest — Auth Flood (Model 4) | Feature vectors + KDD99 dataset |
| 5 | PSI Detector — Schema Drift (Model 5) | Feature vectors + PSI baseline from calibrator |

---

## RabbitMQ Queues Used

| Queue | Direction | Purpose |
|:------|:----------|:--------|
| `anomaly.detected` | Layer 1 → Layer 2 | All anomaly events published here |
| `dead.letters` | Internal | Unroutable messages — reviewed manually |

---

## Setup

See `User_Guide.md` in this directory for full Node 1 installation and startup instructions.
All Python dependencies are in `requirements_node1.txt`.
