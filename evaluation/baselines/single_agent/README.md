# Single-Agent comparative baseline

One local `qwen3:1.7b` controller decides actions, risk, confidence and AUTO/HITL. Structural validation retains every valid route, with no Policy, Threshold rules, RAG or online learning.

For formal Ethernet Mode B, start with [ETHERNET_FULL_RUN.md](ETHERNET_FULL_RUN.md) and the [shared contract](../ETHERNET_SHARED_EXPERIMENT_CONTRACT.md). [Run_Single_Agent_Baseline.md](Run_Single_Agent_Baseline.md) retains Mode A/legacy operational context. The complete reference is [SINGLE_AGENT_BASELINE_SYSTEM.md](SINGLE_AGENT_BASELINE_SYSTEM.md), governed by the [frozen experiment design](../BASELINE_EXPERIMENT_DESIGN.md).

## Environment and offline smoke

Use the existing Python 3.10+ environment with `requests`, `pika`, `prometheus-client`; tests additionally use Django. No new requirements file is necessary. Tests and dry runs do not contact Ollama or RabbitMQ. Run from repository root:

```bash
python -m evaluation.baselines.single_agent.controller \
  --dry-run <plain-incident-jsonl> --mock-responses <mock-response-jsonl> \
  --run-id mock-001 --output <new-output-directory> --network-medium wifi
```

Each mock line is `{"raw_response":"<model output string>"}` or `{"error":"timeout"}` (also connection/http/transport/invalid_runtime_response), consumed once per attempted generation. Supply enough responses for retries. These are test fixtures, not labels or measured model results. Envelopes are recorded in `dry_run_envelopes.json`, with `mode=dry-run` and no warmup.

## Live startup

After the runbook's cold-state and ownership checks, export explicit broker variables and `OLLAMA_HOST` (default `http://localhost:11434`):

```bash
python -m evaluation.baselines.single_agent.controller \
  --live --run-id <run-id> --output <new-output-directory> \
  --network-medium ethernet --evaluation-mode B --dataset-sha256 <input-sha256>
```

The service binds `:8030`, records available runtime identity, preloads the model, performs one fixed non-measured warmup, then starts controller and feedback workers. Wait for both `fyp_single_agent_worker_up` gauges to equal 1 before input. A busy port, failed warmup or competing consumer aborts startup. Clean Ctrl-C exports journal records and closes the run manifest. Never reuse an output directory.

Ethernet uses the reviewed deployment profiles and verified sockets/routes without rewriting hostname resolution. The network flag only affects provenance. Do not install the legacy standalone Prometheus template over the shared Ethernet configuration.

## Validation

```bash
python -B -m unittest discover -s evaluation/baselines/single_agent/tests -v
```

Live smoke validation and deployment-specific model/CPU/exporter verification remain required. No formal comparative result is established by offline tests.

## Formal scoring and evidence

Use frozen routing-label-policy-v2 with the shared Mode B evaluator, including
`--attempts` for the real model-attempt export. No boundary capture/conversion
is needed. NORMAL is excluded from FAR/routing FER; Expected-AUTO coverage and
missing before routing are separate from routing FER. Controller processing time
is not source-event end-to-end latency. Raw model route, accepted output, final
dispatched route and fallback are distinct fields; fallback is not valid output.

Preserve preload plus the fixed non-measured inference. The completed Proposed
Adaptive run had no identical dedicated warmup, so routing metrics use the shared
contract but directly matched LLM latency/residency claims are unsupported.

A worker failure/restart after replay begins invalidates that formal RUN_ID.
Preserve evidence, never resume it, and start a new cold run. See the runbook's
lifecycle/status rules and [preparation audit](ETHERNET_PREPARATION_AUDIT.md).
The changes need a reviewed committed revision and external manifests, followed
by isolated integration validation and live readiness gates before formal use.
