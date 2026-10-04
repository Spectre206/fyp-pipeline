"""Check an externally reviewed experiment revision/file manifest; never approve it."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def verify(repo, manifest):
    repo = Path(repo).resolve()
    def git(*args):
        return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
    required = ('controller_branch','controller_commit','shared_evaluation_revision',
                'deployment_profile_revision','routing_policy_revision','review_reference')
    if any(not isinstance(manifest.get(k),str) or not manifest[k].strip() for k in required):
        raise ValueError('Missing revision/review fields')
    for key in required[1:5]:
        revision = manifest[key]
        if not re.fullmatch('[0-9a-f]{40}', revision) or git('rev-parse',revision+'^{commit}') != revision:
            raise ValueError('Full locally resolvable commit required: '+key)
    if git('branch','--show-current') != manifest['controller_branch']:
        raise ValueError('Controller branch mismatch')
    if git('rev-parse','HEAD') != manifest['controller_commit']:
        raise ValueError('Controller commit mismatch')
    if git('status','--porcelain=v1','--untracked-files=all'):
        raise ValueError('Working tree must be clean')
    # Reject index flags that can conceal tracked working-tree changes.
    if any(line and (line[0].islower() or line[0]=='S') for line in git('ls-files','-v').splitlines()):
        raise ValueError('Hidden tracked-file index flags are not allowed')
    revision_keys = {'shared_evaluation':'shared_evaluation_revision',
                     'deployment':'deployment_profile_revision','routing_policy':'routing_policy_revision'}
    groups = manifest.get('files',{})
    for group in ('shared_evaluation','deployment','routing_policy','corpus'):
        records = groups.get(group)
        if not isinstance(records,list) or not records:
            raise ValueError('Nonempty reviewed file inventory required: '+group)
        for record in records:
            relative = Path(record['path'])
            path = (repo/relative).resolve()
            if relative.is_absolute() or '..' in relative.parts or not path.is_relative_to(repo):
                raise ValueError('Paths must stay within node-local repository')
            expected = record['sha256']
            if not re.fullmatch('[0-9a-f]{64}',expected) or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
                raise ValueError('File hash mismatch: '+str(relative))
            if group in revision_keys:
                blob = subprocess.check_output(['git','-C',str(repo),'show',
                    manifest[revision_keys[group]]+':'+relative.as_posix()])
                if hashlib.sha256(blob).hexdigest() != expected:
                    raise ValueError('Source revision hash mismatch: '+str(relative))
    return dict(status='verified',branch=manifest['controller_branch'],head=git('rev-parse','HEAD'),
                working_tree_clean=True,review_reference=manifest['review_reference'],
                limitation='Verifies supplied inventory, not its completeness or external approval; installed runtime state is separate')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(verify(args.repo,json.loads(args.manifest.read_text())),indent=2,sort_keys=True))

if __name__=='__main__':
    main()
