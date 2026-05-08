import json
import time
import requests
import csv
import os
from datetime import datetime

# ─────────────────────────────────────────────
#  CONFIGURATION — change PROMPT_FILE to switch
#  between simple / medium / strict variants
# ─────────────────────────────────────────────
PROMPT_FILE  = "../prompts/simple_prompts.json"   # ← swap to medium or strict
OLLAMA_URL   = "http://localhost:11434/api/generate"
MODEL        = "deepseek-r1:1.5b"

# ─────────────────────────────────────────────
#  OUTPUT PATHS
# ─────────────────────────────────────────────
RAW_DIR      = "../results/raw_responses"
SUMMARY_DIR  = "../results/summary"
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(SUMMARY_DIR, exist_ok=True)

# ─────────────────────────────────────────────
#  LOAD PROMPT FILE
# ─────────────────────────────────────────────
with open(PROMPT_FILE, "r") as f:
    config = json.load(f)

SYSTEM   = config["system_prompt"]
PROMPTS  = config["prompts"]
VARIANT  = config["variant"]   # simple | medium | strict

RUN_TAG  = f"{MODEL.replace(':', '-')}_{VARIANT}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
RAW_FILE = os.path.join(RAW_DIR,     f"{RUN_TAG}_raw.jsonl")
CSV_FILE = os.path.join(SUMMARY_DIR, f"{RUN_TAG}_summary.csv")

REQUIRED_FIELDS = {
    "anomaly_type", "severity", "affected_component",
    "recommended_actions", "confidence", "risk_tier", "reasoning"
}

VALID_SEVERITIES  = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_RISK_TIERS  = {"LOW", "HIGH"}

RISK_TIER_MAP = {
    "LOW":      "LOW",
    "MEDIUM":   "LOW",
    "HIGH":     "HIGH",
    "CRITICAL": "HIGH"
}

# ─────────────────────────────────────────────
#  VALIDATION HELPERS
# ─────────────────────────────────────────────
def validate(parsed: dict, expected_severity: str) -> dict:
    issues = []

    missing = REQUIRED_FIELDS - parsed.keys()
    if missing:
        issues.append(f"missing_fields:{','.join(sorted(missing))}")

    extra = parsed.keys() - REQUIRED_FIELDS
    if extra:
        issues.append(f"extra_fields:{','.join(sorted(extra))}")

    sev = parsed.get("severity", "")
    if sev not in VALID_SEVERITIES:
        issues.append(f"bad_severity:{sev}")

    tier = parsed.get("risk_tier", "")
    if tier not in VALID_RISK_TIERS:
        issues.append(f"bad_risk_tier:{tier}")
    elif sev in RISK_TIER_MAP and tier != RISK_TIER_MAP[sev]:
        issues.append(f"tier_mismatch:expected={RISK_TIER_MAP[sev]},got={tier}")

    actions = parsed.get("recommended_actions", [])
    if not isinstance(actions, list) or len(actions) != 3:
        issues.append(f"bad_actions_count:{len(actions) if isinstance(actions, list) else 'not_list'}")

    conf = parsed.get("confidence", None)
    if conf is None or not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
        issues.append(f"bad_confidence:{conf}")

    return {
        "schema_valid": len(issues) == 0,
        "issues": "; ".join(issues) if issues else "none"
    }

# ─────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────
results = []

print(f"\n{'═'*62}")
print(f"  Model   : {MODEL}")
print(f"  Variant : {VARIANT.upper()}")
print(f"  Prompts : {len(PROMPTS)}")
print(f"  Run Tag : {RUN_TAG}")
print(f"{'═'*62}\n")

for entry in PROMPTS:
    pid      = entry["id"]
    category = entry["category"]
    expected_sev = entry["severity"]
    prompt_text  = entry["text"]

    payload = {
        "model":  MODEL,
        "prompt": prompt_text,
        "system": SYSTEM,
        "stream": False,
        "options": {
            "num_ctx":     2048,
            "num_predict": 400
        }
    }

    start = time.time()
    resp  = requests.post(OLLAMA_URL, json=payload)
    elapsed = time.time() - start

    resp_json = resp.json()
    raw       = resp_json.get("response", "")

    # ── Token metrics from Ollama response ──────────────
    eval_count    = resp_json.get("eval_count", 0)           # tokens generated
    eval_duration = resp_json.get("eval_duration", 0)        # nanoseconds
    tokens_per_s  = round(eval_count / (eval_duration / 1e9), 2) if eval_duration > 0 else 0.0

    # ── JSON parse ──────────────────────────────────────
    try:
        parsed    = json.loads(raw.strip())
        json_valid = True
    except json.JSONDecodeError:
        parsed    = {}
        json_valid = False

    # ── Schema validation ────────────────────────────────
    val = validate(parsed, expected_sev) if json_valid else {
        "schema_valid": False,
        "issues": "json_parse_failed"
    }

    row = {
        "prompt_id":       pid,
        "category":        category,
        "expected_sev":    expected_sev,
        "json_valid":      json_valid,
        "schema_valid":    val["schema_valid"],
        "issues":          val["issues"],
        "risk_tier":       parsed.get("risk_tier",  "MISSING"),
        "severity_out":    parsed.get("severity",   "MISSING"),
        "confidence":      parsed.get("confidence", "MISSING"),
        "response_time_s": round(elapsed, 2),
        "eval_tokens":     eval_count,
        "tokens_per_s":    tokens_per_s,
    }

    results.append(row)

    # ── Write raw response to JSONL ──────────────────────
    with open(RAW_FILE, "a") as rf:
        rf.write(json.dumps({
            "prompt_id":   pid,
            "category":    category,
            "prompt_text": prompt_text,
            "raw_response": raw,
            "parsed":      parsed,
            "metrics":     {
                "response_time_s": row["response_time_s"],
                "eval_tokens":     eval_count,
                "tokens_per_s":    tokens_per_s
            }
        }) + "\n")

    status = "✓" if val["schema_valid"] else "✗"
    print(
        f"  {status} {pid} [{category[:20]:<20}] "
        f"tier={row['risk_tier']:<4}  "
        f"conf={str(row['confidence']):<4}  "
        f"{elapsed:.1f}s  "
        f"{tokens_per_s:.1f} tok/s"
    )

# ─────────────────────────────────────────────
#  AGGREGATE STATS
# ─────────────────────────────────────────────
times   = [r["response_time_s"] for r in results]
tps     = [r["tokens_per_s"]    for r in results if r["tokens_per_s"] > 0]

fastest_row = min(results, key=lambda r: r["response_time_s"])
slowest_row = max(results, key=lambda r: r["response_time_s"])
fastest_tps = max(results, key=lambda r: r["tokens_per_s"])
slowest_tps = min(results, key=lambda r: r["tokens_per_s"] if r["tokens_per_s"] > 0 else float("inf"))

json_pass    = sum(1 for r in results if r["json_valid"])
schema_pass  = sum(1 for r in results if r["schema_valid"])
tier_low     = sum(1 for r in results if r["risk_tier"] == "LOW")
tier_high    = sum(1 for r in results if r["risk_tier"] == "HIGH")
total        = len(results)

summary_stats = {
    "run_tag":              RUN_TAG,
    "model":                MODEL,
    "variant":              VARIANT,
    "total_prompts":        total,
    "json_valid_count":     json_pass,
    "json_valid_pct":       round(json_pass  / total * 100, 1),
    "schema_valid_count":   schema_pass,
    "schema_valid_pct":     round(schema_pass / total * 100, 1),
    "risk_tier_LOW_count":  tier_low,
    "risk_tier_HIGH_count": tier_high,
    "avg_response_time_s":  round(sum(times) / len(times), 2),
    "fastest_response_s":   fastest_row["response_time_s"],
    "fastest_prompt_id":    fastest_row["prompt_id"],
    "slowest_response_s":   slowest_row["response_time_s"],
    "slowest_prompt_id":    slowest_row["prompt_id"],
    "avg_tokens_per_s":     round(sum(tps) / len(tps), 2) if tps else 0,
    "fastest_tokens_per_s": fastest_tps["tokens_per_s"],
    "fastest_tps_prompt":   fastest_tps["prompt_id"],
    "slowest_tokens_per_s": slowest_tps["tokens_per_s"],
    "slowest_tps_prompt":   slowest_tps["prompt_id"],
}

print(f"\n{'═'*62}")
print(f"  RESULTS SUMMARY — {MODEL} / {VARIANT.upper()}")
print(f"{'═'*62}")
print(f"  JSON valid      : {json_pass}/{total}  ({summary_stats['json_valid_pct']}%)")
print(f"  Schema valid    : {schema_pass}/{total}  ({summary_stats['schema_valid_pct']}%)")
print(f"  Risk tier LOW   : {tier_low}   |   HIGH : {tier_high}")
print(f"  Avg resp time   : {summary_stats['avg_response_time_s']}s")
print(f"  Fastest resp    : {fastest_row['response_time_s']}s  ({fastest_row['prompt_id']})")
print(f"  Slowest resp    : {slowest_row['response_time_s']}s  ({slowest_row['prompt_id']})")
print(f"  Avg tok/s       : {summary_stats['avg_tokens_per_s']}")
print(f"  Fastest tok/s   : {fastest_tps['tokens_per_s']}  ({fastest_tps['prompt_id']})")
print(f"  Slowest tok/s   : {slowest_tps['tokens_per_s']}  ({slowest_tps['prompt_id']})")
print(f"{'═'*62}\n")

# ─────────────────────────────────────────────
#  WRITE CSV SUMMARY
# ─────────────────────────────────────────────
fieldnames = list(results[0].keys())

with open(CSV_FILE, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(results)

# Append aggregate stats row as a footer block
stats_file = os.path.join(SUMMARY_DIR, f"{RUN_TAG}_stats.json")
with open(stats_file, "w") as f:
    json.dump(summary_stats, f, indent=2)

print(f"  Raw responses → {RAW_FILE}")
print(f"  Per-prompt CSV → {CSV_FILE}")
print(f"  Aggregate stats → {stats_file}\n")