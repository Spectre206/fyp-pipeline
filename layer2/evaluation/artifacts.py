"""Best-effort, opt-in JSONL artifacts for a named live evaluation run."""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


def record(stage: str, data: dict) -> None:
    run_id = os.getenv("LAYER2_EVALUATION_RUN_ID")
    if not run_id or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id):
        return
    root = Path(os.getenv("LAYER2_EVALUATION_DIR", Path(__file__).resolve().parent / "results"))
    try:
        directory = root / run_id
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / f"{stage}.jsonl").open("a", encoding="utf-8") as output:
            output.write(json.dumps({"recorded_at": datetime.now(timezone.utc).isoformat(), **data}, default=str) + "\n")
    except Exception:
        # Evaluation capture must never affect live decisions.
        return
