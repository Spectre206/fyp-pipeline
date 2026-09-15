# Shared baseline utilities

Run modules from the repository root with the interpreter containing `pika` and `prometheus-client`. These utilities do not import live proposed-system agents. The authoritative vocabulary is read from the literal `ALLOWED_ACTIONS` declaration without executing that module.

## Capture and freeze Mode A input

Capture is a dedicated session, with Triage and all other controllers stopped. `capture_incidents` becomes the exclusive consumer of the existing `anomaly.detected` queue. It adds no queues or bindings and changes no Layer 1 code.

Set `RABBITMQ_HOST`, `RABBITMQ_USER`, and `RABBITMQ_PASS` securely in the process environment; `RABBITMQ_PORT` defaults to 5672. The vhost is `fyp`. No credential defaults or automatic `.env` discovery are supplied.

```bash
python -m evaluation.baselines.common.capture_incidents \
  --live --capture-id capture-v1 --count <reconciled-expected-count> \
  --output <new-capture-directory>
```

Choose the expected count from the capture protocol; there is no historical-count default. The utility waits until that count is received. An interrupt or error leaves an incomplete file without a completed manifest. Do not freeze it. Reconcile residual queues and Layer 1 publication evidence before approving a capture; reaching the count alone does not prove the producer has finished.

Each JSONL wrapper preserves exact message bytes in `body_base64`, routing key, capture order, event ID, capture wall time, and monotonic offset. Durable flush/fsync precedes ACK. Duplicate/missing IDs or unexpected routing keys stop capture and leave the failing delivery unacknowledged. Preserve partial evidence and reconcile before recapturing; never silently discard duplicates.

The manifest records SHA-256, count, unique IDs, and the schedule convention. Freeze the capture and manifest together. They contain no controller outputs or ground-truth fields.

## Replay

Start exactly one selected controller plus its handling/feedback processes first. Verify empty relevant queues and no stale publishers. Use the same `run_id` for controller and replay, but separate new directories for their evidence.

```bash
python -m evaluation.baselines.common.replay_incidents \
  --live --capture <capture-directory>/incidents.jsonl \
  --manifest <capture-directory>/incidents.manifest.json \
  --run-id <run-id> --output <new-replay-directory> --speed 1
```

Checksum, ID uniqueness, ordering, counts, schedule, and routing keys are validated before connecting. Original bodies, event IDs, and event timestamps are untouched. The first capture starts at offset zero; subsequent interarrival intervals follow capture offsets divided by `speed`. Freeze the same speed and file for every condition.

Fresh `run_id`, `replay_published_at`, and capture sequence are AMQP headers, not payload labels. Publication is persistent, mandatory, and confirmed. The replay journal records pre-publish time and confirmation time. A new output directory is mandatory; accidental evidence overwrite is refused. On partial failure, preserve the run and repeat only under the prespecified rerun policy. No automatic replay restart is attempted.

Existing proposed agents ignore the new headers. Common replay publication logs still provide the input boundary, but the proposed system's Triage timestamp is not an exact controller-receipt timestamp. Do not claim identical latency boundaries without corresponding evidence.

## Analyze

```bash
python -m evaluation.baselines.common.analyze_comparison \
  --capture <capture-directory>/incidents.jsonl \
  --manifest <capture-directory>/incidents.manifest.json \
  --decisions <controller-run>/decision.jsonl \
  --feedback <controller-run>/feedback.jsonl \
  --labels <independent-labels.jsonl> --expect-hitl-feedback
```

Output is JSON on stdout. Omit `--labels` when annotations are not finalized: quality measures become `not computable`. Omit `--expect-hitl-feedback` for a protocol that does not require exhaustive HITL feedback; then only AUTO decisions define feedback-completion expectations. A sampled-review analysis needs an explicitly frozen extension rather than pretending all HITL cases were required.

Canonical decision JSONL requires `event_id`, `routing_decision`, `risk_tier`, and `recommended_actions`; optional `processing_seconds` and `boundary_to_decision_seconds` must describe the same boundaries before comparison. Threshold exports confirmed decisions to this format. Other controllers need an evidence-preserving export into it; the current proposed stage analyzer is not a compatible input format and is not changed.

Conflicting decisions for one ID are reported and treated as lacking a uniquely scoreable decision. Duplicate and unexpected IDs remain visible. Missing decisions remain in route/risk/FAR/FER population denominators as specified by the frozen design. Malformed JSONL fails the CLI rather than being silently skipped.

Action validity uses three distinct global allowlisted actions. Acceptable-action coverage is the macro mean of `|selected ∩ acceptable| / |acceptable|` on nonambiguous labeled incidents with nonempty acceptable sets; missing decisions contribute zero. It is coverage of alternatives, not required-action completion. The acceptable-selected fraction and prohibited-action count are separate. Required categories are retained in annotation data but are not scored without a separately frozen category mapping.

## Durable records and failure boundary

`journal.sqlite3` is authoritative during a run; it uses WAL and synchronous FULL. JSONL exports occur at clean shutdown. Following a crash, preserve SQLite and its sidecars before recovery/export. A journal records delivery bytes, prepared/confirmed decisions, all feedback attempts, quarantine, and failures.

Confirmed duplicate inputs are not republished; collisions between different bodies with the same ID are quarantined. Publication can succeed before confirmation is durably recorded or the input is acknowledged. This remains an at-least-once crash window, not exactly-once Layer 3 handling. Failed live processes stop instead of retrying indefinitely or creating a new identity. Resume/recovery requires operator reconciliation; the CLI never reuses an existing run directory.

## Optional neutral HITL presentation

The additive settings module loads existing Layer 3 settings and supplies only a template-search overlay. Existing backend files, database paths, migrations, decisions, and feedback behavior remain unchanged.

On the gateway, from the repository root, using its existing Django environment:

```bash
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
export DJANGO_SETTINGS_MODULE=evaluation.baselines.common.presentation_settings
python layer3/dashboard/manage.py runserver 0.0.0.0:8000
```

Use the same neutral presentation for all formal conditions. It shows Controller Risk Tier, Controller Confidence (unavailable for Threshold), Decision Rationale, and explicitly scoped controller timing. It does not relabel proposed Policy processing as full-controller latency. The approved legacy UI remains available for smoke testing.

This overlay does not isolate databases. Use a dedicated experiment checkout/database and archive/reset Layer 3 between runs. Human-visible deterministic rationale may reveal the condition; do not claim reviewer blinding merely because labels are neutral.
