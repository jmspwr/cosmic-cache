import contextlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ci', ROOT / 'plasma/ci.py')
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class SchedulingTests(unittest.TestCase):
    def assert_schedule(self, graph):
        waves = ci.batches(graph)
        positions = {}
        for wave, groups in enumerate(waves):
            for group, names in enumerate(groups):
                for name in names:
                    self.assertNotIn(name, positions)
                    positions[name] = (wave, group)
        self.assertEqual(set(positions), set(graph))
        for name, dependencies in graph.items():
            for dependency in dependencies:
                self.assertTrue(
                    positions[dependency][0] < positions[name][0]
                    or positions[dependency] == positions[name],
                    (name, dependency, waves),
                )
        return waves

    def test_shared_library_stays_before_or_with_both_consumers(self):
        self.assert_schedule({'lib': set(), 'a': {'lib'}, 'b': {'lib'}})

    def test_deep_graphs_and_diamonds_have_no_cross_runner_dependencies(self):
        rng = random.Random(0)
        for size in range(1, 121):
            graph = {str(n): {str(d) for d in range(n) if rng.random() < .15} for n in range(size)}
            self.assert_schedule(graph)

    def test_schedule_is_deterministic(self):
        graph = {'c': {'a'}, 'b': {'a'}, 'a': set()}
        self.assertEqual(ci.batches(graph), ci.batches(dict(reversed(list(graph.items())))))

    def test_empty_graph(self):
        self.assertEqual(ci.batches({}), [[] for _ in range(ci.STAGES)])

    def test_cycle_is_rejected(self):
        with self.assertRaises(ValueError):
            ci.batches({'a': {'b'}, 'b': {'a'}})

    def test_aliases_schedule_one_derivation(self):
        def run(*args, **kwargs):
            if args[0] == 'nix':
                return json.dumps({'a': '/a.drv', 'alias': '/a.drv', 'b': '/b.drv'})
            return '/a.drv' if args[-1] == '/a.drv' else '/a.drv /b.drv'
        value = {'selected': ['alias', 'b']}
        with patch.object(ci, 'run', side_effect=run):
            ci.levels(value)
        self.assertEqual(value['needed'], ['a', 'b'])


class PipelineTests(unittest.TestCase):
    def test_failed_host_system_evaluation_removes_publication_proof(self):
        revision = 'a' * 40
        host_revision = 'b' * 40
        value = {'sha256': 'packaging-hash', 'mode': 'git', 'sourceDigest': 'sources'}
        evaluations = []

        def run(*args, **kwargs):
            if args[0] == 'nix-prefetch-url':
                return 'host-hash'
            if args[:2] == ('nix', 'eval'):
                evaluations.append(args[-1])
                if host_revision in args[-1]:
                    raise subprocess.CalledProcessError(1, args)
                return json.dumps({'systemDerivation': '/nix/store/packaging-system.drv'})
            return ''

        with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
            Path('reference-systems.json').write_text(json.dumps({
                'sourceDigest': 'sources', 'clientDigest': 'client', 'systems': {
                    'nixos-unstable': {'revision': host_revision, 'sha256': 'host-hash'},
                    'regression': {'revision': ci.REGRESSION_HOST, 'sha256': 'regression-hash'},
                }}))
            with patch.dict(os.environ, GITHUB_SHA='c' * 40), \
                 patch.object(ci, 'snapshot', return_value=value), \
                 patch.object(ci, 'package_info', return_value={
                     'plasma-workspace': {'version': '6.8.80', 'preferLocalBuild': False}}), \
                 patch.object(ci, 'client_digest', return_value='client'), \
                 patch.object(ci, 'options', return_value=[]), \
                 patch.object(ci, 'github_json', return_value={'sha': host_revision}), \
                 patch.object(ci, 'run', side_effect=run):
                with self.assertRaises(subprocess.CalledProcessError):
                    ci.verify(revision)
            self.assertFalse(Path('cache-proof.json').exists())
            self.assertEqual(len(evaluations), 2)

    def test_reference_closures_are_fetched_with_compilation_disabled(self):
        revision = 'a' * 40
        value = {'sha256': 'hash', 'mode': 'git', 'sourceDigest': 'sources'}
        result = {'systemDerivation': '/nix/store/system.drv',
                  'systemPath': '/nix/store/' + 'a' * 32 + '-system',
                  'applications': {'easyeffects': '/nix/store/native-easyeffects'}}
        systems = {name: {'revision': rev, 'sha256': 'hash', 'closurePaths': 2, **result}
                   for name, rev in [('nixos-unstable', 'b' * 40), ('regression', ci.REGRESSION_HOST)]}
        with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
            Path('reference-systems.json').write_text(json.dumps({
                'sourceDigest': 'sources', 'clientDigest': 'client', 'systems': systems}))
            with patch.dict(os.environ, GITHUB_SHA='c' * 40), \
                 patch.object(ci, 'snapshot', return_value=value), \
                 patch.object(ci, 'package_info', return_value={
                     'plasma-workspace': {'version': '6.8.80', 'preferLocalBuild': False}}), \
                 patch.object(ci, 'client_digest', return_value='client'), \
                 patch.object(ci, 'options', return_value=[]), \
                 patch.object(ci, 'integration_check', return_value=result), \
                 patch.object(ci, 'run', side_effect=lambda *args, **kwargs:
                              '/path/one /path/two' if '-qR' in args else '') as run:
                ci.verify(revision)
            downloads = [c.args for c in run.call_args_list if c.args[:2] == ('nix-store', '--realise')]
            self.assertEqual(len(downloads), 2)
            for args in downloads:
                self.assertEqual(args[args.index('--max-jobs') + 1], '0')
                self.assertEqual(args[args.index('builders') + 1], '')
            self.assertEqual(json.loads(Path('cache-proof.json').read_text())['referenceSystems'], systems)

    def test_resume_preserves_sources_without_polling_new_heads(self):
        revision = 'a' * 40
        heads = {'kwin': {'revision': 'b' * 40, 'url': 'https://example.invalid/source'}}
        value = {'revision': revision, 'url': ci.tarball(revision), 'mode': 'git',
                 'projects': {'kwin': 'plasma/kwin'}, 'needed': ['kwin'],
                 'gitSources': {'kwin': {**heads['kwin'], 'sha256': 'saved-hash'}},
                 'sourceDigest': ci.hashlib.sha256(json.dumps(heads, sort_keys=True).encode()).hexdigest()}
        with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
            Path('snapshot.json').write_text(json.dumps(value))
            with patch.dict(os.environ, GITHUB_OUTPUT=str(Path(directory, 'output'))), \
                 patch.object(ci, 'cache'), patch.object(ci, 'levels', return_value=[[['kwin']], [], [], [], []]), \
                 patch.object(ci, 'git_heads') as heads_call, patch.object(ci, 'source_revision') as revision_call:
                ci.resume()
            heads_call.assert_not_called()
            revision_call.assert_not_called()
            self.assertEqual(json.loads(Path('snapshot.json').read_text()), value)
            self.assertIn('build=true', Path('output').read_text())
            value['sourceDigest'] = 'wrong'
            Path('snapshot.json').write_text(json.dumps(value))
            with patch.object(ci, 'cache'), patch.object(ci, 'levels') as levels:
                with self.assertRaisesRegex(ValueError, 'digest'):
                    ci.resume()
                levels.assert_not_called()

    def test_unchanged_snapshot_skips_nix_evaluation(self):
        proof = {'revision': 'a' * 40, 'clientDigest': 'same', 'mode': 'beta',
                 'sourceDigest': ci.hashlib.sha256(b'{}').hexdigest(),
                 'snapshot': {'projects': {'kwin': 'plasma/kwin'}}}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            with patch.dict(os.environ, GITHUB_OUTPUT=str(output), SOURCE_MODE='beta'), \
                 patch.object(ci, 'cache'), \
                 patch.object(ci, 'published', return_value=proof), \
                 patch.object(ci, 'source_revision', return_value=proof['revision']), \
                 patch.object(ci, 'client_digest', return_value='same'), \
                 patch.object(ci, 'snapshot') as snapshot:
                ci.resolve()
            snapshot.assert_not_called()
            self.assertIn('build=false', output.read_text())


    def test_build_requests_curated_outputs_of_every_batch_member(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
            with patch.object(ci, 'snapshot', return_value={'needed': ['a', 'b']}), \
                 patch.object(ci, 'options', return_value=[]), \
                 patch.object(ci, 'run', return_value='/nix/store/' + 'a' * 32 + '-a') as run:
                ci.build(['a', 'b'], 'a' * 40)
            args = run.call_args.args
            self.assertIn('outputs.a', args)
            self.assertIn('outputs.b', args)



if __name__ == '__main__':
    unittest.main()


class GitSourceTests(unittest.TestCase):
    def test_heads_become_immutable_archive_urls(self):
        rev = 'b' * 40
        with patch.object(ci, 'run', return_value='ref: refs/heads/master\tHEAD\n' + rev + '\tHEAD'):
            heads = ci.git_heads({'kwin': 'plasma/kwin'})
        self.assertEqual(heads['kwin']['revision'], rev)
        self.assertEqual(heads['kwin']['url'], f'https://invent.kde.org/plasma/kwin/-/archive/{rev}/kwin-{rev}.tar.gz')

    def test_missing_remote_head_is_rejected(self):
        with patch.object(ci, 'run', return_value=''):
            with self.assertRaisesRegex(RuntimeError, 'Cannot resolve'):
                ci.git_heads({'kwin': 'plasma/kwin'})

    def test_unchanged_commit_reuses_its_hash(self):
        head = {'revision': 'a' * 40, 'url': 'https://example.invalid/archive'}
        old = {**head, 'sha256': 'known', 'version': '6.8.80-git.aaaaaaaaaaaa'}
        with patch.object(ci, 'run') as run:
            result = ci.git_sources({'kwin': head}, {'kwin': old}, {})
        run.assert_not_called()
        self.assertEqual(result['kwin'], old)

    def test_core_dependency_requirement_cannot_be_bypassed(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'CMakeLists.txt').write_text('set(PROJECT_VERSION "6.8.80")\nset(QT_MIN_VERSION "6.12.0")\n')
            with patch.object(ci, 'run', return_value='hash\n' + directory):
                with self.assertRaisesRegex(RuntimeError, 'needs qt 6.12.0'):
                    ci.git_sources({'kwin': {'revision': 'a' * 40, 'url': 'archive'}}, {},
                                   {'version': '6.7.90', 'dependencies': {'qt': '6.11.2', 'frameworks': '6.30.0'}})

    def test_version_comes_from_development_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'CMakeLists.txt').write_text('set(PROJECT_VERSION "6.8.80")\n')
            with patch.object(ci, 'run', return_value='hash\n' + directory):
                result = ci.git_sources({'kwin': {'revision': 'a' * 40, 'url': 'archive'}}, {},
                                       {'version': '6.7.90', 'dependencies': {'qt': '6.11.2', 'frameworks': '6.30.0'}})
        self.assertEqual(result['kwin']['version'], '6.8.80-git.aaaaaaaaaaaa')
