"""Prepare a separate 50-event engineering subset offline; never publish it."""
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from evaluation.baselines.shared.evaluate import load_labels


def prepare(corpus, labels_path, output):
    labels=load_labels(labels_path)
    lines=[line for line in Path(corpus).read_text().splitlines() if line.strip()]
    events=[json.loads(line) for line in lines]
    ids=[r['event_id'] for r in events]
    if len(ids)!=len(set(ids)) or set(ids)!=set(labels):raise ValueError('Source IDs must uniquely match labels')
    normal,anomaly=defaultdict(list),defaultdict(list)
    for index,row in enumerate(events):
        if any(k.startswith('ground_truth') or k in {'expected_route','safe_to_auto'} for k in row):
            raise ValueError('Runtime ground-truth leakage')
        (normal if labels[row['event_id']]['ground_truth_label']=='NORMAL' else anomaly)[row['affected_component']].append(index)
    choices=sorted(k for k in normal if len(normal[k])>=20 and len(anomaly[k])>=30)
    if not choices:raise ValueError('No component with 20 normal and 30 anomaly events')
    component=choices[0];selected=normal[component][:20]+anomaly[component][:30]
    destination=Path(output);destination.mkdir(parents=True,exist_ok=False)
    (destination/'events_50_diagnostic.jsonl').write_text(''.join(lines[i]+'\n' for i in selected))
    selected_ids={events[i]['event_id'] for i in selected}
    with (destination/'labels_routing_50_diagnostic.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(next(iter(labels.values()))),lineterminator='\n')
        writer.writeheader();writer.writerows(row for i,row in labels.items() if i in selected_ids)
    report={'purpose':'engineering-diagnostic-only','component':component,'events':50,
            'selection':'first sorted eligible component; first 20 NORMAL then first 30 anomalies; source order within groups',
            'source_hashes':{str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in (corpus,labels_path)},
            'outputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(destination.iterdir())}}
    (destination/'manifest.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('corpus','labels','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(prepare(args.corpus,args.labels,args.output),indent=2))
