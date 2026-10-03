import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from evaluation.baselines.shared.verify_revision import verify


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'file').write_bytes(b'approved')
        self.rev='a'*40;self.status='';self.flags='H file'
        self.manifest=dict(controller_branch='branch',controller_commit=self.rev,
            shared_evaluation_revision=self.rev,deployment_profile_revision=self.rev,
            routing_policy_revision=self.rev,review_reference='review-1',files={
                k:[dict(path='file',sha256=hashlib.sha256(b'approved').hexdigest())]
                for k in ('shared_evaluation','deployment','routing_policy','corpus')})
    def git(self,args,**kw):
        command=args[3:]
        if command[0]=='show':return b'approved'
        if command[0]=='branch':return 'branch\n'
        if command[0]=='rev-parse':return self.rev+'\n'
        if command[0]=='status':return self.status
        if command[0]=='ls-files':return self.flags
        raise AssertionError(command)
    def check(self):
        with patch('evaluation.baselines.shared.verify_revision.subprocess.check_output',side_effect=self.git):
            return verify(self.root,self.manifest)
    def test_approved_inventory(self):self.assertEqual(self.check()['status'],'verified')
    def test_dirty_tree(self):
        self.status=' M file'
        with self.assertRaisesRegex(ValueError,'clean'):self.check()
    def test_hidden_source(self):
        self.flags='h file'
        with self.assertRaisesRegex(ValueError,'flags'):self.check()
    def test_hash_mismatch(self):
        (self.root/'file').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.check()
    def test_missing_group(self):
        del self.manifest['files']['corpus']
        with self.assertRaisesRegex(ValueError,'inventory'):self.check()
    def test_escape(self):
        self.manifest['files']['corpus'][0]['path']='../file'
        with self.assertRaisesRegex(ValueError,'Paths'):self.check()
    def test_wrong_head(self):
        self.manifest['controller_commit']='b'*40
        with self.assertRaises(ValueError):self.check()

if __name__=='__main__':unittest.main()
