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
    def test_unchanged_snapshot_skips_nix_evaluation(self):
        proof = {'revision': 'a' * 40, 'clientDigest': 'same'}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            with patch.dict(os.environ, GITHUB_OUTPUT=str(output)), \
                 patch.object(ci, 'cache'), \
                 patch.object(ci, 'published', return_value=proof), \
                 patch.object(ci, 'refresh_source', return_value=(proof['revision'], False)), \
                 patch.object(ci, 'client_digest', return_value='same'), \
                 patch.object(ci, 'package_info') as package_info:
                ci.resolve()
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
