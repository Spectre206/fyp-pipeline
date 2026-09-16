# Common comparative infrastructure

These modules contain no controller routing policy or model prompt. `contracts.py` preserves both actual Layer 1 input forms, maps detector names to semantic families, validates observable fields, reads the authoritative action vocabulary without running Proposed agents, and rejects duplicate/nonfinite JSON. `journal.py` stores durable evidence in SQLite (WAL, synchronous FULL), indexes prepared/confirmed decisions and exports records in insertion order. `layer3_adapter.py` serializes native decisions into shared Layer 3 legacy keys without requiring rule versions or fabricating stages.

`rabbitmq.py` requires `RABBITMQ_HOST`, `RABBITMQ_USER`, `RABBITMQ_PASS`; `RABBITMQ_PORT` defaults to 5672, vhost is `fyp`. It does not load `.env`, create topology or purge queues. Live callers enable publisher confirms before persistent mandatory publication. Exclusive subscriptions and passive ownership checks reject competing consumers; operators must exclude stale publishers and verify unacknowledged messages separately.

## Capture and replay

From repository root, with configured broker environment:

```bash
python -m evaluation.baselines.common.capture_incidents \
  --live --capture-id <unique-id> --count <reconciled-incident-count> \
  --output <new-capture-directory>
python -m evaluation.baselines.common.replay_incidents \
  --live --capture <capture-directory>/incidents.jsonl \
  --manifest <capture-directory>/incidents.manifest.json \
  --run-id <controller-run-id> --output <new-replay-directory> --speed 1
```

Capture is the sole `anomaly.detected` consumer. Preserve exact bytes (base64), routing key, ID, sequence and observed monotonic offsets; fsync precedes ACK. A completed manifest records checksum/count/schedule. Missing manifest means incomplete evidence. Determine the incident count independently; SEG input count and historical totals are not substitutes. Capturing a queued backlog records its drain schedule, not original publication timing.

Replay validates checksum, IDs, order, supported routes and offsets before connecting. It requires exactly one input consumer and an empty ready queue; manually verify its identity and zero unacknowledged messages. Waiting services RabbitMQ heartbeats. Fresh timestamps/run identity are AMQP headers, never payload mutations. Publication logs are fsynced after confirmation. A completed marker is written only on success. Partial runs need reconciliation; no automatic resume or overwrite is provided.

## Comparative analysis

```bash
python -m evaluation.baselines.common.analyze_comparison \
  --capture <capture-directory>/incidents.jsonl \
  --manifest <capture-directory>/incidents.manifest.json \
  --decisions <controller-output>/decision.jsonl \
  --feedback <controller-output>/feedback.jsonl \
  --run-id <run-id> --controller single_agent \
  --labels <independent-labels.jsonl> --expect-hitl-feedback
```

Labels and feedback are optional; no labels means correctness metrics are not computable. Expected IDs come from the verified capture, not received decisions. FAR uses all scoreable unsafe labels; FER uses all scoreable safe/expected-AUTO labels. Missing decisions are explicitly listed and do not count as correct route/risk classifications. They do not enter FAR/FER numerators. Ambiguous labels remain visible in coverage but outside quality denominators. Zero denominators return `not computable` with null value. Wrong-run/controller evidence and unexpected IDs are reported; conflicting duplicate decisions are excluded from uniquely scoreable completion.

Action validity is three distinct allowlisted identifiers. Acceptable-action coverage is the macro mean of selected∩acceptable / acceptable for nonempty acceptable sets; this scores alternatives, not required-category completion. Selected-action relevance and prohibited-action counts are separate. Required-category scoring needs an independently frozen category map. Feedback completion defaults to AUTO; `--expect-hitl-feedback` requires all dispatched decisions. Raw route metrics use the last available extracted route (even from invalid output), alongside raw-route availability, final routes and fallback counts. Attempt counts in this report cover confirmed decisions; `attempt.jsonl` is the full attempt evidence including interrupted/non-dispatched incidents.

Latency summaries use available finite values, median and nearest-rank p95. Compare equivalent receipt-to-confirmed-publication boundaries; local processing is not interchangeable with the Proposed sum of component times. Mode B requires independent Layer 1 population reconciliation; no conversion of its artifacts into the capture-based analyzer input is supplied here.

## Neutral presentation

Set `PYTHONPATH` to include the repository root and `DJANGO_SETTINGS_MODULE=evaluation.baselines.common.presentation_settings` in gateway Django panes. The overlay selects three templates without editing Layer 3 or changing its database. It hides raw envelopes, controller/model metadata, response protocol, routing codes and Policy latency. Genuine reasoning/actions remain visible, so complete blinding cannot be guaranteed. Use the same presentation policy across conditions.

See the [Single-Agent runbook](../single_agent/Run_Single_Agent_Baseline.md) for state isolation and exact startup commands. Generated evidence belongs in ignored results directories and backed-up experiment storage, never committed implicitly. Publish/ACK and shared Layer 3 handling are not exactly-once.
