"""7-Field JSON Schema Validator for Strategy Agent output."""
from typing import Dict, Tuple

REQUIRED_FIELDS = {
    "anomaly_type", "severity", "affected_component",
    "recommended_actions", "confidence", "risk_tier", "reasoning",
}
VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_RISK_TIERS = {"LOW", "HIGH"}
RISK_TIER_MAP = {"LOW": "LOW", "MEDIUM": "LOW", "HIGH": "HIGH", "CRITICAL": "HIGH"}


def validate(parsed: dict) -> Tuple[bool, str]:
    """Return (is_valid, issues_string)."""
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

    conf = parsed.get("confidence")
    if conf is None or not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
        issues.append(f"bad_confidence:{conf}")

    valid = len(issues) == 0
    return valid, ("; ".join(issues) if issues else "none")
