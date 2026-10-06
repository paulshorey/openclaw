#!/usr/bin/env python3
"""Provider-free tests for the map's shell-only environment boundary."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("project_env", Path(__file__).with_name("project-env.py"))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class EnvironmentTests(unittest.TestCase):
    def test_shell_only_never_loads_dotenv_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.env').write_text('PROJECT_SECRET=dotenv\n')
            (root / '.env.example').write_text('PROJECT_SECRET=\n')
            with patch.object(helper, 'project_root', return_value=root), \
                 patch.object(helper, 'login_environment', return_value={'PROJECT_SECRET': 'shell'}), \
                 patch.dict(os.environ, {}, clear=True):
                env, files, declared = helper.build_environment(root, set(), shell_only=True)
                self.assertEqual(env['PROJECT_SECRET'], 'shell')
                self.assertEqual(files, [])
                self.assertIn('PROJECT_SECRET', declared)

    def test_other_projects_retain_dotenv_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.env').write_text('PROJECT_SECRET=dotenv\n')
            with patch.object(helper, 'project_root', return_value=root), \
                 patch.object(helper, 'login_environment', return_value={'PROJECT_SECRET': 'shell'}), \
                 patch.dict(os.environ, {}, clear=True):
                env, files, _ = helper.build_environment(root, set())
                self.assertEqual(env['PROJECT_SECRET'], 'dotenv')
                self.assertEqual(files, [root / '.env'])


if __name__ == '__main__':
    unittest.main()
