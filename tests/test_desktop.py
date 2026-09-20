import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import desktop


class VerificationTests(unittest.TestCase):
    def test_failed_reference_fetch_removes_provisional_publication_proof(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                Path('reference-systems.json').write_text(json.dumps({
                    'sourceDigest': 'source', 'clientDigest': 'client',
                    'systems': {'host': {'revision': 'rev', 'sha256': 'hash',
                        'systemPath': '/nix/store/system', 'closurePaths': 2}},
                }))
                def run(*args, **kwargs):
                    if args[:2] == ('nix-store', '--realise'):
                        self.assertIn('--max-jobs', args)
                        self.assertEqual(args[args.index('--max-jobs') + 1], '0')
                        self.assertEqual(args[args.index('builders') + 1], '')
                        raise RuntimeError('cache miss')
                    return ''
                with patch.object(desktop, 'proof', return_value={'sourceDigest': 'source', 'clientDigest': 'client'}), patch.object(desktop, 'integration', return_value={'systemPath': '/nix/store/system'}), patch.object(desktop, 'run', side_effect=run):
                    with self.assertRaisesRegex(RuntimeError, 'cache miss'):
                        desktop.verify(lambda: 'client')
                self.assertFalse(Path('cache-proof.json').exists())
            finally:
                os.chdir(previous)

    def test_reference_evaluation_must_match_built_artifact(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                Path('reference-systems.json').write_text(json.dumps({
                    'sourceDigest': 'source', 'clientDigest': 'client',
                    'systems': {'host': {'revision': 'rev', 'sha256': 'hash',
                        'systemPath': '/nix/store/old', 'closurePaths': 2}},
                }))
                with patch.object(desktop, 'proof', return_value={'sourceDigest': 'source', 'clientDigest': 'client'}), patch.object(desktop, 'integration', return_value={'systemPath': '/nix/store/new'}), patch.object(desktop, 'run', return_value=''):
                    with self.assertRaisesRegex(RuntimeError, 'evaluation differs'):
                        desktop.verify(lambda: 'client')
                self.assertFalse(Path('cache-proof.json').exists())
            finally:
                os.chdir(previous)
