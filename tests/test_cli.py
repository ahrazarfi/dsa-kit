import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

from dsa import cli, vscode


class ScaffoldTests(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(cli.slugify('Two Sum'), 'two-sum')
        self.assertEqual(cli.slugify('  3Sum (v2)! '), '3sum-v2')
        self.assertEqual(cli.slugify('!!!'), '')

    def test_scaffold_creates_files_once(self):
        base = tempfile.mkdtemp()
        folder, created = cli.scaffold('Two Sum', base)
        self.assertTrue(created)
        self.assertEqual(sorted(os.listdir(folder)), ['expected.txt', 'input.txt', 'output.txt', 'solution.py'])
        with open(os.path.join(folder, 'solution.py')) as f:
            self.assertIn('from dsa import run', f.read())
        self.assertEqual(cli.scaffold('two-sum', base), (folder, False))

    def test_invalid_name(self):
        with self.assertRaises(SystemExit):
            cli.scaffold('???', tempfile.mkdtemp())


class RunAndCheckTests(unittest.TestCase):
    def make_problem(self, base, name, solve_body, input_text, expected):
        folder, _ = cli.scaffold(name, base)
        path = os.path.join(folder, 'solution.py')
        with open(path) as f:
            src = f.read().replace('def solve(self):\n        pass', 'def solve(self, n):\n        ' + solve_body)
        with open(path, 'w') as f:
            f.write(src)
        with open(os.path.join(folder, 'input.txt'), 'w') as f:
            f.write(input_text)
        with open(os.path.join(folder, 'expected.txt'), 'w') as f:
            f.write(expected)
        return folder

    def run_cli(self, *args, cwd=None):
        env = dict(os.environ, PYTHONPATH=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return subprocess.run([sys.executable, '-m', 'dsa'] + list(args), capture_output=True, text=True, cwd=cwd, env=env)

    def test_run_passes_and_writes_output(self):
        folder = self.make_problem(tempfile.mkdtemp(), 'double', 'return n * 2', '4\n', '8\n')
        r = self.run_cli('run', os.path.join(folder, 'solution.py'), cwd=tempfile.gettempdir())
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(folder, 'output.txt')) as f:
            self.assertEqual(f.read(), '8\n')

    def test_run_fail_exits_nonzero(self):
        folder = self.make_problem(tempfile.mkdtemp(), 'double', 'return n * 2', '4\n', '9\n')
        r = self.run_cli('run', os.path.join(folder, 'solution.py'))
        self.assertEqual(r.returncode, 1)
        self.assertIn('FAIL case 1/1', r.stderr)

    def test_check_summary(self):
        base = tempfile.mkdtemp()
        self.make_problem(base, 'good', 'return n', '1\n', '1\n')
        self.make_problem(base, 'bad', 'return n', '1\n', '2\n')
        folder, _ = cli.scaffold('unchecked', base)  # empty expected.txt: skipped
        r = self.run_cli('check', base)
        self.assertEqual(r.returncode, 1)
        self.assertIn('PASS  good', r.stdout)
        self.assertIn('FAIL  bad', r.stdout)
        self.assertNotIn('unchecked', r.stdout)
        self.assertIn('2 checked, 1 passed, 1 failed', r.stdout)


class VSCodeConfigTests(unittest.TestCase):
    def test_jsonc_comments_and_trailing_commas(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, 'k.json')
        with open(p, 'w') as f:
            f.write('// header\n[\n  {"key": "a", "args": "http://x//y",}, /* c */\n]\n')
        self.assertEqual(vscode.load_jsonc(p, []), [{'key': 'a', 'args': 'http://x//y'}])

    def test_keybinding_idempotent_and_keeps_existing(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, 'keybindings.json'), 'w') as f:
            f.write('// mine\n[{"key": "shift+enter", "command": "x"}]\n')
        self.assertEqual(vscode.ensure_keybinding(d), 'added')
        self.assertEqual(vscode.ensure_keybinding(d), 'ok')
        with open(os.path.join(d, 'keybindings.json')) as f:
            data = json.load(f)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['key'], 'shift+enter')

    def test_existing_binding_with_other_key_is_respected(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, 'keybindings.json'), 'w') as f:
            f.write('[{"key": "ctrl+oem_7", "command": "workbench.action.tasks.runTask", "args": "run-current-python"}]')
        self.assertEqual(vscode.ensure_keybinding(d), 'ok')

    def test_task_added_then_only_os_block_updated(self):
        d = tempfile.mkdtemp()
        self.assertEqual(vscode.ensure_task(d, '/a/dsa'), 'added')
        self.assertEqual(vscode.ensure_task(d, '/a/dsa'), 'ok')
        self.assertEqual(vscode.ensure_task(d, '/b/dsa'), 'updated')
        with open(os.path.join(d, 'tasks.json')) as f:
            task = json.load(f)['tasks'][0]
        self.assertEqual(task[vscode._os_key()]['command'], '/b/dsa')
        self.assertEqual(task['args'], ['run', '${file}'])

    def test_extra_path_preserves_existing_settings_text(self):
        d = tempfile.mkdtemp()
        original = '{\n    // keep me\n    "editor.fontSize": 14\n}\n'
        with open(os.path.join(d, 'settings.json'), 'w') as f:
            f.write(original)
        self.assertEqual(vscode.ensure_extra_path(d, '/x/site-packages'), 'added')
        self.assertEqual(vscode.ensure_extra_path(d, '/x/site-packages'), 'ok')
        with open(os.path.join(d, 'settings.json')) as f:
            text = f.read()
        self.assertIn('// keep me', text)
        data = vscode.load_jsonc(os.path.join(d, 'settings.json'), {})
        self.assertEqual(data['python.analysis.extraPaths'], ['/x/site-packages'])
        self.assertEqual(data['editor.fontSize'], 14)

    def test_windows_line_endings_are_kept(self):
        d = tempfile.mkdtemp()
        file = os.path.join(d, 'settings.json')
        with open(file, 'wb') as f:
            f.write(b'{\r\n    "a": 1\r\n}\r\n')
        vscode.ensure_extra_path(d, '/p')
        with open(file, 'rb') as f:
            raw = f.read()
        self.assertEqual(raw.count(b'\n'), raw.count(b'\r\n'))
        kb = os.path.join(d, 'keybindings.json')
        with open(kb, 'wb') as f:
            f.write(b'[\r\n]\r\n')
        vscode.ensure_keybinding(d)
        with open(kb, 'rb') as f:
            raw = f.read()
        self.assertEqual(raw.count(b'\n'), raw.count(b'\r\n'))

    def test_extra_path_appends_to_existing_list_and_handles_missing_file(self):
        d = tempfile.mkdtemp()
        self.assertEqual(vscode.ensure_extra_path(d, '/a'), 'added')
        self.assertEqual(vscode.ensure_extra_path(d, '/b'), 'added')
        self.assertEqual(vscode.load_jsonc(os.path.join(d, 'settings.json'), {})['python.analysis.extraPaths'], ['/a', '/b'])

    def test_bundled_vsix_is_valid(self):
        with zipfile.ZipFile(vscode.VSIX) as z:
            self.assertIn('extension/extension.js', z.namelist())
        self.assertRegex(vscode._vsix_version(), r'^\d+\.\d+\.\d+$')


if __name__ == '__main__':
    unittest.main()
