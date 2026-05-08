import json
import time
import requests
import csv
import os
from datetime import datetime

PROMPT_FILE = "../prompts/stricter_prompts.json"
OLLAMA_URL  = "http://localhost:11434/api/generate"
MODEL       = "phi4-mini:latest"

RAW_DIR     = "../results/raw_responses"
SUMMARY_DIR = "../results/summary"

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(SUMMARY_DIR, exist_ok=True)

with open(PROMPT_FILE, "r") as f:
    config = json.load(f)

SYSTEM  = config["system_prompt"]
PROMPTS = config["prompts"]
VARIANT = config["variant"]

RUN_TAG = f"{MODEL.replace(':','-')}_{VARIANT}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

RAW_FILE = os.path.join(RAW_DIR, f"{RUN_TAG}_raw.csv")
CSV_FILE = os.path.join(SUMMARY_DIR, f"{RUN_TAG}_summary.csv")

REQUIRED_FIELDS = {
    "anomaly_type",
    "severity",
    "affected_component",
    "recommended_actions",
    "confidence",
    "risk_tier",
    "reasoning"
}

results = []

for entry in PROMPTS:
    pid = entry["id"]
    prompt_text = entry["text"]

    start = time.time()

    resp = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt_text,
        "system": SYSTEM,
        "stream": False,
        "options": {
            "num_ctx": 2048,
            "num_predict": 300
        }
    })

    elapsed = round(time.time() - start, 2)

    rj = resp.json()
    raw = rj.get("response", "")

    eval_count = rj.get("eval_count", 0)
    eval_duration = rj.get("eval_duration", 0)

    tps = round(eval_count / (eval_duration / 1e9), 2) if eval_duration > 0 else 0

    try:
        parsed = json.loads(raw.strip())
        valid_json = True
    except:
        parsed = {}
        valid_json = False

    schema_valid = valid_json and REQUIRED_FIELDS.issubset(parsed.keys())

    row = {
        "prompt_id": pid,
        "valid_json": valid_json,
        "schema_valid": schema_valid,
        "confidence": parsed.get("confidence", "MISSING"),
        "response_time_s": elapsed,
        "tokens_per_s": tps,
        "raw_response": raw
    }

    results.append(row)

    print(f"{pid}: json={valid_json} schema={schema_valid} {elapsed}s {tps} tok/s")

with open(RAW_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

avg_resp = round(sum(r["response_time_s"] for r in results) / len(results), 2)
avg_tps  = round(sum(r["tokens_per_s"] for r in results) / len(results), 2)

with open(CSV_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["model","variant","avg_response_time_s","avg_tokens_per_s"])
    writer.writerow([MODEL, VARIANT, avg_resp, avg_tps])

print("\nSaved:")
print(RAW_FILE)
print(CSV_FILE)