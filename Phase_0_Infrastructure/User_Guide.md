# Phase 0: Infrastructure Setup & Environment Validation

> **Project:** Distributed Multi-Agent Self-Healing Data Pipelines
> **Team:** Muhammad Adeel & Muhammad Asim | **Supervisor:** Dr. Laeeq Ahmed
> **Department:** CS&IT, UET Peshawar — Nowshera Campus

This guide provides exact, reproducible steps to bring up the three-node cluster from scratch. All service connections, SSH commands, and access URLs use **hostnames only** — no IP addresses appear in any config or application code. When moving to a new LAN, only `/etc/hosts` on each node needs updating.

---

## Table of Contents

1. [Hardware and Network Topology](#1-hardware-and-network-topology)
2. [Base Configuration — All Nodes](#2-base-configuration--all-nodes)
3. [Observability Stack](#3-observability-stack)
4. [Message Broker — RabbitMQ](#4-message-broker--rabbitmq)
5. [AI Stack — Ollama and ChromaDB](#5-ai-stack--ollama-and-chromadb)
6. [Datasets](#6-datasets)
7. [Hostname Verification](#7-hostname-verification)
8. [Moving to a New LAN](#8-moving-to-a-new-lan)
9. [Validation Checklist](#9-validation-checklist)

---

## 1. Hardware and Network Topology

```
┌──────────────────────────────────────────────────────────────────┐
│                     Cluster LAN Network                          │
│                                                                  │
│  ┌────────────────┐    ┌─────────────────┐    ┌──────────────┐  │
│  │  stream-node   │    │  ai-brain-node  │    │ gateway-node │  │
│  │                │◄──►│  (Headless)     │◄──►│              │  │
│  │  RabbitMQ      │    │  Ollama         │    │  Prometheus  │  │
│  │  Layer 1       │    │  ChromaDB       │    │  Grafana     │  │
│  └────────────────┘    └─────────────────┘    └──────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

| Node | Hostname | OS | CPU | RAM | Primary Services |
|:-----|:---------|:---|:----|:----|:-----------------|
| Node 1 | `stream-node` | Ubuntu 24.04 Desktop | AMD Ryzen 5 | 8 GB | RabbitMQ, Layer 1, Datasets |
| Node 2 | `ai-brain-node` | Ubuntu 24.04 Server (Headless) | AMD Ryzen 5 | 8 GB | Ollama, ChromaDB, 4 Agents |
| Node 3 | `gateway-node` | Ubuntu 24.04 Desktop | Intel Core i5 | 8 GB | Prometheus, Grafana, HITL |

> ⚠️ **WiFi is acceptable for Phase 0 only.** No benchmark measurements should be recorded over WiFi. All paper benchmarks are taken on Gigabit Ethernet after 15 July 2026.

---

## 2. Base Configuration — All Nodes

> Run every step in this section on **all three nodes** before proceeding.

### 2.1 Set Hostnames

```bash
# On Node 1
sudo hostnamectl set-hostname stream-node && sudo reboot

# On Node 2
sudo hostnamectl set-hostname ai-brain-node && sudo reboot

# On Node 3
sudo hostnamectl set-hostname gateway-node && sudo reboot
```

Verify after reboot:

```bash
hostnamectl | grep hostname
```

---

### 2.2 Assign Static IPs via NetworkManager

Static IPs keep `/etc/hosts` entries stable across reboots. When moving to a new LAN, reassign IPs first and then update `/etc/hosts`.

Find your network interface name:

```bash
ip link show
```

Open the NetworkManager TUI:

```bash
sudo nmtui
```

Navigate: **Edit a Connection → select your network → IPv4 Configuration → Manual**

| Node | Example Address | Gateway | DNS |
|:-----|:----------------|:--------|:----|
| stream-node | `<your-lan-prefix>.101/24` | `<your-router-ip>` | `8.8.8.8` |
| ai-brain-node | `<your-lan-prefix>.102/24` | `<your-router-ip>` | `8.8.8.8` |
| gateway-node | `<your-lan-prefix>.103/24` | `<your-router-ip>` | `8.8.8.8` |

After saving, restart and verify:

```bash
sudo systemctl restart NetworkManager
ip addr show
ping 8.8.8.8 -c 3
```

---

### 2.3 Configure /etc/hosts — The Only Place IPs Live

This is the **only file** in the entire cluster that contains IP addresses. Everything else uses hostnames. Run on all three nodes:

```bash
sudo nano /etc/hosts
```

Add these three lines at the bottom, replacing the IPs with the actual addresses from step 2.2:

```
<stream-node-ip>      stream-node
<ai-brain-node-ip>    ai-brain-node
<gateway-node-ip>     gateway-node
```

Verify resolution works from every node:

```bash
ping -c 2 stream-node
ping -c 2 ai-brain-node
ping -c 2 gateway-node
```

All three should respond from all three nodes before continuing.

---

### 2.4 Passwordless SSH — All Directions

Generate an SSH key pair on each node:

```bash
ssh-keygen -t ed25519 -C "fyp-cluster" -f ~/.ssh/id_ed25519 -N ""
```

Add your own public key to your own `authorized_keys` so SSH into self works:

```bash
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
```

Distribute each node's key to the other two (node usernames: `asim` on stream-node, `spectre206` on ai-brain-node, `spectre` on gateway-node):

```bash
# From stream-node
ssh-copy-id spectre206@ai-brain-node
ssh-copy-id spectre@gateway-node

# From ai-brain-node
ssh-copy-id asim@stream-node
ssh-copy-id spectre@gateway-node

# From gateway-node
ssh-copy-id asim@stream-node
ssh-copy-id spectre206@ai-brain-node
```

Configure `~/.ssh/config` on each node for clean hostname-based SSH:

```
Host stream-node
    HostName stream-node
    User asim

Host ai-brain-node
    HostName ai-brain-node
    User spectre206

Host gateway-node
    HostName gateway-node
    User spectre
```

Verify all directions work without a password prompt:

```bash
ssh ai-brain-node "hostname && uptime"
ssh gateway-node "hostname && uptime"
ssh stream-node "hostname && uptime"
```

---

### 2.5 NTP Time Synchronisation

Install and enable chrony on all three nodes:

```bash
sudo apt update && sudo apt install -y chrony
sudo systemctl enable --now chrony
```

Verify offset is under 100ms:

```bash
chronyc tracking
```

Record the `System time` offset from all three nodes — reported in the paper.

---

## 3. Observability Stack

### 3.1 Node Exporter — All Nodes

```bash
sudo apt install -y prometheus-node-exporter
sudo systemctl enable --now prometheus-node-exporter
sudo ufw allow 9100/tcp
```

Verify:

```bash
curl http://localhost:9100/metrics | head -5
```

---

### 3.2 Prometheus — gateway-node ONLY

Install:

```bash
sudo apt install -y prometheus
sudo systemctl enable prometheus
```

Configure scrape targets — hostnames only, no IPs:

```bash
sudo nano /etc/prometheus/prometheus.yml
```

```yaml
scrape_configs:
  - job_name: 'fyp-cluster'
    static_configs:
      - targets:
          - 'stream-node:9100'
          - 'ai-brain-node:9100'
          - 'gateway-node:9100'
```

Restart:

```bash
sudo systemctl restart prometheus
```

Verify all targets are UP:

```bash
curl -s http://localhost:9090/api/v1/targets | grep -o '"health":"[^"]*"'
```

Access Prometheus at: **`http://gateway-node:9090`**

---

### 3.3 Grafana — gateway-node ONLY

```bash
sudo apt install -y apt-transport-https software-properties-common
sudo mkdir -p /etc/apt/keyrings
wget -q -O - https://apt.grafana.com/gpg.key | gpg --dearmor | \
  sudo tee /etc/apt/keyrings/grafana.gpg > /dev/null
echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] \
  https://apt.grafana.com stable main" | \
  sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt update && sudo apt install -y grafana
sudo systemctl enable --now grafana-server
```

Access Grafana at: **`http://gateway-node:3000`** — default login: `admin / admin`

Add Prometheus data source: **Configuration → Data Sources → Prometheus → URL: `http://localhost:9090` → Save & Test**

Import dashboard: **Dashboards → Import → ID `1860` → Load → Import**

---

## 4. Message Broker — RabbitMQ

### 4.1 Install and Configure — stream-node ONLY

```bash
sudo apt install -y rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management
sudo systemctl enable --now rabbitmq-server
```

Create admin user and open ports:

```bash
sudo rabbitmqctl add_user fypadmin fypadmin123
sudo rabbitmqctl set_user_tags fypadmin administrator
sudo rabbitmqctl set_permissions -p / fypadmin ".*" ".*" ".*"
sudo ufw allow 5672/tcp
sudo ufw allow 15672/tcp
```

Verify RabbitMQ is listening on all interfaces and not a specific IP:

```bash
sudo ss -tlnp | grep beam
```

Both ports `5672` and `15672` should show `[::]` or `0.0.0.0`. If you see a specific IP, add this to `/etc/rabbitmq/rabbitmq.conf`:

```
listeners.tcp.default = 5672
```

Access Management UI at: **`http://stream-node:15672`** — login: `fypadmin / fypadmin123`

---

### 4.2 Configure Dead Letter Exchange

```bash
# Create the Dead Letter Exchange
curl -u fypadmin:fypadmin123 -X PUT \
  http://stream-node:15672/api/exchanges/%2F/dlx \
  -H 'Content-Type: application/json' \
  -d '{"type":"direct","durable":true}'

# Create the dead letter queue
curl -u fypadmin:fypadmin123 -X PUT \
  http://stream-node:15672/api/queues/%2F/dead.letters \
  -H 'Content-Type: application/json' \
  -d '{"durable":true}'

# Create main anomaly queue with DLX fallback
curl -u fypadmin:fypadmin123 -X PUT \
  http://stream-node:15672/api/queues/%2F/anomaly.detected \
  -H 'Content-Type: application/json' \
  -d '{"durable":true,"arguments":{"x-dead-letter-exchange":"dlx"}}'
```

Verify from any node:

```bash
curl -u fypadmin:fypadmin123 http://stream-node:15672/api/healthchecks/node
# Expected: {"status":"ok"}
```

---

## 5. AI Stack — Ollama and ChromaDB

### 5.1 Ollama — ai-brain-node ONLY

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable ollama
sudo systemctl stop ollama
```

Configure Ollama to listen on all interfaces — required for hostname-based access from other nodes:

```bash
sudo nano /etc/systemd/system/ollama.service
```

Add under `[Service]`:

```ini
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_NUM_THREADS=4"
Environment="OLLAMA_KEEP_ALIVE=24h"
```

Reload and start:

```bash
sudo systemctl daemon-reload
sudo systemctl start ollama
sudo ufw allow 11434/tcp
```

Pull all models:

```bash
ollama pull qwen3:1.7b
ollama pull qwen3:0.6b
ollama pull deepseek-r1:1.5b
ollama pull phi4-mini
```

Verify cross-node hostname access from stream-node:

```bash
curl http://ai-brain-node:11434/api/tags
```

Should return JSON listing all models.

---

### 5.2 ChromaDB — ai-brain-node ONLY

```bash
pip install chromadb sentence-transformers --break-system-packages
```

Run smoke test:

```bash
python3 - <<'EOF'
import chromadb
client = chromadb.Client()
col = client.create_collection('fyp-test')
col.add(
    documents=['CPU spike detected on stream-node'],
    ids=['incident-001']
)
result = col.query(query_texts=['memory spike anomaly'], n_results=1)
print('ChromaDB OK:', result['documents'])
EOF
```

Expected: `ChromaDB OK: [['CPU spike detected on stream-node']]`

---

### 5.3 Python Dependencies — All Nodes

Core packages on all three nodes:

```bash
pip install pika pydantic prometheus-client python-dotenv requests \
  --break-system-packages
```

ML packages on stream-node only:

```bash
pip install scikit-learn numpy pandas scipy --break-system-packages
```

Django on gateway-node only:

```bash
pip install django djangorestframework channels --break-system-packages
```

---

## 6. Datasets

Download all three datasets to stream-node:

```bash
mkdir -p ~/fyp-datasets/{nab,loghub,kdd99}
```

**NAB — Numenta Anomaly Benchmark:**

```bash
cd ~/fyp-datasets/nab
git clone https://github.com/numenta/NAB.git .
```

**Loghub HDFS:**

```bash
cd ~/fyp-datasets/loghub
wget https://zenodo.org/record/8196385/files/HDFS_v1.zip
unzip HDFS_v1.zip
```

**KDD99:**

```bash
cd ~/fyp-datasets/kdd99
wget http://kdd.ics.uci.edu/databases/kddcup99/kddcup.data_10_percent.gz
gunzip kddcup.data_10_percent.gz
```

Verify all present:

```bash
du -sh ~/fyp-datasets/nab ~/fyp-datasets/loghub ~/fyp-datasets/kdd99
```

---

## 7. Hostname Verification

Run this complete sequence to confirm everything communicates by hostname with no IPs:

**From stream-node:**

```bash
# RabbitMQ health check
curl -u fypadmin:fypadmin123 http://stream-node:15672/api/healthchecks/node

# Ollama models on ai-brain-node
curl http://ai-brain-node:11434/api/tags

# Node Exporter on gateway-node
curl http://gateway-node:9100/metrics | head -3

# SSH to all three nodes
ssh ai-brain-node "hostname && uptime"
ssh gateway-node "hostname && uptime"
ssh stream-node "hostname && uptime"
```

**From gateway-node:**

```bash
# All Prometheus targets up
curl -s http://localhost:9090/api/v1/targets | grep -o '"health":"[^"]*"'
```

All commands should return valid responses. No IP addresses should appear in any connection string.

---

## 8. Moving to a New LAN

Follow this procedure in order when taking the cluster to a different network:

**Step 1 — Connect all nodes and find DHCP-assigned IPs:**

```bash
ip addr show | grep "inet " | grep -v 127
```

**Step 2 — Update `/etc/hosts` on all three nodes before starting any services:**

```bash
sudo nano /etc/hosts
```

Replace the three cluster lines:

```
<new-stream-node-ip>      stream-node
<new-ai-brain-node-ip>    ai-brain-node
<new-gateway-node-ip>     gateway-node
```

**Step 3 — Optionally update static IP assignment via nmtui** to match the new range.

**Step 4 — Verify hostname resolution:**

```bash
ping -c 2 ai-brain-node
ping -c 2 stream-node
ping -c 2 gateway-node
```

**Step 5 — Restart services:**

```bash
# On stream-node
sudo systemctl restart rabbitmq-server

# On ai-brain-node
sudo systemctl restart ollama

# On gateway-node
sudo systemctl restart prometheus
sudo systemctl restart grafana-server
```

**Step 6 — Run the verification sequence from Section 7.**

> ⚠️ **University WiFi warning:** Many university networks block device-to-device communication (client isolation). If `ping ai-brain-node` times out after updating `/etc/hosts`, client isolation is active — not a config error. Use a personal travel router connected to university ethernet as a workaround.

---

## 9. Validation Checklist

### Cluster Networking

- [ ] Hostname set correctly on all 3 nodes
- [ ] Static IP persisting after reboot on all 3 nodes
- [ ] `/etc/hosts` updated with cluster hostnames on all 3 nodes
- [ ] Hostname resolution working in all directions
- [ ] Passwordless SSH working in all 6 directions including self
- [ ] `~/.ssh/config` configured on all nodes
- [ ] NTP offset < 100ms on all nodes

### Observability

- [ ] Node Exporter running on all 3 nodes
- [ ] Prometheus running at `http://gateway-node:9090`
- [ ] All Prometheus targets showing UP
- [ ] Grafana running at `http://gateway-node:3000`
- [ ] Prometheus data source connected in Grafana
- [ ] Node Exporter dashboard (ID 1860) imported

### RabbitMQ

- [ ] RabbitMQ running on stream-node
- [ ] Listening on `[::]` not a specific IP — `sudo ss -tlnp | grep beam`
- [ ] Management UI accessible at `http://stream-node:15672`
- [ ] `fypadmin` user created with admin role
- [ ] DLX exchange created
- [ ] `dead.letters` queue created
- [ ] `anomaly.detected` queue with DLX argument created
- [ ] Cross-node health check passing from ai-brain-node and gateway-node

### Ollama + Models

- [ ] Ollama running on ai-brain-node
- [ ] `OLLAMA_HOST=0.0.0.0:11434` in service file
- [ ] `qwen3:1.7b` pulled
- [ ] `qwen3:0.6b` pulled
- [ ] Cross-node API accessible — `curl http://ai-brain-node:11434/api/tags` from stream-node

### ChromaDB

- [ ] ChromaDB installed on ai-brain-node
- [ ] Smoke test output matches expected result
- [ ] sentence-transformers installed

### Datasets

- [ ] NAB cloned on stream-node
- [ ] Loghub HDFS downloaded on stream-node
- [ ] KDD99 downloaded and gunzipped on stream-node

### Final Hostname Check

- [ ] All verification commands in Section 7 return valid responses with no IPs used
- [ ] All Prometheus targets UP by hostname from gateway-node

---

*Phase 0 complete → Phase 1: Stream Ingestion & Anomaly Detection begins 1 April 2026*