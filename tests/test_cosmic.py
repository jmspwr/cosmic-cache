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
    def test_changed_host_requires_verification_even_when_sources_are_unchanged(self):
        proof = {'revision': 'a' * 40, 'clientDigest': 'same',
                 'referenceSystems': {'nixos-unstable': {'revision': 'old-host'}}}
        with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
            output = Path(directory, 'output')
            with patch.dict(os.environ, GITHUB_OUTPUT=str(output)), \
                 patch.object(ci, 'cache'), patch.object(ci, 'published', return_value=proof), \
                 patch.object(ci, 'host_revision', return_value='new-host'), \
                 patch.object(ci, 'client_digest', return_value='same'), \
                 patch.object(ci, 'package_info', return_value=dict.fromkeys(SourceTests.required)):
                ci.resolve(proof['revision'])
            self.assertIn('build=true', output.read_text())
            self.assertIn('host=new-host', output.read_text())

    def test_published_snapshot_retry_only_finishes_retention(self):
        proof = {'storage': {'compressedBytes': 1}, 'publicationParent': 'old', 'retentionRoot': '/root'}
        with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
            ci.dump('cache-proof.json', proof)
            with patch.object(ci, 'validate_proof'), \
                 patch.object(ci, 'published', return_value={**proof, 'publicationRevision': 'new'}), \
                 patch.object(ci.shared, 'publish') as publish, patch.object(ci, 'pin_root') as pin:
                ci.publish()
            publish.assert_not_called()
            pin.assert_called_once_with('/root')

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
        proof = {'revision': 'a' * 40, 'clientDigest': 'same', 'referenceSystems': {'nixos-unstable': {'revision': 'host'}}}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            with patch.dict(os.environ, GITHUB_OUTPUT=str(output)), \
                 patch.object(ci, 'cache'), \
                 patch.object(ci, 'published', return_value=proof), \
                 patch.object(ci, 'client_digest', return_value='same'), \
                 patch.object(ci, 'host_revision', return_value='host'), \
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

    def test_source_bundle_publishes_without_running_upstream_and_rejects_workflows(self):
        real_run = ci.run
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, remote = root / 'source', root / 'remote.git'
            real_run('git', 'init', str(source))
            real_run('git', 'init', '--bare', str(remote))
            real_run('git', 'config', 'user.name', 'Test', cwd=source)
            real_run('git', 'config', 'user.email', 'test@example.invalid', cwd=source)
            (source / '.cosmic-cache-source.json').write_text('{}')
            real_run('git', 'add', '.', cwd=source)
            real_run('git', 'commit', '-m', 'Source', cwd=source)
            revision = real_run('git', 'rev-parse', 'HEAD', cwd=source)

            def bundle():
                (root / 'source.bundle').unlink(missing_ok=True)
                real_run('git', 'update-ref', 'refs/heads/snapshot', 'HEAD', cwd=source)
                real_run('git', 'bundle', 'create', str(root / 'source.bundle'), 'refs/heads/snapshot', cwd=source)

            def local_run(*args, **kwargs):
                if args[:2] == ('git', 'push'):
                    args = (*args[:2], str(remote), *args[3:])
                return real_run(*args, **kwargs)

            bundle()
            with patch.object(ci.shared, 'ROOT', root), patch.object(ci, 'run', side_effect=local_run), \
                 patch.dict(os.environ, GITHUB_TOKEN='test'):
                ci.publish_source(revision)
                self.assertEqual(real_run('git', 'rev-parse', 'refs/heads/source', cwd=remote), revision)
                (source / '.github').mkdir()
                (source / '.github/workflow.yml').write_text('untrusted')
                real_run('git', 'add', '.', cwd=source)
                real_run('git', 'commit', '-m', 'Invalid source', cwd=source)
                bundle()
                with self.assertRaisesRegex(RuntimeError, 'Invalid source snapshot'):
                    ci.publish_source(real_run('git', 'rev-parse', 'HEAD', cwd=source))
                self.assertEqual(real_run('git', 'rev-parse', 'refs/heads/source', cwd=remote), revision)

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

    def test_epoch_submodules_define_the_suite(self):
        modules = ''.join(
            f'[submodule "{n}"]\n\tpath = {n}\n\turl = https://github.com/pop-os/{n}{s}\n'
            for n, s in [(f'cosmic-{i}', ['', '.git', '/'][i % 3]) for i in range(20)]
            + [('simple-wrapper', ''), ('launcher', '.git')])
        repos = ci.epoch_components(modules)
        self.assertIn('pop-os/cosmic-1', repos)
        self.assertIn('pop-os/launcher', repos)
        self.assertNotIn('pop-os/simple-wrapper', repos)
        with self.assertRaisesRegex(RuntimeError, 'epoch'):
            ci.epoch_components('')

    def test_every_epoch_component_gets_a_trackable_recipe(self):
        with tempfile.TemporaryDirectory() as directory:
            self.recipes(directory)
            nixpkgs = Path(directory, 'nixpkgs')
            (nixpkgs / 'pkgs/by-name/co/cosmic-known').mkdir(parents=True)
            (nixpkgs / 'pkgs/by-name/co/cosmic-known/package.nix').write_text(
                'src = fetchFromGitHub {\n owner = "pop-os";\n repo = "cosmic-known";\n rev = "' + 'b' * 40 + '";\n};\n')
            repos = ['pop-os/' + n for n in self.required + ['cosmic-known', 'cosmic-new']]
            suite, added = ci.supplement(directory, repos, nixpkgs)
            self.assertEqual(added, ['cosmic-known', 'cosmic-new'])
            self.assertEqual(sorted(suite), sorted(self.required + added))
            self.assertEqual(ci.component_sources(directory)['pop-os/cosmic-known']['rev'], 'b' * 40)
            self.assertIn('pop-os/cosmic-new', ci.component_sources(directory))
            # Once the packaging repository covers a component, nothing is added for it.
            self.assertEqual(ci.supplement(directory, repos, nixpkgs), (suite, []))
            with self.assertRaisesRegex(RuntimeError, 'other/tool'):
                ci.supplement(directory, ['other/tool'], nixpkgs)

    def test_component_selection_excludes_extensions_and_legacy_alias(self):
        for name in ['cosmic-comp', 'cosmic-app-library', 'cutecosmic', 'pop-launcher']:
            self.assertTrue(ci.selected_package(name))
        for name in ['cosmic-ext-dock', 'cosmic-applibrary', 'update']:
            self.assertFalse(ci.selected_package(name))


if __name__ == '__main__':
    unittest.main()
