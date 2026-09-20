import contextlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ci', ROOT / 'cosmic/ci.py')
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class PipelineTests(unittest.TestCase):
    def test_upstream_execution_does_not_inherit_publication_secrets(self):
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'github-secret', 'GH_TOKEN': 'gh-secret',
            'CACHIX_AUTH_TOKEN': 'cache-secret', 'GIT_CONFIG_VALUE_0': 'credential',
            'ACTIONS_RUNTIME_TOKEN': 'runtime-secret', 'ACTIONS_ID_TOKEN_REQUEST_TOKEN': 'oidc-secret',
            'PATH': '/bin',
        }, clear=True):
            self.assertEqual(ci.build_env(), {'PATH': '/bin'})

    def test_failed_publication_does_not_release_previous_retention(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
            ci.dump('cache-proof.json', {'storage': {'compressedBytes': 1}, 'publicationParent': 'old', 'retentionRoot': '/root'})
            with patch.object(ci, 'validate_proof'), patch.dict(os.environ, GITHUB_TOKEN='test'), \
                 patch.object(ci, 'published', return_value={}), \
                 patch.object(ci.shared, 'publish', side_effect=RuntimeError('branch changed')), \
                 patch.object(ci, 'pin_root') as pin:
                with self.assertRaisesRegex(RuntimeError, 'branch changed'):
                    ci.publish()
                pin.assert_not_called()

    def test_stale_client_proof_is_rejected_before_package_evaluation(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
            ci.dump('snapshot.json', {})
            with patch.object(ci, 'client_digest', return_value='new'), \
                 patch.object(ci, 'package_info') as info:
                with self.assertRaisesRegex(RuntimeError, 'Stale'):
                    ci.validate_proof({'schema': 3, 'clientDigest': 'old'})
                info.assert_not_called()

    def test_reference_provenance_mismatch_leaves_no_publishable_proof(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
            ci.dump('cache-proof.json', {'previous': 'stale proof'})
            ci.dump('reference-systems.json', {'revision': 'wrong'})
            with patch.object(ci, 'proof_for', return_value={'revision': 'expected'}), \
                 patch.object(ci, 'fetch_packages'):
                with self.assertRaisesRegex(RuntimeError, 'provenance'):
                    ci.verify('a' * 40)
            self.assertFalse(Path('cache-proof.json').exists())

    def test_changed_reference_output_leaves_no_publishable_proof(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
            proof = {'revision': 'a' * 40, 'clientDigest': 'same', 'builderRevision': 'builder'}
            ci.dump('reference-systems.json', {**proof, 'systems': {'nixos-unstable': {'systemPath': '/old'}}})
            with patch.object(ci, 'proof_for', return_value=proof), \
                 patch.object(ci, 'fetch_packages'), \
                 patch.object(ci, 'reference', return_value={'systemPath': '/new'}):
                with self.assertRaisesRegex(RuntimeError, 'output changed'):
                    ci.verify(proof['revision'])
            self.assertFalse(Path('cache-proof.json').exists())

    def test_repeated_candidates_retain_advertised_snapshot(self):
        from scripts import storage
        with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
            ci.dump('cache-proof.json', {})
            previous = {'publicationRevision': 'advertised', 'packages': {'app': {'path': '/published-output'}}}
            with patch.object(ci, 'validate_proof'), patch.object(ci, 'published', return_value=previous), \
                 patch.object(storage, 'check', return_value={'compressedBytes': 10}), \
                 patch.object(ci, 'retention_root', return_value='/current-root'), \
                 patch.object(ci, 'push_path'), patch.object(ci, 'pin') as pin:
                ci.retain()
                ci.retain()
            self.assertEqual([c.args for c in pin.call_args_list], [(['/published-output'],), (['/published-output'],)])
            self.assertEqual(json.loads(Path('cache-proof.json').read_text())['publicationParent'], 'advertised')

    def test_unchanged_snapshot_skips_nix_evaluation(self):
        proof = {'revision': 'a' * 40, 'clientDigest': 'same'}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            with patch.dict(os.environ, GITHUB_OUTPUT=str(output)), \
                 patch.object(ci, 'cache'), \
                 patch.object(ci, 'published', return_value=proof), \
                 patch.object(ci, 'client_digest', return_value='same'), \
                 patch.object(ci, 'package_info') as package_info:
                ci.resolve(proof['revision'])
            package_info.assert_not_called()
            self.assertIn('build=false', output.read_text())




class SourceTests(unittest.TestCase):
    required = ['cosmic-comp', 'cosmic-greeter', 'cosmic-panel', 'cosmic-session',
                'cosmic-settings', 'xdg-desktop-portal-cosmic']

    def recipes(self, directory):
        for name in self.required:
            folder = Path(directory, 'pkgs', name)
            folder.mkdir(parents=True)
            (folder / 'package.nix').write_text(
                'src = fetchFromGitHub {\n owner = "pop-os";\n repo = "' + name
                + '";\n rev = "' + 'a' * 40 + '";\n};\n'
            )

    def test_core_repositories_are_tracked(self):
        with tempfile.TemporaryDirectory() as directory:
            self.recipes(directory)
            self.assertEqual(len(ci.component_sources(directory)), len(self.required))

    def test_new_untrackable_component_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            self.recipes(directory)
            folder = Path(directory, 'pkgs', 'cosmic-new')
            folder.mkdir()
            (folder / 'package.nix').write_text('src = unsupportedFetcher {};')
            with self.assertRaisesRegex(RuntimeError, 'cosmic-new'):
                ci.component_sources(directory)

    def test_component_selection_excludes_extensions_and_legacy_alias(self):
        for name in ['cosmic-comp', 'cosmic-app-library', 'cutecosmic', 'pop-launcher']:
            self.assertTrue(ci.selected_package(name))
        for name in ['cosmic-ext-dock', 'cosmic-applibrary', 'update']:
            self.assertFalse(ci.selected_package(name))


if __name__ == '__main__':
    unittest.main()
