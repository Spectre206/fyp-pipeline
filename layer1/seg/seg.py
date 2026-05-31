# layer1/seg/seg.py
# Synthetic Event Generator — v1.2 Implementation
# orchestrates data generation, noise injection, and RabbitMQ replay.

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

class SyntheticEventGenerator:
    EVENT_SPEC = {
        "NORMAL": 1000,
        "cpu_memory_spike": 200,
        "error_rate_surge": 200,
        "throughput_drop": 200,
        "auth_failure_flood": 200,
        "schema_drift": 150,
    }
    SEVERITY_DIST = {"HIGH": 100, "MEDIUM": 60, "CRITICAL": 40}
    NODES = ["stream-node", "ai-brain-node", "gateway-node"]

    def __init__(self, replay_speed=1.0, host="192.168.18.101"):
        self.rng = np.random.default_rng(42)
        self.interval = 1.0 / replay_speed
        self.templates = EventTemplateFactory(self.rng)
        self.noise = NoiseInjector(self.rng)
        self.labels = {} 

        # V1.2: Connect to the 'fyp' vhost and use 'pipeline.events' exchange
        self._conn = pika.BlockingConnection(pika.ConnectionParameters(
            host=host,
            virtual_host="fyp",
            credentials=pika.PlainCredentials("fyp_user", "fyp_pass_2026")
        ))
        self._ch = self._conn.channel()
        log.info(f"Connected to RabbitMQ at {host} [vhost: fyp]")

    def _strip_ground_truth(self, event: dict) -> dict:
        gt = {k: event.pop(k, None) for k in GT_FIELDS}
        self.labels[event["event_id"]] = gt
        return event

    def generate_corpus(self) -> list:
        events = []
        # Generate NORMAL and ANOMALY events...
        for _ in range(self.EVENT_SPEC["NORMAL"]):
            events.append(self.templates.normal(str(self.rng.choice(self.NODES))))
            
        for atype in ("cpu_memory_spike", "error_rate_surge", "throughput_drop", "auth_failure_flood"):
            for sev, cnt in self.SEVERITY_DIST.items():
                for _ in range(cnt):
                    events.append(self.templates.anomaly(atype, sev, str(self.rng.choice(self.NODES))))

        for subtype in ("missing_field", "type_mutation", "value_shift"):
            for _ in range(50):
                events.append(self.templates.schema_drift(subtype, str(self.rng.choice(self.NODES))))

        self.rng.shuffle(events)
        
        # Apply temporal and metric noise
        for ev in events:
            ev["event_id"] = str(uuid.uuid4())
            self.noise.apply(ev)
        return events

    # ── Corpus and Labels writer ───────────────────────────────────────
    def save_corpus(self, events: list, path: str):
        """
        Saves two files:
          events_1950.jsonl — one stripped event per line (no ground truth)
          labels.csv        — event_id + ground truth fields
        """
        out = Path(path)
        out.mkdir(parents=True, exist_ok=True)

        jsonl_path = out / "events_1950.jsonl"
        csv_path   = out / "labels.csv"

        with open(jsonl_path, "w") as jf, \
             open(csv_path, "w", newline="") as cf:

            writer = csv.DictWriter(cf, fieldnames=[
                "event_id", "ground_truth_label", 
                "ground_truth_risk_tier", "ground_truth_action"
            ])
            writer.writeheader()

            for ev in events:
                # 1. Strip ground truth and store in self.labels
                clean = self._strip_ground_truth(dict(ev))
                
                # 2. Write the cleaned event to JSONL
                jf.write(json.dumps(clean) + "\n")
                
                # 3. Write the labels to CSV using the event_id
                writer.writerow({
                    "event_id": clean["event_id"],
                    **self.labels[clean["event_id"]]
                })

        log.info(f"Corpus saved to {jsonl_path}")
        log.info(f"Labels saved to {csv_path}")

    def replay(self, events_path):
        lines = open(events_path).readlines()
        total_events = len(lines)
        # Updated log message to match the new exchange
        log.info(f"Replaying {total_events} events to exchange: raw.events") 
        
        for i, line in enumerate(lines, 1): # Added progress tracker
            ev = json.loads(line.strip())
            
            headers = {
                "x-event-type": ev.get("anomaly_type", "NORMAL"),
                "x-severity": ev.get("severity", "N/A"),
                "x-node": ev.get("node", "unknown")
            }
            
            self._ch.basic_publish(
                exchange="raw.events",  # <--- CRITICAL V1.2 FIX
                routing_key="anomaly.raw",
                body=json.dumps(ev),
                properties=pika.BasicProperties(
                    delivery_mode=2, 
                    content_type="application/json",
                    headers=headers
                )
            )
            
            # Print an update every 100 events
            if i % 100 == 0 or i == total_events:
                log.info(f"Progress: Published {i}/{total_events} events...")
                
            time.sleep(max(0, self.interval))
            
        log.info("Replay successfully finished.")
        self._conn.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["generate", "replay"], default="generate")
    ap.add_argument("--speed", type=float, default=1.0)
    
    # Fixed defaults so it saves locally in the fyp-pipeline folder!
    ap.add_argument("--output", default="evaluation/")
    ap.add_argument("--input", default="evaluation/events_1950.jsonl")
    
    a = ap.parse_args()

    seg = SyntheticEventGenerator(replay_speed=a.speed) # Passed speed into the class!
    if a.mode == "generate":
        seg.save_corpus(seg.generate_corpus(), a.output)
    else:
        seg.replay(a.input)