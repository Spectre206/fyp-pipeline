"""
ADM Runner — Anomaly Detection Module Orchestrator (v1.3)

v1.3 CHANGELOG:
    - Config-driven: loads adm_config.json (hostname-based, no hardcoded IP).
    - Prometheus removed (only Fusion Engine is scraped in Layer 1).
    - Handles FeatureStore's None return during calibration:
      events for still-warming components are consumed but NOT fanned out.
    - Normal events are NEVER discarded — they are fanned out like any other
      event, and the Fusion Engine later decides if they are anomalies.

Flow:
    validated.event (RabbitMQ)
        → ADMRunner.on_message()
            → FeatureStore.process()  [in-process, may return None]
            → if enriched is None: skip fanout (still calibrating)
            → else: basic_publish(detection.fanout, routing_key='')
                → detect.cpu / detect.error / detect.throughput /
                  detect.auth / detect.schema all receive it
                → each detector publishes result to fusion.results
                    → Fusion Engine → anomaly.detected
"""
# layer1/adm/adm_runner.py

import json
import logging
import sys
from pathlib import Path

import pika
import structlog

# Feature Store lives one directory up
sys.path.insert(0, str(Path(__file__).parent.parent / 'feature_store'))
from feature_store import FeatureStore

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ADM_RUNNER] %(levelname)s %(message)s"
)
log = structlog.get_logger()

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "adm_config.json"

FALLBACK_RABBITMQ = {
    "host": "stream-node",
    "port": 5672,
    "virtual_host": "fyp",
    "username": "fyp_user",
    "password": "fyp_pass_2026",
    "input_queue": "validated.event",
    "fanout_exchange": "detection.fanout",
}


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"adm_config.json not found at {path}. "
            f"The ADM Runner requires this file. "
            f"Pass a different path via ADMRunner(config_path=...)."
        )
    with open(path) as f:
        cfg = json.load(f)
    log.info(f"Loaded config from {path}")
    return cfg


class ADMRunner:
    """
    v1.3 ADM Runner — fanout exchange, config-driven, no metrics.

    Consumes validated events from validated.event queue.
    Enriches each event via FeatureStore (in‑process).
    Publishes enriched events ONCE to detection.fanout exchange.

    Because detection.fanout is a FANOUT exchange:
      - routing key is ignored
      - all 5 bound detect.* queues receive the message automatically
    """

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH):
        self.config = load_config(config_path)
        rmq = self.config.get("rabbitmq", FALLBACK_RABBITMQ)

        self.host = rmq.get("host", FALLBACK_RABBITMQ["host"])
        self.port = rmq.get("port", FALLBACK_RABBITMQ["port"])
        self.vhost = rmq.get("virtual_host", FALLBACK_RABBITMQ["virtual_host"])
        self.username = rmq.get("username", FALLBACK_RABBITMQ["username"])
        self.password = rmq.get("password", FALLBACK_RABBITMQ["password"])
        self.input_queue = rmq.get("input_queue", FALLBACK_RABBITMQ["input_queue"])
        self.fanout_exchange = rmq.get("fanout_exchange", FALLBACK_RABBITMQ["fanout_exchange"])

        # Feature Store (stateful, in‑process)
        self.feature_store = FeatureStore(calibration_n=100)
        log.info("feature_store_initialised")

        # RabbitMQ connection
        params = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.vhost,
            credentials=pika.PlainCredentials(self.username, self.password),
            heartbeat=60,
            blocked_connection_timeout=30,
        )
        self.conn = pika.BlockingConnection(params)
        self.ch = self.conn.channel()

        log.info("adm_runner_started",
                 host=self.host,
                 input_queue=self.input_queue,
                 fanout_exchange=self.fanout_exchange)

    def on_message(self, ch, method, props, body):
        """
        Process one validated event:
        1. Parse JSON.
        2. FeatureStore.process() → may return None during calibration.
        3. If enriched is None → ack (event consumed, calibration updated, but not fanned out).
        4. Else → publish once to detection.fanout (all 5 detect.* queues receive it).
        """
        # Step 1: Parse JSON
        try:
            event = json.loads(body)
        except json.JSONDecodeError as exc:
            log.error("json_parse_error", error=str(exc))
            ch.basic_nack(method.delivery_tag, requeue=False)
            return

        event_id = event.get("event_id", "MISSING")
        atype = event.get("anomaly_type", "UNKNOWN")

        # Step 2: Feature Store enrichment
        try:
            enriched = self.feature_store.process(event)
        except Exception as exc:
            log.error("feature_store_error", event_id=event_id, error=str(exc))
            # Degrade gracefully: publish with empty features
            enriched = dict(event)
            enriched["feature_vector"] = {}
            enriched["calibrated"] = False
            enriched["calibration_events_left"] = 100
            enriched["window_depth"] = 0

        # Step 2b: Handle calibration gate
        if enriched is None:
            log.debug("event_withheld_calibrating",
                      event_id=event_id,
                      anomaly_type=atype)
            ch.basic_ack(method.delivery_tag)
            return

        # Step 3: Publish ONCE to detection.fanout
        try:
            self.ch.basic_publish(
                exchange=self.fanout_exchange,
                routing_key="",               # fanout ignores routing key
                body=json.dumps(enriched, default=str).encode("utf-8"),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json"
                )
            )
            log.info("event_fanned_out",
                     event_id=event_id,
                     anomaly_type=atype,
                     window_depth=enriched.get("window_depth", 0),
                     calibrated=enriched.get("calibrated", False),
                     features_count=len(enriched.get("feature_vector", {})))

        except Exception as exc:
            log.error("fanout_publish_error",
                      event_id=event_id, error=str(exc))
            ch.basic_nack(method.delivery_tag, requeue=True)
            return

        ch.basic_ack(method.delivery_tag)

    def run(self):
        self.ch.basic_qos(prefetch_count=1)    # stateful Feature Store, order matters
        self.ch.basic_consume(
            queue=self.input_queue,
            on_message_callback=self.on_message
        )
        log.info("adm_consuming", queue=self.input_queue, exchange=self.fanout_exchange)
        try:
            self.ch.start_consuming()
        except KeyboardInterrupt:
            log.info("adm_runner_stopping")
            self.ch.stop_consuming()
        finally:
            if self.conn and not self.conn.is_closed:
                self.conn.close()
                log.info("adm_runner_connection_closed")


if __name__ == "__main__":
    ADMRunner().run()