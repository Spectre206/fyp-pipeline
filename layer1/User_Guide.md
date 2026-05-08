# Layer 1 User Guide — stream-node (192.168.18.101)

This guide covers installing, configuring, and running the full Layer 1 stack on Node 1 from scratch. Complete `Phase_0_Infrastructure/User_Guide.md` before starting here — RabbitMQ, static IP, passwordless SSH, and NTP must all be verified first.

---

## 1. Prerequisites Checklist

Before running any Layer 1 component, confirm that all Phase 0 infrastructure items are in place: static IP `192.168.18.101` is set, hostname is `stream-node`, RabbitMQ is running with the `fypadmin` user, the `/etc/hosts` cluster mapping is present on all three nodes, and NTP is synchronised. This section will provide the exact verification commands for each.

---

## 2. Python Environment Setup

This section will cover creating a Python 3.10+ virtual environment on Node 1, activating it, and installing all dependencies from `requirements_node1.txt`. It will also document which packages correspond to which component (scikit-learn for ADM, pydantic for the validator, pika for RabbitMQ, river for PSI streaming).

---

## 3. Dataset Download and Placement

This section will describe how to download the three evaluation datasets — NAB (Numenta Anomaly Benchmark), Loghub HDFS, and KDD99 — and where to place them on Node 1 so the ADM training scripts can find them. Refer to `datasets/README.md` for download links. Expected directory paths and approximate download sizes will be documented here.

---

## 4. Running the Synthetic Event Generator (SEG)

This section will explain the two SEG operating modes: corpus generation mode (writes 1,950 events + `labels.csv` to disk) and live replay mode (publishes events to the pipeline at the speed configured in `seg/config/seg_config.json`). It will cover how to set the random seed, adjust replay speed, and verify that events are being produced with the correct distribution across categories.

---

## 5. Running the Pydantic Validator

This section will describe starting the validator, how it connects to the SEG output, and how to verify it is correctly classifying structural violations as `schema_drift` anomalies and routing them directly to `anomaly.detected`. Expected log lines for valid events and for each violation type (missing field, type mutation) will be shown.

---

## 6. Running the Feature Store

This section will cover starting the Feature Store, how to monitor the per-component rolling windows via the built-in status endpoint, and how to confirm that the baseline calibration window (first 100 events per component) has completed before PSI scoring becomes active. Memory usage monitoring commands will be included.

---

## 7. Training and Running the ADM Models

This section will cover the two-step process for each ML-based detector: (1) training on the relevant dataset and saving the model to `adm/models/`, and (2) running `adm_runner.py` which loads all five detectors and processes feature vectors in parallel. It will include expected training time on Node 1 hardware, how to verify each detector is publishing to `anomaly.detected`, and how to check RabbitMQ queue depth from the management UI at `192.168.18.101:15672`.

---

## 8. Verifying End-to-End Layer 1 Output

This section will describe how to confirm that the complete Layer 1 pipeline is working: events flowing from the SEG through the validator and feature store and out of the ADM into `anomaly.detected`. It will cover how to use the RabbitMQ management UI to inspect message payloads, how to check the Dead Letter Exchange for unroutable messages, and what a correctly formed `anomaly.detected` message should look like.

---

## 9. Running as Background Services

This section will document how to configure each Layer 1 component as a `systemd` service so it survives SSH disconnection and restarts automatically on reboot. Template `systemd` unit files and `journalctl` log commands will be included.

---

## 10. Troubleshooting

Common issues encountered during Layer 1 implementation will be documented here, including: RabbitMQ connection refused (firewall or service not running), Feature Store memory growing unboundedly (window size misconfiguration), ADM not detecting known anomalies (model not trained on correct dataset split), and Pydantic validation errors from unexpected SEG output fields.
