"""SQLite Decision Logger — shared write interface for Auto-Executor and Django."""
import sqlite3
import json
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "decisions.db")

def _get_conn():
    """Return a thread-local SQLite connection with WAL mode."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    """Create the decisions table if it doesn't exist."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            anomaly_type TEXT,
            severity TEXT,
            affected_component TEXT,
            node TEXT,
            routing_reason TEXT,
            risk_tier_from_llm TEXT,
            confidence_from_llm REAL,
            decision_type TEXT NOT NULL,
            decision_timestamp TEXT NOT NULL,
            time_in_queue_seconds REAL,
            original_actions TEXT,
            final_actions TEXT,
            operator_notes TEXT,
            auto_execute_outcome TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()

def write_decision(data: dict):
    """Write one decision row. Accepts a dict with keys matching the schema."""
    conn = _get_conn()
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO decisions (
            event_id, anomaly_type, severity, affected_component, node,
            routing_reason, risk_tier_from_llm, confidence_from_llm,
            decision_type, decision_timestamp, time_in_queue_seconds,
            original_actions, final_actions, operator_notes,
            auto_execute_outcome, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("event_id"),
        data.get("anomaly_type"),
        data.get("severity"),
        data.get("affected_component"),
        data.get("node"),
        data.get("routing_reason"),
        data.get("risk_tier_from_llm"),
        data.get("confidence_from_llm"),
        data.get("decision_type"),
        ts,
        data.get("time_in_queue_seconds"),
        json.dumps(data.get("original_actions", [])),
        json.dumps(data.get("final_actions", [])),
        data.get("operator_notes", ""),
        data.get("auto_execute_outcome"),
        ts
    ))
    conn.commit()
    conn.close()
