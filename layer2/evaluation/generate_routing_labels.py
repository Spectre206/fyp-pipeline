"""Generate routing-label-policy-v2 from corpus annotations only (offline)."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

POLICY_VERSION = "routing-label-policy-v2"
SOURCE_COLUMNS = (
    "event_id", "ground_truth_label", "ground_truth_risk_tier", "ground_truth_action",
)
ROUTING_COLUMNS = ("expected_route", "safe_to_auto")


def read_source(path):
    with Path(path).open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source, strict=True)
        fields = reader.fieldnames
        if not fields or len(set(fields)) != len(fields) or any(not f for f in fields):
            raise ValueError("Missing, empty or duplicate CSV column names")
        missing = set(SOURCE_COLUMNS) - set(fields)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")
        records, seen = [], set()
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Row {reader.line_num}: wrong number of fields")
            for key in SOURCE_COLUMNS[:3]:
                if not row[key] or row[key] != row[key].strip():
                    raise ValueError(f"Row {reader.line_num}: missing/invalid {key}")
            if row['event_id'] in seen:
                raise ValueError(f"Row {reader.line_num}: duplicate event_id {row['event_id']}")
            seen.add(row['event_id'])
            normal = row['ground_truth_label'] == 'NORMAL'
            risk = row['ground_truth_risk_tier']
            action = row['ground_truth_action']
            if risk not in ({'N/A', 'LOW', 'HIGH'} if normal else {'LOW', 'HIGH'}):
                raise ValueError(f"Row {reader.line_num}: invalid ground_truth_risk_tier")
            if action != action.strip() or (not normal and not action):
                raise ValueError(f"Row {reader.line_num}: missing/invalid ground_truth_action")
            if any(row.get(key, '') != '' for key in ROUTING_COLUMNS):
                raise ValueError(f"Row {reader.line_num}: source routing fields must be blank; will not replace existing annotations")
            records.append(row)
        if not records:
            raise ValueError("Source CSV contains no records")
    return fields, records


def routing_label(row):
    if row['ground_truth_label'] == 'NORMAL':
        return '', ''
    combination = (row['ground_truth_label'], row['ground_truth_risk_tier'],
                   row['ground_truth_action'])
    if combination == ('ANOMALY', 'LOW', 'AUTO_RESTART_CONSUMER'):
        return 'AUTO', 'true'
    if combination == ('ANOMALY', 'HIGH', 'ESCALATE_TO_HITL'):
        return 'HITL', 'false'
    raise ValueError(f"event_id={row['event_id']}: inconsistent benchmark annotation {combination!r}")


def generate(input_path, output_path):
    input_path, output_path = Path(input_path), Path(output_path)
    if input_path.resolve() == output_path.resolve():
        raise ValueError("Input and output must be different files")
    fields, records = read_source(input_path)
    output_fields = fields + [f for f in ROUTING_COLUMNS if f not in fields]
    output_rows = []
    for row in records:
        route, safe = routing_label(row)
        output_rows.append({**row, 'expected_route': route, 'safe_to_auto': safe})
    # Exclusive creation prevents replacing source files, hardlinks or earlier results.
    with output_path.open('x', newline='', encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames=output_fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(output_rows)
    category = lambda r: 'NORMAL/unlabeled' if not r['expected_route'] else f"{r['expected_route']}/{r['safe_to_auto']}"
    groups = {}
    for key in SOURCE_COLUMNS[1:]:
        groups[key] = {
            value: dict(sorted(Counter(category(r) for r in output_rows if r[key] == value).items()))
            for value in sorted({r[key] for r in output_rows})
        }
    return {
        'policy_version': POLICY_VERSION,
        'field_distributions': {key: dict(sorted(Counter(r[key] for r in output_rows).items()))
                                for key in SOURCE_COLUMNS[1:] + ROUTING_COLUMNS},
        'input': str(input_path), 'output': str(output_path),
        'input_sha256': hashlib.sha256(input_path.read_bytes()).hexdigest(),
        'output_sha256': hashlib.sha256(output_path.read_bytes()).hexdigest(),
        'rows': len(records), 'source_columns': fields, 'output_columns': output_fields,
        'routing_distribution': dict(sorted(Counter(category(r) for r in output_rows).items())),
        'routing_by_source_field': groups,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = generate(args.input, args.output)
    except (ValueError, OSError, csv.Error) as exc:
        parser.exit(2, f'Routing label generation failed: {exc}\n')
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
