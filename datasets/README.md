# Datasets — Download Instructions

The three datasets used for training the ADM models and generating the evaluation
corpus are not included in this repository due to file size. Download them to
this directory before running any Layer 1 component.

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
