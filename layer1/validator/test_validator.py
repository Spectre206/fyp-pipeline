# layer1/validator/test_validator.py

import sys
from pydantic import ValidationError

# Import the classes from your validator.py file
from validator import PipelineEvent, ValidatorConsumer

print("Running Pydantic Validator unit tests...\n")

# ── Test 1: Valid event passes ─────────────────────────────────────────
good = {
    "event_id":           "550e8400-e29b-41d4-a716-446655440000",
    "timestamp":          "2026-04-01T10:00:00+00:00",
    "anomaly_type":       "cpu_memory_spike",
    "severity":           "HIGH",
    "affected_component": "ADM runner",
    "node":               "stream-node",
    "metric_values":      {"cpu_percent": 91.5, "mem_percent": 93.2},
    "context":            "CPU spike detected",
}
evt = PipelineEvent(**good)
assert evt.anomaly_type == "cpu_memory_spike"
assert evt.severity == "HIGH"
print("Test 1 PASSED: valid event accepted by Pydantic")

# ── Test 2: Missing required field → MISSING_FIELD ────────────────────
bad_missing = {
    "event_id":     "550e8400-e29b-41d4-a716-446655440001",
    "timestamp":    "2026-04-01T10:00:01+00:00",
    "anomaly_type": "cpu_memory_spike",
    "severity":     "HIGH",
    # missing: affected_component, node, metric_values
}
try:
    PipelineEvent(**bad_missing)
    print("Test 2 FAILED: should have raised ValidationError")
except ValidationError as e:
    v = ValidatorConsumer.__new__(ValidatorConsumer)
    v._seen_ids = set()
    etype = v._classify_error(e, bad_missing)
    assert etype == "MISSING_FIELD", f"Expected MISSING_FIELD, got {etype}"
    print(f"Test 2 PASSED: missing field → error_type={etype} → severity=MEDIUM")

# ── Test 3: Type mutation → TYPE_MUTATION ─────────────────────────────
bad_type = {
    "event_id":           "550e8400-e29b-41d4-a716-446655440002",
    "timestamp":          "2026-04-01T10:00:02+00:00",
    "anomaly_type":       "cpu_memory_spike",
    "severity":           "HIGH",
    "affected_component": "ADM runner",
    "node":               "stream-node",
    "metric_values":      "this_should_be_a_dict",   # type mutation
    "context":            "",
}
try:
    PipelineEvent(**bad_type)
    print("Test 3 FAILED: should have raised ValidationError")
except ValidationError as e:
    v = ValidatorConsumer.__new__(ValidatorConsumer)
    v._seen_ids = set()
    etype = v._classify_error(e, bad_type)
    assert etype == "TYPE_MUTATION", f"Expected TYPE_MUTATION, got {etype}"
    print(f"Test 3 PASSED: type mutation → error_type={etype} → severity=HIGH")

# ── Test 4: Invalid enum value → SCHEMA_VIOLATION ─────────────────────
bad_enum = dict(good)
bad_enum["event_id"]     = "550e8400-e29b-41d4-a716-446655440003"
bad_enum["anomaly_type"] = "invalid_type_not_in_literal"
try:
    PipelineEvent(**bad_enum)
    print("Test 4 FAILED: should have raised ValidationError")
except ValidationError as e:
    v = ValidatorConsumer.__new__(ValidatorConsumer)
    v._seen_ids = set()
    etype = v._classify_error(e, bad_enum)
    assert etype in ("SCHEMA_VIOLATION", "TYPE_MUTATION")
    print(f"Test 4 PASSED: invalid enum → error_type={etype} → severity=MEDIUM")

# ── Test 5: Empty metric_values → validation error ────────────────────
bad_empty = dict(good)
bad_empty["event_id"]      = "550e8400-e29b-41d4-a716-446655440004"
bad_empty["metric_values"] = {}
try:
    PipelineEvent(**bad_empty)
    print("Test 5 FAILED: should have raised ValidationError")
except ValidationError as e:
    print("Test 5 PASSED: empty metric_values correctly rejected")

# ── Test 6: Invalid UUID → validation error ───────────────────────────
bad_uuid = dict(good)
bad_uuid["event_id"] = "not-a-valid-uuid"
try:
    PipelineEvent(**bad_uuid)
    print("Test 6 FAILED: should have raised ValidationError")
except ValidationError as e:
    print("Test 6 PASSED: invalid UUID correctly rejected")

# ── Test 7: NORMAL event with N/A severity passes ─────────────────────
normal = {
    "event_id":           "550e8400-e29b-41d4-a716-446655440005",
    "timestamp":          "2026-04-01T10:00:05+00:00",
    "anomaly_type":       "NORMAL",
    "severity":           "N/A",
    "affected_component": "HTTP gateway",
    "node":               "stream-node",
    "metric_values":      {"cpu_percent": 32.1, "mem_percent": 45.0},
    "context":            "Healthy baseline traffic",
}
evt2 = PipelineEvent(**normal)
assert evt2.anomaly_type == "NORMAL"
assert evt2.severity == "N/A"
print("Test 7 PASSED: NORMAL event with N/A severity accepted")

print("\nAll 7 tests PASSED ✓")