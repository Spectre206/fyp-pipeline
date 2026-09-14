# Datasets — Historical Download Instructions

**Project:** Distributed Multi-Agent Coordination for Self-Healing Data Pipelines: A Human-in-the-Loop Approach on Commodity Hardware

> **Historical/offline dataset plan.** The assignments below describe the earlier
> ML-based ADM design. They are not prerequisites for the active statistical/
> deterministic Layer 1 runtime or its synthetic 1,950-event corpus. Historical
> training scripts remain under `layer1/evaluation/historical/`.
> Use the [current Layer 1 README](../layer1/README.md) and
> [Full_Rerun.md](../Full_Rerun.md) for current corpus generation and replay.

The external datasets are not bundled. The historical download locations and
model assignments below are retained for reference.

---

## NAB — Numenta Anomaly Benchmark

**Used by:** Isolation Forest (Model 1), Z-Score (Model 2), Moving Average (Model 3)
**Download:** https://github.com/numenta/NAB
**Specific files needed:**
  - `data/realAWSCloudwatch/ec2_cpu_utilization_5f5533.csv`
  - `data/realAWSCloudwatch/ec2_cpu_utilization_ac20cd.csv`
  - `data/realAWSCloudwatch/ec2_cpu_utilization_fe7f93.csv`
  - `data/realKnownCause/machine_temperature_system_failure.csv`
  - `data/realKnownCause/ambient_temperature_system_failure.csv`
  - `data/realTwitter/Twitter_volume_AMZN.csv`

Place the cloned NAB repo in `datasets/NAB/`.

---

## Loghub — HDFS Log Dataset

**Used by:** SEG (schema drift events), PSI Detector (Model 5)
**Download:** https://github.com/logpai/loghub
**Specific file needed:** HDFS/HDFS_1/HDFS.log (2GB — download separately)
**Direct link:** https://zenodo.org/record/3227177

Place the HDFS log file at `datasets/Loghub/HDFS/HDFS.log`.

---

## KDD99 — Network Intrusion Detection Dataset

**Used by:** Rate-gate + Random Forest (Model 4 — auth flood detection)
**Download:** http://kdd.ics.uci.edu/databases/kddcup99/kddcup99.html
**Specific file needed:** kddcup.data_10_percent.gz (~2MB compressed)

Place the extracted CSV at `datasets/KDD99/kddcup.data_10_percent.csv`.

---

## Expected Directory Structure After Download

```
datasets/
├── NAB/
│   ├── data/realAWSCloudwatch/
│   └── data/realKnownCause/
├── Loghub/
│   └── HDFS/
│       └── HDFS.log
├── KDD99/
│   └── kddcup.data_10_percent.csv
└── README.md          ← you are here
```
