import json
import subprocess
import unittest
from unittest.mock import patch

from scripts import storage


class StorageTests(unittest.TestCase):
    def test_missing_runtime_fails_instead_of_reporting_zero_bytes(self):
        with patch.object(storage.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'path is not valid')):
            with self.assertRaisesRegex(RuntimeError, 'missing from both caches'):
                storage.inventory({'current': {'/nix/store/' + 'a' * 32 + '-app'}})

    def test_shared_runtime_is_counted_once_and_official_closure_is_free(self):
        a, b, shared, public = ['/nix/store/' + c * 32 + '-' + c for c in 'abcd']
        entries = {a: (10, [shared, public]), b: (20, [shared]), shared: (30, [])}

        def run(args, **kwargs):
            uri, path = args[args.index('--store') + 1], args[5]
            if uri == 'https://cache.nixos.org':
                return subprocess.CompletedProcess(args, 0, json.dumps({path: {}}), '') if path == public else subprocess.CompletedProcess(args, 1, '', 'path is not valid')
            size, refs = entries[path]
            return subprocess.CompletedProcess(args, 0, json.dumps({path: {'downloadSize': size, 'references': refs}}), '')

        with patch.object(storage.subprocess, 'run', side_effect=run):
            report = storage.inventory({'cosmic': {a}, 'previous': {b}})
        self.assertEqual(report['compressedBytes'], 60)
        self.assertEqual(report['snapshots']['cosmic']['compressedBytes'], 40)
        self.assertEqual(report['snapshots']['previous']['compressedBytes'], 50)
        self.assertNotIn(public, report['paths'])

    def test_network_failure_is_not_mistaken_for_an_official_cache_miss(self):
        with patch.object(storage.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'HTTP error 403')):
            with self.assertRaisesRegex(RuntimeError, '403'):
                storage.inventory({'cosmic': {'/nix/store/' + 'a' * 32 + '-shell'}})

    def test_runtime_manifest_and_reference_roots_omit_unpromised_outputs(self):
        proof = {'packages': {'a': {'path': '/old'}}, 'runtimePaths': ['/out', '/sessions'], 'referenceSystems': {'test': {'systemPath': '/system'}}}
        self.assertEqual(storage.roots(proof), {'/out', '/sessions', '/system'})
