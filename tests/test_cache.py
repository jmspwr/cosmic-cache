import contextlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from scripts import cache as ci


class PublicationTests(unittest.TestCase):
    def test_network_error_is_not_treated_as_unpublished(self):
        with patch.object(ci, 'run', side_effect=subprocess.CalledProcessError(1, 'git')):
            with self.assertRaises(subprocess.CalledProcessError):
                ci.published("cosmic-cache", "cosmic")

    def test_publish_first_snapshot_and_fast_forward_with_ignored_files(self):
        with tempfile.TemporaryDirectory() as directory:
            remote = Path(directory) / 'remote.git'
            work = Path(directory) / 'work'
            ci.run('git', 'init', '--bare', str(remote))
            ci.run('git', 'clone', str(remote), str(work))
            with contextlib.chdir(work):
                ci.run('git', 'config', 'user.name', 'Test')
                ci.run('git', 'config', 'user.email', 'test@example.invalid')
                Path('.gitignore').write_text('snapshot.json\ncache-proof.json\n')
                ci.run('git', 'add', '.gitignore')
                ci.run('git', 'commit', '-m', 'Initial')
                ci.run('git', 'push', 'origin', 'HEAD:main')
                self.assertEqual(ci.published("cosmic-cache", "cosmic"), {})
                ci.dump('snapshot.json', {'revision': 'a' * 40})
                ci.dump('cache-proof.json', {'revision': 'a' * 40})
                ci.publish("cosmic-cache")
                first = ci.run('git', 'ls-remote', 'origin', 'refs/heads/cosmic-cache').split()[0]
                self.assertEqual(ci.published("cosmic-cache", "cosmic")['revision'], 'a' * 40)
                ci.dump('snapshot.json', {'revision': 'b' * 40})
                ci.dump('cache-proof.json', {'revision': 'b' * 40})
                ci.publish("cosmic-cache")
                self.assertEqual(ci.published("cosmic-cache", "cosmic")['revision'], 'b' * 40)
                self.assertIn('parent ' + first, ci.run('git', 'cat-file', '-p', 'FETCH_HEAD'))
                self.assertIn('snapshot.json', ci.run('git', 'ls-tree', '--name-only', 'FETCH_HEAD'))
                current = ci.run('git', 'rev-parse', 'FETCH_HEAD')
                with self.assertRaisesRegex(RuntimeError, 'changed after retention'):
                    ci.publish('cosmic-cache', expected_parent=first)
                self.assertEqual(current, ci.run('git', 'ls-remote', 'origin', 'refs/heads/cosmic-cache').split()[0])

    def test_publication_is_readable_from_cosmic_subdirectory(self):
        with tempfile.TemporaryDirectory() as directory:
            remote = Path(directory) / 'remote.git'
            work = Path(directory) / 'work'
            ci.run('git', 'init', '--bare', str(remote))
            ci.run('git', 'clone', str(remote), str(work))
            with contextlib.chdir(work):
                ci.run('git', 'config', 'user.name', 'Test')
                ci.run('git', 'config', 'user.email', 'test@example.invalid')
                Path('.gitignore').write_text('snapshot.json\ncache-proof.json\n')
                Path('builder.py').write_text('build-only code')
                for desktop in ['cosmic']:
                    Path(desktop).mkdir()
                    Path(desktop, 'default.nix').write_text('{}')
                ci.run('git', 'add', '.')
                ci.run('git', 'commit', '-m', 'Initial')
                for desktop, branch in [('cosmic', 'cosmic-cache')]:
                    ci.run('git', 'reset', '--mixed', 'HEAD')
                    with contextlib.chdir(desktop):
                        ci.dump('snapshot.json', {'desktop': desktop})
                        ci.dump('cache-proof.json', {'desktop': desktop})
                        ci.publish(branch, files=[f'{desktop}/default.nix', f'{desktop}/snapshot.json', f'{desktop}/cache-proof.json'])
                        proof = ci.published(branch, desktop)
                        self.assertEqual(proof['desktop'], desktop)
                        self.assertEqual(proof['snapshot']['desktop'], desktop)
                        files = ci.run('git', 'ls-tree', '-r', '--name-only', 'FETCH_HEAD').splitlines()
                        self.assertNotIn('builder.py', files)
                        self.assertEqual(len(files), 3)
                        self.assertEqual(ci.run('git', 'diff', '--cached', '--name-only'), '')
