"""Offline readiness checks only: never starts services or publishes messages."""
import argparse
import hashlib
import json
import subprocess
import re
from pathlib import Path
from urllib.parse import urlsplit

from evaluation.baselines.shared.evaluate import load_labels
from evaluation.baselines.shared.verify_revision import verify

NODES = {'stream-node': '10.10.10.11', 'ai-brain-node': '10.10.10.12', 'gateway-node': '10.10.10.13'}
REQUIRED_TARGETS = {
    ('fyp-cluster', f'{node}:9100', ip, 9100) for node, ip in NODES.items()
} | {('fyp-layer1', f'stream-node:{port}', '10.10.10.11', port) for port in range(8002,8009)} | {
    ('fyp-single-agent-baseline','ai-brain-node:8030','10.10.10.12',8030),
    ('rabbitmq','stream-node:15692','10.10.10.11',15692),
    ('fyp-layer3-autoexec','gateway-node:8014','10.10.10.13',8014),
    ('fyp-layer3-hitl','gateway-node:8000','10.10.10.13',8000),
    ('prometheus','localhost:9090','localhost',9090),
    ('node','localhost:9100','localhost',9100),
}
INACTIVE = {'fyp-agent-pipeline','fyp-threshold-baseline'}
FROZEN_FILES = {'events_1950.jsonl','seg_config.json','labels.csv','labels_routing.csv'}


def check_targets(document):
    seen = []
    for target in document['data']['activeTargets']:
        job = target['labels']['job']
        if job in INACTIVE:
            continue  # Process/queue ownership must still be checked separately.
        url = urlsplit(target['scrapeUrl'])
        identity = (job, target['labels'].get('instance'), url.hostname, url.port)
        if identity not in REQUIRED_TARGETS or target['health'] != 'up':
            raise ValueError(f'Unexpected/down required target: {identity}')
        seen.append(identity)
    if len(seen) != len(REQUIRED_TARGETS) or set(seen) != REQUIRED_TARGETS:
        raise ValueError('Missing or duplicated required target')
    return {'required_up':len(seen),'inactive_jobs':sorted(INACTIVE)}


def check_revision(repo, manifest):
    if (manifest.get('controller_branch') != 'experiment/single-agent-baseline' or
        manifest.get('controller') != 'single_agent' or manifest.get('network_medium') != 'ethernet' or
        manifest.get('replay_speed') != 1):
        raise ValueError('Single-Agent Ethernet identity/speed mismatch')
    hashes=manifest.get('frozen_input_hashes',{})
    if set(hashes) != FROZEN_FILES or any(not isinstance(h,str) or len(h)!=64 or
       any(c not in '0123456789abcdef' for c in h) for h in hashes.values()):
        raise ValueError('Four approved frozen input hashes required')
    groups=manifest.get('files',{})
    required={
        'shared_evaluation':{'evaluation/baselines/shared/evaluate.py','evaluation/baselines/shared/verify_revision.py',
                            'evaluation/baselines/single_agent/ethernet_checks.py'},
        'deployment':{'deployment/ethernet/node2.env.sh','deployment/ethernet/node3.env.sh',
                      'deployment/ethernet/prometheus.ethernet.yml','layer3/dashboard/settings.py','layer3/requirements_node3.txt',
                      'layer3/dashboard/hitl/views.py','layer3/dashboard/hitl/management/commands/consume_hitl.py'},
        'routing_policy':{'layer2/evaluation/generate_routing_labels.py','layer2/evaluation/ROUTING_LABEL_POLICY.md'}}
    for group, paths in required.items():
        if not paths <= {r['path'] for r in groups.get(group,[])}:
            raise ValueError('Incomplete reviewed inventory: '+group)
    node=manifest.get('node')
    if node not in NODES:raise ValueError('Unknown node')
    local_required=FROZEN_FILES if node=='stream-node' else {'labels.csv','labels_routing.csv'}
    local={Path(r['path']).name:r['sha256'] for r in groups.get('corpus',[])}
    if not local_required <= local.keys() or any(local[k]!=hashes[k] for k in local_required):
        raise ValueError('Local frozen files do not match approved cross-node hashes')
    records = groups.get('controller', [])
    required_runtime = {
        'evaluation/baselines/single_agent/' + name for name in
        ('controller.py','feedback.py','llm_client.py','metrics.py','prompt.py','schema.py',
         'ETHERNET_FULL_RUN.md','ethernet_checks.py',
         'observability/FYP_Single_Agent_Baseline_Observability.json')
    } | {
        'evaluation/baselines/common/' + name for name in
        ('contracts.py','journal.py','rabbitmq.py','layer3_adapter.py','presentation_settings.py',
         'templates/hitl/detail.html')
    } | {'layer2/agents/schema_validator.py'}
    if not required_runtime <= {r['path'] for r in records}:
        raise ValueError('Incomplete reviewed inventory: controller')
    result = verify(repo,manifest)
    root = Path(repo).resolve()
    for record in records:
        relative = Path(record['path'])
        path = (root / relative).resolve()
        if relative.is_absolute() or '..' in relative.parts or not path.is_relative_to(root):
            raise ValueError('Controller paths must stay within repository')
        expected = record['sha256']
        if not re.fullmatch('[0-9a-f]{64}', expected) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Controller hash mismatch: ' + str(relative))
        blob = subprocess.check_output(['git','-C',str(root),'show',
            manifest['controller_commit'] + ':' + relative.as_posix()])
        if hashlib.sha256(blob).hexdigest() != expected:
            raise ValueError('Controller source revision mismatch: ' + str(relative))
    return result


def check_corpus(directory, manifest):
    root=Path(directory)
    hashes=manifest['frozen_input_hashes']
    for name in FROZEN_FILES:
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=hashes[name]:
            raise ValueError('Frozen hash mismatch: '+name)
    labels=load_labels(root/'labels_routing.csv')
    import csv
    with (root/'labels.csv').open(newline='') as source:
        original=list(csv.DictReader(source))
    if len(original)!=len(labels) or [r['event_id'] for r in original]!=list(labels):
        raise ValueError('Source/derived label order or IDs differ')
    for row in original:
        if any(row[k]!=labels[row['event_id']][k] for k in row if k not in ('expected_route','safe_to_auto')):
            raise ValueError('Source annotation changed')
    events=[json.loads(line) for line in (root/'events_1950.jsonl').read_text().splitlines() if line.strip()]
    ids=[r['event_id'] for r in events]
    if len(ids)!=1950 or len(set(ids))!=1950 or set(ids)!=set(labels):
        raise ValueError('Corpus must have 1950 unique matching IDs')
    forbidden={'expected_route','safe_to_auto'}
    if any(any(k.startswith('ground_truth') or k in forbidden for k in row) for row in events):
        raise ValueError('Ground truth leaked into runtime corpus')
    from collections import Counter
    distribution=Counter(r['expected_route'] for r in labels.values())
    if distribution!={'':1000,'AUTO':380,'HITL':570}:raise ValueError('Unexpected frozen label distribution')
    return {'events':len(events),'routing_distribution':dict(distribution),'hashes_verified':True}


ACTIVE_QUEUES = {'raw.events','validated.event','detect.cpu','detect.error','detect.throughput',
                 'detect.auth','detect.schema','fusion.results','anomaly.detected',
                 'auto.execute','hitl.queue','outcome.feedback'}
IDLE_QUEUES = {'triage.result','strategy.result','dead.letters'}


def check_queues(rows):
    seen = set()
    for row in rows:
        name = row['name']
        if name not in ACTIVE_QUEUES | IDLE_QUEUES:
            continue
        if name in seen:
            raise ValueError('Duplicate queue: ' + name)
        seen.add(name)
        if (row['consumers'] != int(name in ACTIVE_QUEUES) or
            row['messages_ready'] != 0 or row['messages_unacknowledged'] != 0):
            raise ValueError('Queue ownership/count/backlog mismatch: ' + name)
    if seen != ACTIVE_QUEUES | IDLE_QUEUES:
        raise ValueError('Missing experiment queue')
    return {'queues_verified': len(seen), 'limitation': 'Counts require manual process/connection identity verification'}


def check_workers(text):
    expected = {'controller', 'feedback'}
    seen = set()
    for line in text.splitlines():
        if line.startswith('fyp_single_agent_worker_up{'):
            match = re.fullmatch(r'fyp_single_agent_worker_up\{worker="(controller|feedback)"\}\s+([^ ]+)', line)
            if not match or match[1] in seen or float(match[2]) != 1:
                raise ValueError('Single-Agent worker not ready or malformed gauge')
            seen.add(match[1])
    if seen != expected:
        raise ValueError('Both Single-Agent workers must be ready')
    return {'workers_ready': sorted(seen)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for command in ('targets','queues','workers'):
        p=sub.add_parser(command);p.add_argument('--input',type=Path,required=True)
    p=sub.add_parser('revision');p.add_argument('--repo',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
    p=sub.add_parser('corpus');p.add_argument('--directory',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='targets':result=check_targets(json.loads(args.input.read_text()))
    elif args.command=='queues':result=check_queues(json.loads(args.input.read_text()))
    elif args.command=='workers':result=check_workers(args.input.read_text())
    elif args.command=='revision':result=check_revision(args.repo,json.loads(args.manifest.read_text()))
    else:result=check_corpus(args.directory,json.loads(args.manifest.read_text()))
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__':main()
