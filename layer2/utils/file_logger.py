"""Shared append-only JSONL logger for Layer 2 agents."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

# Base directory for logs = layer2/logs
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"

def append_log(filename: str, data: dict) -> None:
    """
    Append a JSON line to layer2/logs/<filename>.

    The logger is intentionally simple:
      - Creates the logs directory if needed.
      - Appends one JSON object per line.
      - Does not raise on error; it logs to stderr and continues so the
        agent never crashes because of a logging problem.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / filename

    record = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        **data,
    }

    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except Exception as e:
        # Do not crash the agent because of logging failure
        print(f"[file_logger] WARN failed to write {filename}: {e}")