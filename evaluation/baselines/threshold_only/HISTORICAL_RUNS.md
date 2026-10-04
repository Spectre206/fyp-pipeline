# Threshold-only Ethernet run history

This record preserves both execution attempts and their distinct protocol
statuses. Formal closeout verified the preserved node-local evidence for the
completed replacement run. This gateway-only documentation edit did not rerun
or regenerate results, or independently reopen all native Node 1/2 artifacts,
which are not locally available. An offline evaluator assesses record integrity;
it cannot certify upstream process continuity.

| Run ID | Protocol status | Formal comparison |
|---|---|---|
| `threshold-ethernet-full-20261003-053739` | `RESUMED_INVALID_FOR_FORMAL_COMPARISON` | Excluded |
| `threshold-ethernet-full-20261003-084252` | `COMPLETED_UNINTERRUPTED` | Included |

## Interrupted and resumed attempt

The first run began formal execution at revision
`ea3a0407983ca0ff75e57e89a1c09cbc90f73fad`. A short power outage interrupted the
run; the throughput detector exited with `pika.exceptions.AMQPHeartbeatTimeout`.
The observed queue state was 286 messages in `detect.throughput` and zero
consumers. The operator later restarted that detector under the same RUN_ID.
This resumed execution lost uninterrupted-run validity.

Downstream controller exports and evaluator outputs could subsequently be
internally consistent. They do not reverse the interruption or make the run
eligible. All results from this attempt remain diagnostic/historical only and
must not enter the formal comparison table. Preserve the original node-local
artifacts and protocol history; do not delete, relabel or overwrite them.

## Completed replacement run

Run `threshold-ethernet-full-20261003-084252` used execution revision
`c1cdbd70e66e8a70b68d22c2eec539e70515cfdb` on
`experiment/threshold-baseline`, Ethernet Mode B, replay speed 1.

The completed formal closeout evidence records successful replay (SEG exit 0), no
application-worker restart after the replay marker, zero ready/unacknowledged
messages in experiment queues, zero DLQ, zero pending HITL, 639/639 controller
feedback, and successful evaluation with `no_detected_record_errors` and
FAR/FER/coverage agreement. Its formal status is `COMPLETED_UNINTERRUPTED`.

The gateway protocol log locally corroborates the completed status at that
revision; gateway metrics and SQLite corroborate feedback and HITL counts.
Formal closeout also verified the preserved Node 1/2 controller/evaluator and
protocol evidence; those native artifacts were not independently reopened by
this gateway-only edit. Formal eligibility rests on that verified full protocol
evidence, not merely clean controller exports. This verification of the completed
replacement does not rehabilitate the earlier resumed run.

See the [final result record](results/ETHERNET_RESULTS.md) and
[shared comparison](../COMPARISON.md). A later worker failure requires preservation
of that run and a new RUN_ID/cold reset, never a formal same-ID resume. No raw
history was changed during this documentation update.
