# Layer 1 — Real-Time Data Plane

> **Node:** `stream-node` — Ubuntu 24.04 Desktop, AMD Ryzen 5, 8 GB RAM
> **Role:** Real-time event ingestion, validation, feature extraction, anomaly detection, and signal fusion

---

## What This Layer Does

Layer 1 is the entry point of the distributed self-healing pipeline. It generates a fixed, labeled synthetic corpus of 1,950 system-health events, enforces schema validity, computes derived feature vectors over per-component rolling windows, runs five independent anomaly detectors in parallel, and fuses their results into a single decision published to `anomaly.detected`. Layer 1 has no runtime dependency on Nodes 2 or 3.

---

## Architecture

```
SEG ──► Validator
  │
  ├─ [structural violation] ───────────────────────► anomaly.detected (100)
  │
  └─ [valid event] ──► Feature Store + ADM Runner
              │
              └──► detection.fanout
                      │
                      ├──► detect.cpu        ──┐
                      ├──► detect.error      ──┤
                      ├──► detect.throughput ──┼──► fusion.results
                      ├──► detect.auth       ──┤
                      └──► detect.schema     ──┘
                                                 │
                                                 ▼
                                          Fusion Engine
                                                 │
                                    ├─ [all normal] → suppress (995)
                                    └─ [≥1 anomaly] → anomaly.detected (532 fused)
```

Final `anomaly.detected` queue count: **100 bypass + 532 fused = 632 messages**.

### Schema Drift: Two Distinct Paths

**Structural violations** (missing fields, type mutations) are caught by the Pydantic Validator and routed directly to `anomaly.detected` via the SchemaDriftRouter. These events cannot be safely featurised and bypass the Feature Store and Fusion Engine entirely.

**Value/distribution drift** (`value_shift`) is structurally valid, passes Pydantic validation, and flows through the full pipeline: Validator → Feature Store → detection.fanout → Schema Drift Detector (PSI + shift marker) → Fusion Engine.

---

## Components

| Component | Directory | Role |
|:----------|:----------|:-----|
| **Synthetic Event Generator** | `seg/` | Generates the 1,950-event corpus and replays events into the live pipeline at configurable speed. Seeds are fixed for reproducibility. |
| **RabbitMQ Topology** | `rabbitmq/` | One-time setup script that declares all exchanges, queues, and bindings. |
| **Pydantic Validator** | `validator/` | Schema enforcement gate. Structural failures are immediately published as `schema_drift` anomalies via the SchemaDriftRouter, bypassing the Feature Store and Fusion Engine. |
| **Feature Store** | `feature_store/` | Stateful in-process library. Maintains per-`(node, component)` rolling windows and per-`(component,)` calibration baselines. Computes Z-scores, moving averages, rate-of-change, spike counts, PSI scores, silence duration, and auth failure rate. |
| **ADM Runner + Detectors** | `adm/` | ADM Runner fans out enriched events to `detection.fanout`. Five standalone detectors consume from their own queues and publish results to `fusion.results`. |
| **Fusion Engine** | `fusion_engine/` | Correlates detector results by `event_id` within a 5-second window, suppresses normal events, and publishes fused anomalies. |

---

## Detection Architecture

Five anomaly detectors run as independent RabbitMQ consumers. Each receives every enriched event via the `detection.fanout` fanout exchange, evaluates it against its specific detection logic, and publishes a result (detected or not) to `fusion.results`.

| # | Detector | Algorithm | Queue | Target Class | TP | FP | Precision | Recall |
|---|----------|-----------|-------|--------------|----|----|-----------|--------|
| 1 | CPU/Memory Spike | Z-Score (>2.0) + raw threshold (>70%) | `detect.cpu` | cpu_memory_spike (200) | 188 | 9 | 95.4% | 94.0% |
| 2 | Error Rate Surge | Z-Score (>2.0) + step-change (>10%) | `detect.error` | error_rate_surge (200) | 148 | 2 | 98.7% | 74.0% |
| 3 | Throughput Drop | Moving Avg deviation + raw threshold (<40) + silent crash | `detect.throughput` | throughput_drop (200) | 141 | 0 | 100% | 70.5% |
| 4 | Auth Failure Flood | Rate-gate (>20/min) + Random Forest (KDD99) | `detect.auth` | auth_failure_flood (200) | 124 | 0 | 100% | 62.0% |
| 5 | Schema Drift | Shift marker (primary) + PSI (confidence boost) | `detect.schema` | schema_drift value_shift (50) | 31 | 0 | 100% | 62.0% |

*TP = true positives on target class. FP = false positives across all event types. Recall is on the target anomaly type only.*

---

## Feature Store

The Feature Store is a stateful in-process library called by the ADM Runner. It maintains:

- **Rolling windows** keyed by `(node, component)` — no cross-node mixing.
- **Calibration baselines** keyed by `(component,)` — pools events across nodes for faster calibration.
- **Calibration gate** — the first 20 events per component are used to build a baseline. During this period, events are consumed but not fanned out to detectors (`calibration_n=20`).
- **Baseline persistence** — frozen baselines are saved as JSON files and restored on restart.

**Features computed per event:** 10 per-metric features (rolling_mean, rolling_std, rolling_min, rolling_max, z_score, rate_of_change, spike_count, short_ma, long_ma, psi_score) plus 2 global features (silence_duration_s, auth_failures_per_min).

---

## Fusion Engine (v1.7)

| Parameter | Value |
|-----------|-------|
| Primary correlation window | **5 seconds** |
| Late-arrival recovery window | **0.75 seconds** |
| Effective maximum wait | **5.75 seconds** |
| Minimum confidence to publish | 0.3 |
| Fast path | Enabled (CRITICAL + weight ≥ 0.80) |

- **Correlation:** Groups detector results by `event_id`. When all 5 detectors report, fusion occurs immediately. Otherwise, waits up to 5 seconds, then allows a 0.75-second recovery window.
- **Suppression:** Events where all detectors returned normal, or single-detector anomalies below the confidence threshold, are suppressed (not published).
- **Fast path:** A CRITICAL result from a high-weight model marks the event as fast-path priority but **does not finalize early**. The event remains eligible for full correlation.
- **Compound detection:** ≥2 unique detectors flagging the same event produces a "compound" incident.

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

## Observability

Layer 1 components expose Prometheus metrics on the following ports (scraped by Prometheus on `gateway-node`):

| Component | Port |
|-----------|------|
| Validator | 8002 |
| Fusion Engine | 8003 |
| Error Rate Detector | 8004 |
| Throughput Drop Detector | 8005 |
| Auth Flood Detector | 8006 |
| CPU Spike Detector | 8007 |
| Schema Drift Detector | 8008 |

ADM Runner and Feature Store do not expose their own Prometheus endpoints.

Prometheus/Grafana are part of the observability infrastructure on Node 3 and are **not** part of the anomaly-processing data path.

---

## Timestamp Propagation

| Field | Meaning |
|-------|---------|
| `timestamp` | Original synthetic event occurrence time (from corpus generation) |
| `ingestion_time` | Real UTC time when the event entered `raw.events` during replay |
| `fused_at` | Time when Fusion Engine produced the final fused decision |

`node` and `affected_component` are propagated from the original event through all detectors and into the fused event.

---

## Evaluation Corpus

**1,950 synthetic events** generated with seed 42 for full reproducibility.

| Category | Count |
|----------|-------|
| NORMAL | 1,000 |
| cpu_memory_spike | 200 |
| error_rate_surge | 200 |
| throughput_drop | 200 |
| auth_failure_flood | 200 |
| schema_drift — missing_field | 50 |
| schema_drift — type_mutation | 50 |
| schema_drift — value_shift | 50 |

Ground truth labels are stored in `evaluation/labels.csv` and are **not** exposed to the detection pipeline (stripped by the SEG before publishing).

---

## Known Limitations

1. **Isolation Forest distribution mismatch** — A NAB-trained Isolation Forest flagged ~98% of synthetic events due to domain mismatch between NAB system metrics and the synthetic corpus. The IF model is saved but unused; detection relies on Z-scores.
2. **Hardcoded detector thresholds** — All five detectors use module-level Python constants. No config-driven threshold management exists yet.
3. **PSI as standalone detector** — PSI scores are elevated across most events due to synthetic corpus variance. PSI serves as a confidence booster only, not a primary detection signal.
4. **`silence_duration_s` wall-clock bug** — The silence duration feature computes elapsed time using `datetime.now()` rather than corpus timestamps, producing inflated values during corpus replay.
5. **Hardcoded file paths** — Detector JSONL output files and the auth RF model path use absolute paths.

---

## Setup

See **[User Guide](User_Guide.md)** for full installation, configuration, and step-by-step run instructions. All Python dependencies are in `requirements_node1.txt`.