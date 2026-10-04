# Proposed Adaptive Ethernet demo

**Demo outputs are not formal experimental evidence.** This is a short restart
and demonstration guide for the existing installation. For research execution,
use [the formal Ethernet runbook](../Ethernet_Full_Rerun.md).

## Connect and prepare

Connect the same three laptops to the unmanaged gigabit switch with Ethernet
cables; keep Wi-Fi available for Internet access. Use the reviewed existing
network configuration; do not install packages or change gateways.

| Node | Ethernet IP | Interface |
|---|---|---|
| stream-node | 10.10.10.11 | enp2s0 |
| ai-brain-node | 10.10.10.12 | enp2s0 |
| gateway-node | 10.10.10.13 | enx00e04c681057 |

On each node, check `ip -br addr`, `ip route get <peer-IP>`, and
`ping -c 2 <peer-IP>` for the other two nodes. Require the Ethernet interface and
10.10.10.x source. `sudo ethtool <interface>` should show 1000Mb/s, full duplex
and link detected.

Use a demo checkout/state whose active files can be updated. Formal evidence
must already be preserved separately: the demo updates Feature Store state,
Fusion output, Chroma, EMA and the gateway database. It does not cold-reset them.
Stop if the active state is the only remaining copy of formal evidence. Stop
previous application consumers before startup; do not run competing controllers.

In **every application terminal**, select that node's existing reviewed Python
environment, then activate it:

```bash
export REPO="$HOME/fyp-pipeline"
read -r -p 'Absolute existing Python environment directory: ' EXPERIMENT_VENV
test -f "$EXPERIMENT_VENV/bin/activate" || exit 1
source "$EXPERIMENT_VENV/bin/activate"
cd "$REPO"
```

Node 1 may use its established system Python instead if that is its reviewed
installation. On **every Node 2/3 application terminal**, also source the
appropriate profile and enter the existing RabbitMQ credentials:

```bash
# Node 2:
source "$REPO/deployment/ethernet/node2.env.sh"
# Node 3: use node3.env.sh instead of node2.env.sh above.
set +x
read -r -p 'RabbitMQ user: ' RABBITMQ_USER
read -r -s -p 'RabbitMQ password: ' RABBITMQ_PASS
printf '\n'
export RABBITMQ_USER RABBITMQ_PASS
```

Node 1 retains its existing local broker configuration, vhost `fyp`.

## Start the system

Run each long-running command below in its **own terminal**, after the setup
above. Leave it running. Paths are relative to `$REPO`.

**Node 1:** check/start the existing broker, then declare the existing topology:

```bash
sudo systemctl start rabbitmq-server
cd "$REPO/layer1/rabbitmq"
python3 setup_topology.py
sudo rabbitmqctl list_queues -p fyp name consumers messages_ready messages_unacknowledged
```

Investigate old backlogs before demo publication; do not purge unknown messages.

| Node 1 working directory | Command | Metrics port |
|---|---|---|
| layer1/validator | `python3 validator.py` | 8002 |
| layer1/adm | `python3 adm_runner.py` | — |
| layer1/fusion_engine | `python3 fusion_engine.py` | 8003 |
| layer1/adm | `python3 detectors/error_rate.py` | 8004 |
| layer1/adm | `python3 detectors/throughput_drop.py` | 8005 |
| layer1/adm | `python3 detectors/auth_flood.py` | 8006 |
| layer1/adm | `python3 detectors/cpu_spike.py` | 8007 |
| layer1/adm | `python3 detectors/schema_drift.py` | 8008 |

**Node 2:** start/check the existing Ollama installation. Confirm the installed
`qwen3:1.7b` model; do not download or change models during the demo.

```bash
sudo systemctl start ollama
curl -fsS http://localhost:11434/api/tags
ollama list
```

Choose one fresh demo ID (for example `demo-20261004-150000`). In each of the four
Node 2 agent terminals, set that **same** ID and a separate demo output root:

```bash
read -r -p 'Same demo ID in all four terminals: ' LAYER2_EVALUATION_RUN_ID
export LAYER2_EVALUATION_RUN_ID
export LAYER2_EVALUATION_DIR="$HOME/fyp-demo-results"
cd "$REPO/layer2"
```

| Node 2 command (one per terminal) | Metrics port |
|---|---|
| `python3 agents/triage_agent.py` | 8010 |
| `python3 agents/strategy_agent.py` | 8011 |
| `python3 agents/policy_agent.py` | 8012 |
| `python3 agents/learning_agent.py` | 8013 |

**Node 3:** check the existing Django database migrations once, then start the
three application processes in separate prepared terminals:

```bash
cd "$REPO/layer3/dashboard"
python3 manage.py migrate
```

| Node 3 working directory | Command | Port |
|---|---|---|
| layer3 | `python3 auto_executor/executor.py` | 8014 |
| layer3/dashboard | `python3 manage.py consume_hitl` | — |
| layer3/dashboard | `python3 manage.py runserver 0.0.0.0:8000 --noreload` | 8000 |

## Quick readiness and observability

From gateway, check the application metrics before publishing:

```bash
for target in 10.10.10.11:{8002..8008} 10.10.10.12:{8010..8013} 10.10.10.13:8014 10.10.10.13:8000; do
  curl -fsS "http://$target/metrics" >/dev/null || { echo "Unavailable: $target"; exit 1; }
done
curl -fsS http://localhost:9090/api/v1/targets
```

On Node 1, repeat `sudo rabbitmqctl list_queues -p fyp name consumers
messages_ready messages_unacknowledged` as a single command. Confirm the intended
consumers are present. On Nodes 2/3, `ss -nt | grep ':5672'` should show remote
broker connections to `10.10.10.11:5672`.

Keep the existing Prometheus/Grafana services and configuration. Open the
configured Grafana URL and **Hybrid Agentic Framework — Final Research
Observability** dashboard. Required Proposed-system targets should be UP;
intentionally inactive controller targets can remain DOWN. Open the HITL UI at
<http://10.10.10.13:8000/>. Do not reinstall the monitoring template.

## Publish a small demo workload

On Node 1, in one prepared terminal, generate into a fresh private demo directory
outside the checkout. The existing SEG generates the full source; select 50
inputs locally before replay because SEG has no `--limit` option. No formal
corpus, labels or run directory is reused or overwritten.

```bash
umask 077
DEMO_DIR=$(mktemp -d "$HOME/fyp-demo.XXXXXXXX")
cd "$REPO/layer1/seg"
python3 seg.py --mode generate --config config/seg_config.json --output "$DEMO_DIR"
python3 - "$DEMO_DIR" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
events = [json.loads(line) for line in (root / 'events_1950.jsonl').read_text().splitlines() if line.strip()]
for component in sorted({e['affected_component'] for e in events}):
    normal = [e for e in events if e['affected_component'] == component and e.get('anomaly_type', 'NORMAL') == 'NORMAL']
    abnormal = [e for e in events if e['affected_component'] == component and e.get('anomaly_type', 'NORMAL') != 'NORMAL']
    if len(normal) >= 20 and len(abnormal) >= 30:
        selected = normal[:20] + abnormal[:30]
        break
else:
    raise SystemExit('No suitable demo component; stop without publication.')
(root / 'demo50.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in selected))
print('Demo component:', component, 'events:', len(selected))
PY
# Only continue if generation and selection succeeded:
test -s "$DEMO_DIR/demo50.jsonl" || exit 1
python3 seg.py --mode replay --config config/seg_config.json --input "$DEMO_DIR/demo50.jsonl" --speed 1
```

The first 20 normal inputs support calibration if that component is cold (the
first 19 accepted events are withheld). Existing demo state changes what is
observed. Fifty inputs do not guarantee fifty incidents or both routing paths.
Generated labels are unused; there is no research scoring in this procedure.

## What to show and how to stop

Follow Layer 1 detector/Fusion logs and Grafana, then Triage and Strategy
proposals, deterministic Policy AUTO/HITL authorization, and simulated AUTO
execution. In the dashboard, approve/reject/modify suitable pending demo
incidents where available; observe `outcome.feedback` and Learning activity.
Do not change thresholds or fabricate incidents to force a particular route.
CPU-only inference may take time; inspect queue backlogs while it processes.

After SEG exits, allow application queues and feedback to drain and finish the
chosen demo human reviews. On Node 1, inspect queue ready/unacknowledged counts
with the readiness command above. Then Ctrl+C the application processes in
their owning terminals; infrastructure may remain running. If interrupted,
record that the demo was interrupted before a later restart. No completion here
is a formal experiment claim. Unset credentials or close the application shells.
