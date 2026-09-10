"""Analyze opt-in Layer 2 JSONL artifacts from one named run."""
import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

STAGES = ("triage", "strategy", "policy", "feedback", "learning")


def is_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )

def rows(path):
    output, malformed = {}, 0
    for stage in STAGES:
        items = []
        source = path / f"{stage}.jsonl"
        if source.exists():
            for line in source.read_text().splitlines():
                try:
                    item = json.loads(line)
                    if not isinstance(item, dict):
                        malformed += 1
                    else:
                        items.append(item)
                except json.JSONDecodeError:
                    malformed += 1
        output[stage] = items
    return output, malformed

def latest(items):
    result, duplicates = {}, 0
    for item in items:
        key = item.get("event_id")
        if not key: continue
        if key in result: duplicates += 1
        result[key] = item
    return result, duplicates

def distribution(values):
    values = sorted(v for v in values if is_number(v))
    if not values: return {"count": 0}
    q = lambda p: values[min(len(values)-1, int((len(values)-1)*p))]
    return {"count":len(values), "mean":sum(values)/len(values), "median":q(.5), "p95":q(.95), "p99":q(.99), "max":max(values)}

def unavailable(reason): return {"status":"not_computable", "reason":reason}


def read_ground_truth(path):
    """Read only externally supplied labels; runtime output is never labels."""
    if path is None:
        return {}, 0, None
    labels, malformed = {}, 0
    try:
        with path.open(newline="") as source:
            for row in csv.DictReader(source):
                event_id = row.get("event_id")
                if not event_id:
                    malformed += 1
                    continue
                expected_route = row.get("expected_route", "").strip()
                safe_to_auto = row.get("safe_to_auto", "").strip()
                if expected_route not in {"", "AUTO", "HITL"}:
                    malformed += 1
                if safe_to_auto not in {"", "true", "false"}:
                    malformed += 1
                labels[event_id] = row
    except (OSError, csv.Error):
        return {}, 0, "ground_truth_file_unreadable"
    return labels, malformed, None


def percentage_counts(counts):
    total = sum(counts.values())
    return {
        key: {"count": value, "percentage": value / total if total else None}
        for key, value in sorted(counts.items())
    }


def rate(numerator, denominator):
    return numerator / denominator if denominator else None


def risk_accuracy(strategy, labels):
    comparable = [
        (result, labels[event_id])
        for event_id, result in strategy.items()
        if event_id in labels
        and labels[event_id].get("ground_truth_risk_tier") in {"LOW", "HIGH"}
    ]
    if not comparable:
        return unavailable("requires matching event_id keyed ground_truth_risk_tier labels")

    matrix = Counter()
    correct = 0
    for result, label in comparable:
        expected = label["ground_truth_risk_tier"]
        predicted = result.get("risk_tier")
        matrix[f"expected_{expected}__predicted_{predicted or 'MISSING'}"] += 1
        correct += predicted == expected
    return {
        "status": "computed",
        "definition": "Strategy predicted risk tier == externally labeled ground_truth_risk_tier / labeled cases",
        "labeled_cases": len(comparable),
        "correct": correct,
        "value": rate(correct, len(comparable)),
        "confusion_matrix": dict(sorted(matrix.items())),
    }


def automation_metrics(policy, labels):
    has_safe_to_auto = any(
        row.get("safe_to_auto", "").strip() in {"true", "false"}
        for row in labels.values()
    )
    has_expected_route = any(
        row.get("expected_route") in {"AUTO", "HITL"} for row in labels.values()
    )
    if not has_safe_to_auto:
        far = unavailable("requires authoritative safe_to_auto ground truth for each AUTO decision")
    else:
        comparable = [
            (event_id, row) for event_id, row in policy.items()
            if row.get("routing_decision") == "AUTO" and event_id in labels
            and labels[event_id].get("safe_to_auto", "").strip() in {"true", "false"}
        ]
        unsafe = sum(labels[event_id]["safe_to_auto"].strip() == "false" for event_id, _ in comparable)
        far = {
            "status": "computed",
            "definition": "AUTO decisions labeled safe_to_auto=false / AUTO decisions with safe_to_auto labels",
            "labeled_auto_decisions": len(comparable),
            "unsafe_auto_decisions": unsafe,
            "value": rate(unsafe, len(comparable)),
        }
    if not has_expected_route:
        fer = unavailable("requires authoritative expected_route ground truth to identify AUTO-eligible HITL decisions")
    else:
        eligible = [
            (event_id, row) for event_id, row in policy.items()
            if event_id in labels and labels[event_id].get("expected_route") == "AUTO"
        ]
        false_escalations = sum(row.get("routing_decision") == "HITL" for _, row in eligible)
        fer = {
            "status": "computed",
            "definition": "HITL decisions with expected_route=AUTO / decisions with expected_route=AUTO",
            "auto_eligible_decisions": len(eligible),
            "false_escalations": false_escalations,
            "value": rate(false_escalations, len(eligible)),
        }
    return far, fer


def analyze(run_dir, ground_truth_path=None, expect_hitl_feedback=False):
    raw, malformed = rows(run_dir)
    data, duplicates = {}, {}
    for stage, values in raw.items(): data[stage], duplicates[stage] = latest(values)
    labels, malformed_ground_truth, ground_truth_error = read_ground_truth(ground_truth_path)
    ids = set().union(*[set(values) for values in data.values()])
    strategy, policy = data["strategy"], data["policy"]
    feedback, learning = data["feedback"], data["learning"]
    non_timeout = [x for x in strategy.values() if not x.get("timed_out", False)]
    schema_valid = sum(x.get("schema_valid") is True for x in non_timeout)
    decisions = Counter(x.get("routing_decision", "UNKNOWN") for x in policy.values())
    reasons = Counter(x.get("routing_reason", "UNKNOWN") for x in policy.values())
    auto_policy_ids = {
        event_id for event_id, row in policy.items()
        if row.get("routing_decision") == "AUTO"
    }
    hitl_policy_ids = {
        event_id for event_id, row in policy.items()
        if row.get("routing_decision") == "HITL"
    }
    expected_feedback = auto_policy_ids | (hitl_policy_ids if expect_hitl_feedback else set())
    triage_processing_latency = distribution(
        x.get("triage_latency_s") for x in data["triage"].values()
    )
    strategy_processing_latency = distribution(
        x.get("strategy_latency_s") for x in strategy.values()
    )
    policy_processing_latency = distribution(
        x.get("policy_latency_s") for x in policy.values()
    )
    feedback_completion_latency = distribution(
        feedback[event_id].get("feedback_completion_latency_s")
        for event_id in set(feedback) & expected_feedback
    )
    learning_processing_latency = distribution(
        x.get("learning_latency_s") for x in learning.values()
    )
    end_to_end_decision_latency = distribution(
        x.get("end_to_end_decision_latency_s") for x in policy.values()
    )
    control_plane_processing_latency = distribution(
        data["triage"][event_id].get("triage_latency_s")
        + strategy[event_id].get("strategy_latency_s")
        + policy[event_id].get("policy_latency_s")
        for event_id in set(data["triage"]) & set(strategy) & set(policy)
        if all(is_number(record.get(key)) for record, key in (
            (data["triage"][event_id], "triage_latency_s"),
            (strategy[event_id], "strategy_latency_s"),
            (policy[event_id], "policy_latency_s"),
        ))
    )
    far, fer = automation_metrics(policy, labels)
    auto_expected = len(auto_policy_ids)
    auto_received = len(auto_policy_ids & set(feedback))
    hitl_expected = len(hitl_policy_ids) if expect_hitl_feedback else 0
    hitl_received = len(hitl_policy_ids & set(feedback))
    summary = {
      "counts": {
          "unique_events": len(ids),
          "missing_strategy": len(ids - set(strategy)),
          "missing_policy": len(ids - set(policy)),
          "missing_feedback": len(expected_feedback - set(feedback)),
          "pending_hitl_without_feedback": len(hitl_policy_ids - set(feedback)),
          "unknown_feedback_event_ids": len(set(feedback) - set(policy)),
          "missing_learning_processing": len(set(feedback) - set(learning)),
          "malformed_records": malformed,
          "duplicates": duplicates,
          "ground_truth_records": len(labels),
          "malformed_ground_truth_records": malformed_ground_truth,
          "ground_truth_error": ground_truth_error,
      },
      "svr": {
          "status": "computed",
          "definition": "schema-valid non-timeout Strategy responses / non-timeout Strategy responses",
          "total_requests": len(strategy),
          "timeouts": sum(x.get("timed_out", False) for x in strategy.values()),
          "timeout_rate": rate(sum(x.get("timed_out", False) for x in strategy.values()), len(strategy)),
          "valid_json": sum(x.get("valid_json", False) for x in strategy.values()),
          "invalid_json": sum(not x.get("valid_json", False) and not x.get("timed_out", False) for x in strategy.values()),
          "schema_valid": schema_valid,
          "schema_invalid": len(non_timeout) - schema_valid,
          "invalid_schema_rate": rate(len(non_timeout) - schema_valid, len(non_timeout)),
          "value": rate(schema_valid, len(non_timeout)),
      },
      "routing": {
          "total": len(policy),
          "counts": percentage_counts(decisions),
          "reasons": percentage_counts(reasons),
      },
      "feedback": {
          "overall": {"expected": len(expected_feedback), "received": len(set(feedback) & expected_feedback), "value": rate(len(set(feedback) & expected_feedback), len(expected_feedback))},
          "auto": {"expected": auto_expected, "received": auto_received, "value": rate(auto_received, auto_expected)},
          "hitl": {
              "status": "computed" if expect_hitl_feedback else "not_evaluated",
              "expected": hitl_expected,
              "received": hitl_received,
              "value": rate(hitl_received, hitl_expected),
              "reason": None if expect_hitl_feedback else "HITL completion was not required for this analysis",
          },
          "late_feedback": unavailable("requires an experiment-defined feedback deadline"),
      },
      "latency_seconds": {
          "triage_processing_latency": triage_processing_latency,
          "strategy_processing_latency": strategy_processing_latency,
          "policy_processing_latency": policy_processing_latency,
          "control_plane_processing_latency": control_plane_processing_latency,
          "end_to_end_decision_latency": end_to_end_decision_latency,
          "feedback_completion_latency": feedback_completion_latency,
          "learning_processing_latency": learning_processing_latency,
      },
      "risk_tier_accuracy": risk_accuracy(strategy, labels),
      "false_automation_rate": far,
      "false_escalation_rate": fer,
    }
    return summary, data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--ground-truth", type=Path, help="optional CSV with event_id keyed labels")
    parser.add_argument("--expect-hitl-feedback", action="store_true")
    args = parser.parse_args()
    summary, data = analyze(
        args.run_dir, args.ground_truth, args.expect_hitl_feedback
    )
    (args.run_dir / "evaluation_summary.json").write_text(json.dumps(summary, indent=2))
    with (args.run_dir/"per_event.csv").open("w",newline="") as output:
        fields=["event_id","anomaly_type","triage_protocol","strategy_valid_json","strategy_schema_valid","strategy_timeout","strategy_risk_tier","strategy_confidence","policy_decision","policy_reason","feedback_received","feedback_outcome","triage_latency_s","strategy_latency_s","policy_latency_s","end_to_end_decision_latency_s","feedback_completion_latency_s","learning_latency_s"]
        writer=csv.DictWriter(output,fieldnames=fields); writer.writeheader()
        for event_id in sorted(set().union(*[set(x) for x in data.values()])):
            t, s, p, f = (
                data[stage].get(event_id, {})
                for stage in ("triage", "strategy", "policy", "feedback")
            )
            writer.writerow({"event_id":event_id,"anomaly_type":t.get("anomaly_type"),"triage_protocol":t.get("response_protocol"),"strategy_valid_json":s.get("valid_json"),"strategy_schema_valid":s.get("schema_valid"),"strategy_timeout":s.get("timed_out"),"strategy_risk_tier":s.get("risk_tier"),"strategy_confidence":s.get("confidence"),"policy_decision":p.get("routing_decision"),"policy_reason":p.get("routing_reason"),"feedback_received":bool(f),"feedback_outcome":f.get("outcome_type"),"triage_latency_s":t.get("triage_latency_s"),"strategy_latency_s":s.get("strategy_latency_s"),"policy_latency_s":p.get("policy_latency_s"),"end_to_end_decision_latency_s":p.get("end_to_end_decision_latency_s"),"feedback_completion_latency_s":f.get("feedback_completion_latency_s"),"learning_latency_s":data["learning"].get(event_id,{}).get("learning_latency_s")})
    print(f"Evaluation artifacts: {args.run_dir}")
    print(
        "SVR: "
        f"{summary['svr']['value']} "
        f"({summary['svr']['schema_valid']}/{summary['svr']['total_requests'] - summary['svr']['timeouts']} non-timeout responses)"
    )
    print(
        "Routing: "
        + ", ".join(
            f"{decision}={values['count']}"
            for decision, values in summary["routing"]["counts"].items()
        )
    )
    print(
        "Feedback completion: "
        f"{summary['feedback']['overall']['value']} "
        f"({summary['feedback']['overall']['received']}/{summary['feedback']['overall']['expected']})"
    )
    print(f"Machine-readable summary: {args.run_dir / 'evaluation_summary.json'}")
if __name__ == "__main__": main()
