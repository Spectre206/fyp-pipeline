# Ethernet deployment profile

Deployment configuration only: no algorithms, prompts, models, thresholds, queues, ports or controller semantics change. Wi-Fi remains enabled and remains the Internet/default route. Ethernet has no default gateway. Do not change `/etc/hosts` or NetworkManager profiles for this procedure.

| Node | Ethernet address | Interface |
|---|---|---|
| stream-node | 10.10.10.11 | enp2s0 |
| ai-brain-node | 10.10.10.12 | enp2s0 |
| gateway-node | 10.10.10.13 | enx00e04c681057 |

## Startup environments

Verify the same frozen application revision on all nodes with `git branch --show-current`, `git rev-parse HEAD`, and `git status --short`. Use the existing Layer 1 startup procedure unchanged: its broker is co-located on stream-node, and topology setup stays on localhost. Do not recreate topology merely to change transport.

On Node 2, in **each** selected controller pane:

```bash
export REPO=/home/spectre206/fyp-pipeline
source "$REPO/.venv/bin/activate"
source "$REPO/deployment/ethernet/node2.env.sh"
```

This exports `RABBITMQ_HOST=10.10.10.11`, `RABBITMQ_PORT=5672`, and `OLLAMA_HOST=http://localhost:11434`. Supply credentials securely in each pane, or through the existing protected launch environment:

```bash
read -r -p 'RabbitMQ user: ' RABBITMQ_USER
export RABBITMQ_USER
read -r -s -p 'RabbitMQ password: ' RABBITMQ_PASS
export RABBITMQ_PASS
printf '\n'
```

For Proposed, `cd "$REPO/layer2"` and launch each in its own pane: `python agents/triage_agent.py`, `python agents/strategy_agent.py`, `python agents/policy_agent.py`, `python agents/learning_agent.py`. Follow [Full_Rerun.md](../../Full_Rerun.md) for the existing state/startup protocol; this profile does not reset state.

On Node 3, in **each** Django, HITL consumer and Auto Executor pane:

```bash
export REPO=/home/spectre/fyp-pipeline
source "$REPO/venv/bin/activate"
source "$REPO/deployment/ethernet/node3.env.sh"
```

Supply the same runtime credential variables as above. The profile exports only the broker host/port; the helpers fix vhost to `fyp`. Existing processes must be stopped cleanly and restarted with the new environment; exporting variables does not redirect existing connections.

Use separate panes: from `$REPO/layer3/dashboard`, run `python manage.py runserver 0.0.0.0:8000` and `python manage.py consume_hitl`; from `$REPO/layer3`, run `python auto_executor/executor.py`.

Django now accepts direct Ethernet access at **http://10.10.10.13:8000** and retains all existing Wi-Fi/hostname entries. Hostname access still follows existing resolution and does not alone prove Ethernet. Ollama remains localhost, Chroma remains its local PersistentClient, and SQLite remains local.

## Prometheus origin and manual deployment

`prometheus.ethernet.yml` derives from the manually captured gateway configuration available at `/etc/prometheus/prometheus.yml`, inspected on 2026-09-24. Source SHA-256: `de9730d9c7cba01268f5fbd3a7f350b94d687711fdb4104addff18cacf49314c`. The old empty `Phase_0_Infrastructure/configs/prometheus.yml` is not the live deployment and is untouched.

All ten jobs are preserved: `fyp-cluster`, `fyp-layer1`, `fyp-agent-pipeline`, `fyp-threshold-baseline`, `prometheus`, `node`, `rabbitmq`, `fyp-layer3-autoexec`, `fyp-layer3-hitl`, `fyp-single-agent-baseline`. Global scrape/evaluation intervals remain 15s. Cluster, Layer 1, Proposed agents, both baselines and HITL retain explicit 5s scrape intervals; cluster retains its 5s timeout. Other jobs inherit the original global defaults.

Remote targets use Ethernet IPs; each retains its original `hostname:port` instance label. Grafana's fixed node selectors and display overrides therefore remain compatible without JSON changes. Prometheus self-scrape remains `localhost:9090`; the duplicate local `node` job remains `localhost:9100`, including its existing label identity. Gateway self-scrapes may use a local kernel route, not the physical switch.

**Manual gateway procedure only; nothing in this profile deploys automatically:**

1. Back up the current `/etc/prometheus/prometheus.yml` to a unique, protected archive path. Retain its ownership/mode and checksum; never overwrite the Wi-Fi backup.
2. Review the Ethernet template against the current live config, including any changes since capture. Run `promtool check config "$REPO/deployment/ethernet/prometheus.ethernet.yml"` before installation.
3. Manually copy/install the reviewed file to `/etc/prometheus/prometheus.yml`, preserving the deployment's required ownership/mode.
4. Run `promtool check config /etc/prometheus/prometheus.yml`. Do not reload a failing config; restore the archived file if needed.
5. Run `sudo systemctl reload prometheus`. If the unit lacks reload support, use its established deployment reload procedure before measurement.
6. Inspect `curl -fsS http://localhost:9090/api/v1/targets`: confirm Ethernet scrape URLs, original logical instances, and health of the active condition's targets.

Inactive controller jobs can be DOWN; do not start competing controllers to make every target green. Retain the same job-selection policy and scrape intervals across matched Wi-Fi/Ethernet conditions. Grafana datasource/live dashboard state needs no changes. Its combined network panel includes Wi-Fi Internet traffic and is not transport proof by itself.

## Prove application transport before formal runs

Run on Node 2 while its controller is active:

```bash
ip route get 10.10.10.11
sudo ss -ntp | grep ':5672'
ip -s link show dev enp2s0
```

On Node 3:

```bash
ip route get 10.10.10.11
sudo ss -ntp | grep ':5672'
ip -s link show dev enx00e04c681057
curl -fsS http://localhost:9090/api/v1/targets
```

On Node 1:

```bash
sudo rabbitmqctl list_connections name peer_host peer_port user vhost
ip -s link show dev enp2s0
```

Remote broker peers should include `10.10.10.12` and `10.10.10.13` when those clients are active. Save socket endpoints, peer addresses, route output and Ethernet counters before/after the smoke workload. Scrape URLs should use `.11/.12/.13` while `instance` stays hostname-based, except the intentionally local jobs.

Optional bounded packet observation on Nodes 1 and 2:

```bash
sudo timeout 30 tcpdump -ni enp2s0 \
  'net 10.10.10.0/24 and tcp and (port 5672 or portrange 8000-8030 or port 9100 or port 15692)'
```

Use `enx00e04c681057` on gateway-node. Also inspect equivalent FYP ports on the actual Wi-Fi interface, filtering peer addresses in `192.168.18.0/24`. Wi-Fi Internet traffic is expected; equivalent FYP inter-node traffic over Wi-Fi is not. Node 1's co-located broker traffic and local Ollama/SQLite/self-scrapes need not traverse Ethernet.

## Controller branches and rollback

Apply these deployment settings later alongside each reviewed branch; do not merge controller implementations:

| Condition | Node 2 broker | Metrics transport | Local model |
|---|---|---|---|
| Proposed | 10.10.10.11 | 10.10.10.12:8010–8013 | localhost:11434 |
| Threshold | 10.10.10.11 | 10.10.10.12:8020 | Inactive |
| Single-Agent | 10.10.10.11 | 10.10.10.12:8030 | localhost:11434 |

Layer 3 uses the same Ethernet broker profile for every controller. Use baseline-specific runbooks/CLI network metadata on those branches. Only one controller condition may own the shared queues at a time.

To roll back, stop affected clients cleanly, restore and validate the archived Wi-Fi Prometheus config, then reload it. Start fresh application panes without sourcing the Ethernet profile; in reused panes unset `RABBITMQ_HOST` and `RABBITMQ_PORT` and restore the prior protected launch environment. Confirm the existing defaults/`.env` and unchanged hostname resolution point to the Wi-Fi broker before restarting. Check sockets and scrape URLs again. No Git checkout, Wi-Fi disablement, or model/storage relocation is needed.

## Experiment safety and dependency note

Use fresh run IDs; preserve Wi-Fi evidence and previous SQLite/JSONL artifacts before existing cold-state resets. Freeze application commit, datasets, prompts/schema/model settings, human-review policy, monitoring intervals and physical machines within matched comparisons. Archive runtime configuration and transport proof with each condition. Smoke tests are integration checks, not formal results. Do not start a formal experiment until Ethernet transport is proven.

`structlog>=26.1.0` is added to Layer 3 requirements because Auto Executor imports it and the verified gateway already has 26.1.0. This is a **reproducibility fix, not Ethernet logic**; it installs/upgrades nothing by itself. No unrelated requirements are changed.
