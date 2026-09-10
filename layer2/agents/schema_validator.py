"""Single source of truth for Strategy's output contract."""
from typing import Tuple

REQUIRED_FIELDS = frozenset({
    "anomaly_type", "severity", "affected_component",
    "recommended_actions", "confidence", "risk_tier", "reasoning",
})
VALID_SEVERITIES = frozenset({"LOW", "MEDIUM", "HIGH", "CRITICAL"})
VALID_RISK_TIERS = frozenset({"LOW", "HIGH"})
RISK_TIER_MAP = {"LOW": "LOW", "MEDIUM": "LOW", "HIGH": "HIGH", "CRITICAL": "HIGH"}

# Triage protocol identifiers that Policy allows for automatic execution.
# This vocabulary is shared by application validation, Ollama's output schema,
# and Policy's final authority check.
ALLOWED_ACTIONS = frozenset({
    "EMERGENCY_RESTART_CONSUMER", "SCALE_CONSUMER_RESOURCES",
    "MONITOR_AND_ALERT", "LOG_AND_CONTINUE", "CIRCUIT_BREAKER_OPEN",
    "RATE_LIMIT_ENDPOINT", "INVESTIGATE_UPSTREAM", "RESTART_ALL_CONSUMERS",
    "RESTART_FAILED_CONSUMER", "CHECK_QUEUE_DEPTH", "ISOLATE_NODE",
    "RATE_LIMIT_AUTH", "ALERT_SECURITY_TEAM", "HALT_INGESTION_REVIEW_SCHEMA",
    "FLAG_FOR_SCHEMA_REVIEW", "EMERGENCY_FULL_PIPELINE_REVIEW",
    "COORDINATED_REMEDIATION", "GENERIC_INVESTIGATE",
})

STRATEGY_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": sorted(REQUIRED_FIELDS),
    "properties": {
        "anomaly_type": {"type": "string"},
        "severity": {"type": "string", "enum": sorted(VALID_SEVERITIES)},
        "affected_component": {"type": "string"},
        "recommended_actions": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {"type": "string", "enum": sorted(ALLOWED_ACTIONS)},
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "risk_tier": {"type": "string", "enum": sorted(VALID_RISK_TIERS)},
        "reasoning": {"type": "string"},
    },
}


def validate(parsed: dict) -> Tuple[bool, str]:
    """Return (is_valid, issues_string)."""
    if not isinstance(parsed, dict):
        return False, f"not_object:{type(parsed).__name__}"

    issues = []

    missing = REQUIRED_FIELDS - parsed.keys()
    if missing:
        issues.append(f"missing_fields:{sorted(missing)}")

    extra = parsed.keys() - REQUIRED_FIELDS
    if extra:
        issues.append(f"extra_fields:{sorted(extra)}")

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
        issues.append(
            f"bad_actions_count:{len(actions) if isinstance(actions, list) else type(actions)}"
        )
    elif any(not isinstance(action, str) or action not in ALLOWED_ACTIONS for action in actions):
        issues.append("bad_actions_value")

    conf = parsed.get("confidence")
    if (
        conf is None
        or isinstance(conf, bool)
        or not isinstance(conf, (int, float))
        or not (0.0 <= conf <= 1.0)
    ):
        issues.append(f"bad_confidence:{conf}")

    for field in ("anomaly_type", "affected_component", "reasoning"):
        if not isinstance(parsed.get(field), str):
            issues.append(f"bad_{field}")

    valid = len(issues) == 0
    return valid, ("; ".join(issues) if issues else "none")
