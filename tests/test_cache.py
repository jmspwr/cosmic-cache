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
                ci.published("cached", "cosmic")

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
                self.assertEqual(ci.published("cached", "cosmic"), {})
                ci.dump('snapshot.json', {'revision': 'a' * 40})
                ci.dump('cache-proof.json', {'revision': 'a' * 40})
                ci.publish("cached")
                first = ci.run('git', 'ls-remote', 'origin', 'refs/heads/cached').split()[0]
                self.assertEqual(ci.published("cached", "cosmic")['revision'], 'a' * 40)
                ci.dump('snapshot.json', {'revision': 'b' * 40})
                ci.dump('cache-proof.json', {'revision': 'b' * 40})
                ci.publish("cached")
                self.assertEqual(ci.published("cached", "cosmic")['revision'], 'b' * 40)
                self.assertIn('parent ' + first, ci.run('git', 'cat-file', '-p', 'FETCH_HEAD'))
                self.assertIn('snapshot.json', ci.run('git', 'ls-tree', '--name-only', 'FETCH_HEAD'))
