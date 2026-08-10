"""Auto-Execution Engine — consumes auto.execute, simulates remediation."""
import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog
from datetime import datetime, timezone

from rabbitmq.connection import get_connection, publish
from sqlite_logger.logger import init_db, write_decision

log = structlog.get_logger()

class AutoExecutor:
    def __init__(self):
        init_db()
        self.conn = get_connection()
        self.ch = self.conn.channel()
        log.info("auto_executor_started")

    def execute_actions(self, actions: list) -> tuple:
        """
        Simulate remediation. Returns (outcome_type, resolution_time_ms).
        All successes unless actions list is empty.
        """
        if not actions:
            return ("AUTO_EXECUTE_FAILURE", 0)
        time.sleep(0.5)  # Simulate execution time
        return ("AUTO_EXECUTE_SUCCESS", 500)

    def on_message(self, ch, method, props, body):
        try:
            policy = json.loads(body)
            event_id = policy.get("event_id", "unknown")
            chain = policy.get("full_reasoning_chain", {})
            triage = chain.get("triage_result", {})
            strategy = chain.get("strategy_result", {})
            llm = strategy.get("llm_response", {})
            ev = triage.get("original_event", {})

            # Extract the 3 recommended actions from LLM output
            actions = llm.get("recommended_actions", [])

            # Simulate execution
            outcome_type, resolution_ms = self.execute_actions(actions)

            # Write to SQLite
            write_decision({
                "event_id": event_id,
                "anomaly_type": triage.get("anomaly_type"),
                "severity": triage.get("severity"),
                "affected_component": ev.get("affected_component"),
                "node": ev.get("node"),
                "routing_reason": policy.get("routing_reason"),
                "risk_tier_from_llm": llm.get("risk_tier"),
                "confidence_from_llm": llm.get("confidence"),
                "decision_type": "AUTO_EXECUTE",
                "time_in_queue_seconds": 0.0,
                "original_actions": actions,
                "final_actions": actions,
                "auto_execute_outcome": outcome_type,
            })

            # Publish outcome.feedback for Learning Agent
            feedback = {
                "event_id": event_id,
                "outcome_type": outcome_type,
                "actual_actions_taken": actions,
                "operator_notes": "auto-executed",
                "resolution_time_ms": resolution_ms,
                "full_policy_result": policy,
            }
            publish("outcome.feedback", json.dumps(feedback))

            ch.basic_ack(method.delivery_tag)
            log.info("auto_executed", event_id=event_id, outcome=outcome_type)

        except Exception as e:
            log.error("auto_executor_error", error=str(e))
            ch.basic_nack(method.delivery_tag, requeue=False)

    def run(self):
        self.ch.basic_qos(prefetch_count=1)
        self.ch.basic_consume("auto.execute", self.on_message)
        log.info("auto_executor_consuming", queue="auto.execute")
        self.ch.start_consuming()

if __name__ == "__main__":
    AutoExecutor().run()
