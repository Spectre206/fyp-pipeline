# Threshold-Only baseline

The main design/reference document is [THRESHOLD_BASELINE_SYSTEM.md](THRESHOLD_BASELINE_SYSTEM.md). The [frozen experiment design](../BASELINE_EXPERIMENT_DESIGN.md) governs comparisons; [common utilities](../common/README.md) cover capture, replay, neutral HITL presentation, and analysis.

## Prerequisites

Run from the repository root with Python 3.10+ and the experiment environment containing `pika` and `prometheus-client`. Tests additionally use the existing gateway's Django dependency. No new dependency family or requirements file is introduced. Record exact installed versions for formal runs.

The baseline never loads Ollama, ChromaDB, or proposed agent runtimes. Its vocabulary reader parses the existing pure contract declaration. No network connections or metrics listeners start on import.

## Broker-free dry run

Use a separate smoke payload JSONL, not captured wrapper JSONL or formal labels:

```bash
python -m evaluation.baselines.threshold_only.controller \
  --run-id smoke-001 --output /tmp/threshold-smoke-001 \
  --dry-run <smoke-payloads.jsonl>
```

The output directory must not already exist. Dry-run publication is an in-memory stub, recorded as `mode=dry-run`; generated envelopes and timing are test evidence, not actual Layer 3 completions or experiment results. No RabbitMQ or HTTP port is used.

## Live experiment

First preserve prior evidence and isolate/reset the gateway database. Stop Triage, Strategy, Policy, Learning, and any other controllers. Check that the selected gateway is the only active Layer 3 instance. Set broker host/user/password explicitly in the environment; do not commit secrets.

```bash
ss -ltn '( sport = :8020 )'
python -m evaluation.baselines.threshold_only.controller \
  --live --run-id <run-id> --output <new-controller-run-directory>
```

The metrics bind itself also detects a busy port before consuming messages. This single command starts both independent workers and the shared metrics endpoint. Wait for both `fyp_threshold_worker_up` gauges to become 1 before replay. The controller rejects competing Triage/Strategy/Policy consumers; the feedback worker rejects competing Learning consumers. These checks do not replace verifying stale queued publications, gateway ownership, and empty run state.

The service uses exclusive subscriptions to its two input queues without modifying topology. It never creates or purges application queues. Each worker owns its own AMQP connection. Any worker failure stops both workers, retains evidence, and leaves unacknowledged work for reconciliation. Stop with Ctrl-C only after the agreed workload, Layer 3 handling, and feedback are complete. JSONL exports are written at shutdown.

## Mode A and Mode B

Mode A: Layer 1 is stopped. Replay the approved boundary capture using the common utility with the same run ID and a separate replay-output directory. Only fresh replay header timestamps support input-wait and boundary-to-decision metrics.

Mode B: use the unchanged Layer 1 cold procedure and SEG replay from the existing runbook, replacing only the proposed Layer 2 processes with Threshold. Source event timestamps are not fresh controller-boundary publication timestamps, so the baseline leaves those queue-wait metrics unobserved. Do not reset Chroma, EMA, or Ollama; keep them inactive.

## Monitoring

`observability/prometheus.threshold.yml` is a separate template. Reconcile it with the deployed scrape intervals, exporter configuration, authentication, and labels before formal use. It excludes ports 8010–8013. For Mode A, disable `layer1-application`; the dashboard labels those application panels N/A. Preserve the template's shared job names or adjust the new dashboard consistently.

Import the separate Threshold dashboard and select its experiment Prometheus datasource. It uses a datasource variable, not the proposed dashboard's hard-coded UID. Node/detector label names follow source (`detector`, not `model`). RabbitMQ per-queue metrics depend on deployed exporter settings; verify them rather than treating missing data as zero. No Grafana or Prometheus service is installed/restarted by these files.

## Tests

```bash
python -B -m unittest discover -s evaluation/baselines/threshold_only/tests -v
```

Tests use temporary storage and mock broker/side effects. Existing Layer 3 function bodies are exercised without import-time metrics servers or live consumer startup. The neutral template is rendered locally.

## Cold state and repetitions

Archive old records; stop competing controllers and Learning; reconcile/drain relevant queues; initialize an isolated Layer 3 database and a new run directory; start the selected gateway and Threshold workers; verify consumers/metrics; then replay. Do not alter original event IDs. Reusing IDs against old HITL state will suppress incidents because its database key is unique.

For Mode B additionally reset Layer 1 as prescribed by the frozen runbook. Nothing in this baseline automatically resets any shared state.

Prefer full captured Mode A populations. If compute cost requires it, the approved candidate protocol is one full run per architecture plus three repetitions on a frozen stratified subset, in balanced order:

1. Threshold → Single-Agent → Proposed.
2. Proposed → Threshold → Single-Agent.
3. Single-Agent → Proposed → Threshold.

Finalize subset, counts, human review, cutoffs, and rerun criteria before formal execution. No baseline results are claimed by the implementation.
