# layer1/seg/seg.py
# Synthetic Event Generator — v1.3 (config-driven, hostname-based)
# orchestrates data generation, noise injection, and RabbitMQ replay.
#
# CHANGELOG v1.2 -> v1.3:
#   - seg_config.json is now actually loaded (was previously dead/unused).
#   - RabbitMQ host defaults to the "stream-node" hostname, not a hardcoded IP.
#   - CLI flags override config values; config overrides built-in fallbacks.
#   - "nodes" list is now sourced from config (single source of truth,
#     previously duplicated separately in event_templates.py).
#   - Corpus generation rate (poisson_lambda_seconds) is now decoupled from
#     replay playback speed (--speed) — see _gen_timestamps()/replay() notes.
#   - base_timestamp from config is honored as the reproducible anchor for
#     generated corpora (was silently ignored in favor of datetime.now()).

import json
import time
import uuid
import csv
import argparse
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pika

from event_templates import EventTemplateFactory
from noise_injector import NoiseInjector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SEG] %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)

# Ground truth fields — stripped before pipeline ingestion
GT_FIELDS = {"ground_truth_label", "ground_truth_risk_tier", "ground_truth_action"}

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "seg_config.json"

# Built-in fallbacks — used ONLY if seg_config.json is missing or a key is
# absent from it. These intentionally mirror the config so behavior is
# identical either way, but the config is always preferred when present.
FALLBACK_EVENT_SPEC = {
    "NORMAL": 1000, "cpu_memory_spike": 200, "error_rate_surge": 200,
    "throughput_drop": 200, "auth_failure_flood": 200, "schema_drift": 150,
}
FALLBACK_SEVERITY_DIST = {"HIGH": 100, "MEDIUM": 60, "CRITICAL": 40}
FALLBACK_NODES = ["stream-node", "ai-brain-node", "gateway-node"]
FALLBACK_RABBITMQ = {
    "host": "stream-node", "port": 5672, "virtual_host": "fyp",
    "username": "fyp_user", "password": "fyp_pass_2026",
    "exchange": "fyp.events", "routing_key": "event.raw",
}


def load_config(path: Path) -> dict:
    """Loads seg_config.json. Raises a clear error if it's missing --
    SEG should not run silently on stale/duplicated defaults."""
    if not path.exists():
        raise FileNotFoundError(
            f"seg_config.json not found at {path}. "
            f"SEG requires this file — it is the single source of truth "
            f"for event counts, severity mix, RabbitMQ settings, and seed. "
            f"Pass --config to point at a different location."
        )
    with open(path) as f:
        cfg = json.load(f)
    log.info(f"Loaded config from {path}")
    return cfg


class SyntheticEventGenerator:

    def __init__(self, config: dict, replay_speed: float = None, host: str = None):
        self.config = config
        self.rng = np.random.default_rng(config.get("seed", 42))

        rmq = config.get("rabbitmq", FALLBACK_RABBITMQ)
        # Precedence: explicit CLI --host > config's rabbitmq.host > fallback hostname.
        # NOTE: this is a hostname ("stream-node"), resolved via /etc/hosts on
        # every node — never a hardcoded IP. See Phase 0 doc / README convention.
        self.host = host or rmq.get("host", FALLBACK_RABBITMQ["host"])
        self.port = rmq.get("port", FALLBACK_RABBITMQ["port"])
        self.vhost = rmq.get("virtual_host", FALLBACK_RABBITMQ["virtual_host"])
        self.username = rmq.get("username", FALLBACK_RABBITMQ["username"])
        self.password = rmq.get("password", FALLBACK_RABBITMQ["password"])
        self.exchange = rmq.get("exchange", FALLBACK_RABBITMQ["exchange"])
        self.routing_key = rmq.get("routing_key", FALLBACK_RABBITMQ["routing_key"])

        self.event_spec = config.get("event_counts", FALLBACK_EVENT_SPEC)
        self.severity_dist_map = config.get("severity_distribution", {})
        self.nodes = config.get("nodes", FALLBACK_NODES)

        # Corpus generation rate: governed by poisson_lambda_seconds ONLY.
        # This is a property of the *dataset* and must stay fixed regardless
        # of how fast it's later replayed — see _gen_timestamps().
        self.gen_interval = float(config.get("poisson_lambda_seconds", 1.0))

        # Replay playback rate: an independent knob, CLI > config > default 1.0.
        # Only affects how fast an already-generated corpus is published to
        # RabbitMQ during `--mode replay` — never affects corpus content itself.
        self.replay_speed = replay_speed if replay_speed is not None \
            else float(config.get("replay_speed", 1.0))

        base_ts = config.get("base_timestamp")
        self.base_timestamp = (
            datetime.fromisoformat(base_ts.replace("Z", "+00:00"))
            if base_ts else datetime.now(timezone.utc).replace(microsecond=0)
        )

        self.templates = EventTemplateFactory(self.rng, nodes=self.nodes)
        self.noise = NoiseInjector(self.rng)
        self.labels = {}
        self._conn = None
        self._ch = None

    def _connect(self):
        """Lazy connect — only needed for --mode replay, not for generate."""
        if self._conn is not None:
            return
        self._conn = pika.BlockingConnection(pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.vhost,
            credentials=pika.PlainCredentials(self.username, self.password),
        ))
        self._ch = self._conn.channel()
        log.info(f"Connected to RabbitMQ at {self.host}:{self.port} [vhost: {self.vhost}]")

    def _strip_ground_truth(self, event: dict) -> dict:
        gt = {k: event.pop(k, None) for k in GT_FIELDS}
        self.labels[event["event_id"]] = gt
        return event

    def _gen_timestamps(self, n, start):
        """Sequential, exponentially-spaced timestamps (Poisson process),
        anchored at a fixed base_timestamp for full corpus reproducibility."""
        ts, out = start, []
        for _ in range(n):
            out.append(ts.isoformat())
            ts += timedelta(seconds=max(0.01, self.rng.exponential(self.gen_interval)))
        return out

    def generate_corpus(self) -> list:
        events = []
        for _ in range(self.event_spec["NORMAL"]):
            events.append(self.templates.normal(str(self.rng.choice(self.nodes))))

        for atype in ("cpu_memory_spike", "error_rate_surge", "throughput_drop", "auth_failure_flood"):
            dist = self.severity_dist_map.get(atype, FALLBACK_SEVERITY_DIST)
            for sev, cnt in dist.items():
                for _ in range(cnt):
                    events.append(self.templates.anomaly(atype, sev, str(self.rng.choice(self.nodes))))

        schema_dist = self.severity_dist_map.get("schema_drift", {})
        for subtype, spec in schema_dist.items():
            for _ in range(spec["count"]):
                events.append(self.templates.schema_drift(subtype, str(self.rng.choice(self.nodes))))

        self.rng.shuffle(events)

        ts = self._gen_timestamps(len(events), self.base_timestamp)
        for ev, t in zip(events, ts):
            ev["event_id"] = str(uuid.uuid4())
            ev["timestamp"] = t
            self.noise.apply(ev)

        return events

    def save_corpus(self, events: list, output_dir: str = None):
        """
        Saves two files (names/dir come from config unless overridden):
          <corpus_filename> — one stripped event per line (no ground truth)
          <labels_filename> — event_id + ground truth fields
        """
        out = Path(output_dir or self.config.get("output_dir", "evaluation/"))
        out.mkdir(parents=True, exist_ok=True)

        jsonl_path = out / self.config.get("corpus_filename", "events_1950.jsonl")
        csv_path = out / self.config.get("labels_filename", "labels.csv")

        with open(jsonl_path, "w") as jf, open(csv_path, "w", newline="") as cf:
            writer = csv.DictWriter(cf, fieldnames=[
                "event_id", "ground_truth_label",
                "ground_truth_risk_tier", "ground_truth_action"
            ])
            writer.writeheader()

            for ev in events:
                clean = self._strip_ground_truth(dict(ev))
                jf.write(json.dumps(clean) + "\n")
                writer.writerow({
                    "event_id": clean["event_id"],
                    **self.labels[clean["event_id"]]
                })

        log.info(f"Corpus saved to {jsonl_path}")
        log.info(f"Labels saved to {csv_path}")
        return jsonl_path, csv_path

    def replay(self, events_path):
        self._connect()
        lines = open(events_path).readlines()
        total_events = len(lines)
        # Playback pacing is governed by replay_speed alone; corpus content/
        # timestamps were already fixed at generation time and are untouched.
        sleep_interval = self.gen_interval / self.replay_speed if self.replay_speed else self.gen_interval

        log.info(
            f"Replaying {total_events} events to exchange '{self.exchange}' "
            f"(routing key: '{self.routing_key}') at {self.replay_speed}x speed"
        )

        for i, line in enumerate(lines, 1):
            ev = json.loads(line.strip())

            headers = {
                "x-event-type": ev.get("anomaly_type", "NORMAL"),
                "x-severity": ev.get("severity", "N/A"),
                "x-node": ev.get("node", "unknown"),
            }

            self._ch.basic_publish(
                exchange=self.exchange,
                routing_key=self.routing_key,
                body=json.dumps(ev),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                    headers=headers,
                ),
            )

            if i % 100 == 0 or i == total_events:
                log.info(f"Progress: Published {i}/{total_events} events...")

            time.sleep(max(0, sleep_interval))

        log.info("Replay successfully finished.")
        self._conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["generate", "replay"], default="generate")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG_PATH),
                     help="Path to seg_config.json (default: config/seg_config.json)")
    ap.add_argument("--speed", type=float, default=None,
                     help="Replay playback speed multiplier. Overrides config's replay_speed. "
                          "Only affects --mode replay pacing, never corpus content.")
    ap.add_argument("--host", default=None,
                     help="RabbitMQ hostname. Overrides config's rabbitmq.host. "
                          "Use a hostname (e.g. stream-node), never a hardcoded IP.")
    ap.add_argument("--output", default=None, help="Output dir. Overrides config's output_dir.")
    ap.add_argument("--input", default=None, help="Input corpus path for --mode replay.")

    a = ap.parse_args()

    cfg = load_config(Path(a.config))
    seg = SyntheticEventGenerator(cfg, replay_speed=a.speed, host=a.host)

    if a.mode == "generate":
        seg.save_corpus(seg.generate_corpus(), a.output)
    else:
        default_input = Path(cfg.get("output_dir", "evaluation/")) / cfg.get("corpus_filename", "events_1950.jsonl")
        seg.replay(a.input or str(default_input))