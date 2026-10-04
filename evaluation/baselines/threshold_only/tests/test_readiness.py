"""Broker-free formal-run CLI and capture validation regression tests."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from evaluation.baselines.common.capture_incidents import Capture, load_capture
from evaluation.baselines.common import replay_incidents
from evaluation.baselines.threshold_only.tests.test_contracts import fused

ROOT = Path(__file__).resolve().parents[4]


class ReadinessTests(unittest.TestCase):
    def cli(self, output, source, *extra):
        return subprocess.run([sys.executable, '-B', '-m',
            'evaluation.baselines.threshold_only.controller', '--run-id', 'readiness',
            '--output', str(output), '--dry-run', str(source), *extra],
            cwd=ROOT, text=True, capture_output=True)

    def test_network_provenance_and_identical_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'inputs.jsonl'
            source.write_text(json.dumps(fused())+'\n')
            results = []
            for medium in ('wifi', 'ethernet'):
                output = root/medium
                result = self.cli(output, source, '--network-medium', medium, '--dataset-sha256', 'a'*64)
                self.assertEqual(result.returncode, 0, result.stderr)
                manifest = json.loads((output/'run.json').read_text())
                self.assertEqual(manifest['network_medium'], medium)
                self.assertEqual(manifest['dataset_sha256'], 'a'*64)
                self.assertEqual(manifest['rules_version'], 'threshold-v1')
                self.assertEqual(len(manifest['git_commit']), 40)
                self.assertTrue(manifest['node_hostname'])
                row = json.loads((output/'decision.jsonl').read_text())
                results.append({k: row[k] for k in ('routing_decision', 'routing_reason',
                    'risk_tier', 'recommended_actions', 'rationale', 'original_event', 'rules_sha256')})
            self.assertEqual(*results)

    def test_invalid_network_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'run'
            result = self.cli(output, Path(tmp)/'unused', '--network-medium', 'mobile')
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())

    def test_live_requires_explicit_network_before_connecting(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'run'
            result = subprocess.run([sys.executable, '-B', '-m',
                'evaluation.baselines.threshold_only.controller', '--live', '--run-id', 'test',
                '--output', str(output)], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('--network-medium is required', result.stderr)
            self.assertFalse(output.exists())

    def test_invalid_dataset_digest_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'run'
            result = self.cli(output, Path(tmp)/'unused', '--dataset-sha256', 'invalid')
            self.assertEqual(result.returncode, 2)
            self.assertFalse(output.exists())

    def test_cli_does_not_overwrite_completed_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp)/'input', Path(tmp)/'run'
            source.write_text(json.dumps(fused())+'\n')
            self.assertEqual(self.cli(output, source).returncode, 0)
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            self.assertNotEqual(self.cli(output, source).returncode, 0)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def captured(self, root):
        capture = Capture(root)
        capture.write('anomaly.fused', json.dumps(fused()).encode())
        capture.finish()
        return root/'incidents.jsonl', root/'incidents.manifest.json'

    def test_manifest_schedule_counts_and_completion_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, manifest = self.captured(Path(tmp))
            original = json.loads(manifest.read_text())
            for field, value in [('schedule', 'invented'), ('count', True),
                                 ('unique_ids', True), ('capture_complete', False), ('count', 2)]:
                with self.subTest(field=field, value=value):
                    manifest.write_text(json.dumps({**original, field: value}))
                    with self.assertRaises(ValueError):
                        load_capture(data, manifest)

    def test_sequence_and_routing_key_rejected_even_with_matching_checksum(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, manifest = self.captured(Path(tmp))
            original, metadata = json.loads(data.read_text()), json.loads(manifest.read_text())
            for field, value in [('sequence', False), ('sequence', 3), ('routing_key', 'auto.execute'),
                                 ('offset_seconds', -1), ('event_id', 'mismatch')]:
                with self.subTest(field=field):
                    data.write_text(json.dumps({**original, field: value})+'\n')
                    metadata['sha256'] = hashlib.sha256(data.read_bytes()).hexdigest()
                    manifest.write_text(json.dumps(metadata))
                    with self.assertRaises(ValueError):
                        load_capture(data, manifest)

    def test_replay_cli_services_heartbeats_and_refuses_competing_consumers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, manifest = self.captured(root)
            connection = MagicMock()
            channel = connection.channel.return_value
            state = channel.queue_declare.return_value.method
            state.message_count = 0
            for consumers in (0, 2, 1):
                state.consumer_count = consumers
                argv = ['replay', '--live', '--capture', str(data), '--manifest', str(manifest),
                        '--run-id', 'test', '--output', str(root/f'replay-{consumers}')]
                with patch.object(sys, 'argv', argv), patch(
                        'evaluation.baselines.common.rabbitmq.connect', return_value=connection), patch(
                        'evaluation.baselines.common.rabbitmq.publish') as publish:
                    if consumers != 1:
                        with self.assertRaises(RuntimeError): replay_incidents.main()
                        publish.assert_not_called()
                    else:
                        replay_incidents.main()
                        connection.sleep.assert_called()
                        channel.confirm_delivery.assert_called()
                        publish.assert_called_once()
                        self.assertTrue((root/'replay-1/completed.json').exists())

    def test_bad_checksum_fails_before_broker_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, manifest = self.captured(root)
            data.write_bytes(data.read_bytes()+b' ')
            argv = ['replay', '--live', '--capture', str(data), '--manifest', str(manifest),
                    '--run-id', 'test', '--output', str(root/'replay')]
            with patch.object(sys, 'argv', argv), patch('evaluation.baselines.common.rabbitmq.connect') as connect:
                with self.assertRaises(ValueError): replay_incidents.main()
                connect.assert_not_called()
            self.assertFalse((root/'replay').exists())
