"""Command line: `new`, and `dsa run | setup | doctor | check | new`."""
import argparse
import os
import re
import runpy
import shutil
import subprocess
import sys
import time

from . import vscode

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
REQUEST_FILE = os.path.join(os.path.expanduser('~'), '.dsa', 'open-request')


def slugify(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def scaffold(name, base):
    """Create <base>/<slug>/ with the four files. Returns (folder, created)."""
    slug = slugify(name)
    if not slug:
        raise SystemExit('Invalid problem name')
    folder = os.path.join(base, slug)
    if os.path.exists(folder):
        return folder, False
    os.makedirs(folder)
    with open(os.path.join(DATA, 'solution_template.py'), newline='') as src:
        template = src.read()
    with open(os.path.join(folder, 'solution.py'), 'w', newline='\n') as f:
        f.write(template)
    for name in ('input.txt', 'expected.txt', 'output.txt'):
        open(os.path.join(folder, name), 'w').close()
    return folder, True


def open_in_vscode(folder):
    """Ask the layout extension to arrange the panes; fall back to plain tabs via `code`."""
    os.makedirs(os.path.dirname(REQUEST_FILE), exist_ok=True)
    with open(REQUEST_FILE, 'w') as f:
        f.write(folder)
    deadline = time.time() + 1.0
    while time.time() < deadline:
        if os.path.getsize(REQUEST_FILE) == 0:
            return  # the extension took it
        time.sleep(0.05)
    open(REQUEST_FILE, 'w').close()
    code = shutil.which('code')
    if code:
        subprocess.run([code, '-r'] + [os.path.join(folder, n) for n in ('solution.py', 'input.txt', 'output.txt')])


HINT_MARKER = os.path.join(os.path.expanduser('~'), '.dsa', 'seen-hint')
HINT = """
How it works (shown once):
  1. Put the arguments in input.txt, one per line, e.g.   [2, 7, 11, 15]   then   9   on the next line
  2. Optional: put the expected answer in expected.txt, e.g.   [0, 1]
  3. Press Ctrl+' (or run `dsa run solution.py`). The answer lands in output.txt;
     a wrong answer pops the terminal open with expected vs got.
  Try `dsa demo` to see a finished example. More options: `dsa doctor`, and the README.
"""


def _show_hint_once():
    if os.path.exists(HINT_MARKER):
        return
    print(HINT)
    os.makedirs(os.path.dirname(HINT_MARKER), exist_ok=True)
    open(HINT_MARKER, 'w').close()


def demo(base=None):
    """Create a finished Two Sum example, run it once, and open it."""
    base = base or os.getcwd()
    folder = os.path.join(base, 'demo-two-sum')
    if os.path.exists(folder):
        raise SystemExit("'demo-two-sum' already exists here; delete it first or run `dsa demo` elsewhere.")
    os.makedirs(folder)
    for name in ('solution.py', 'input.txt', 'expected.txt'):
        shutil.copyfile(os.path.join(DATA, 'demo', name), os.path.join(folder, name))
    open(os.path.join(folder, 'output.txt'), 'w').close()
    run_file(os.path.join(folder, 'solution.py'))
    with open(os.path.join(folder, 'output.txt')) as f:
        answer = f.read().strip()
    print('Created %s' % folder)
    print('Ran it: output.txt now holds "%s" and it matches expected.txt.' % answer)
    print("Now edit input.txt or expected.txt (e.g. make expected.txt wrong) and press Ctrl+' to see a failure.")
    open_in_vscode(folder)


def new_main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    name = ' '.join(argv).strip() or input('Problem name: ').strip()
    folder, created = scaffold(name, os.getcwd())
    print('Created %s' % folder if created else "'%s' already exists, opening it." % os.path.basename(folder))
    open_in_vscode(folder)
    if created:
        _show_hint_once()


def run_file(path):
    """Run a solution file the way `python file.py` would, but inside dsa's own environment."""
    path = os.path.abspath(path)
    sys.argv = [path]
    sys.path.insert(0, os.path.dirname(path))
    runpy.run_path(path, run_name='__main__')


def _confirm(question, yes):
    if yes:
        return True
    try:
        return input(question + ' [Y/n] ').strip().lower() in ('', 'y', 'yes')
    except EOFError:
        return False


def setup(yes=False, folder=None):
    folder = folder or vscode.user_dir()
    dsa_exe = shutil.which('dsa') or os.path.abspath(sys.argv[0])
    print('VS Code user folder: %s' % folder)
    print('dsa command:         %s' % dsa_exe)
    if vscode._is_wsl():
        print('WSL detected: VS Code settings live on the Windows side, so that is where they are edited. '
              'Run this inside WSL (not from Windows) so the extension goes into the WSL VS Code server.')
    if not shutil.which('code'):
        print("Note: the `code` command was not found. Install VS Code (https://code.visualstudio.com), then "
              "on Windows tick 'Add to PATH' in the installer, or on macOS run 'Shell Command: Install code "
              "command in PATH' from the command palette, and rerun `dsa setup`.")

    print('Layout extension: ', end='')
    print(vscode.install_extension() or 'NOT installed: no VS Code extensions folder was found. Install VS Code '
          'and open it once, or add the extension by hand from %s' % vscode.VSIX)

    for label, fn, arg in (('run task', vscode.ensure_task, dsa_exe), ("Ctrl+' shortcut", vscode.ensure_keybinding, None),
                           ('editor import path', vscode.ensure_extra_path, None)):
        if _confirm('Add the %s to %s?' % (label, folder), yes):
            try:
                status = fn(folder, arg) if arg else fn(folder)
                print('%s: %s' % (label, status if status != 'conflict' else
                                  "skipped, Ctrl+' is already bound to something else in your keybindings. Bind another "
                                  "key to the command workbench.action.tasks.runTask with args \"%s\" yourself." %
                                  vscode.TASK_LABEL))
            except ValueError as e:
                print('%s: could not parse the existing file (%s); add it by hand, see the README.' % (label, e))
        else:
            print('%s: skipped' % label)
    print('\nDone. Now: (1) open a NEW terminal so the commands are on PATH, (2) reload VS Code '
          '(Ctrl+Shift+P, "Developer: Reload Window") so the extension activates, (3) try `dsa demo`.')


def doctor():
    ok = True

    def check(label, passed, fix=''):
        nonlocal ok
        ok = ok and passed
        print('%s %s%s' % ('ok ' if passed else 'FAIL', label, '' if passed else '  ->  ' + fix))

    check('dsa on PATH', bool(shutil.which('dsa')), 'run `uv tool update-shell` and open a new terminal')
    check('new on PATH', bool(shutil.which('new')), 'run `uv tool update-shell` and open a new terminal')
    check('`code` on PATH', bool(shutil.which('code')), 'only needed for the fallback; add VS Code to PATH')
    check('layout extension installed', vscode.extension_present(), 'run `dsa setup`')
    folder = vscode.user_dir()
    try:
        tasks = vscode.load_jsonc(os.path.join(folder, 'tasks.json'), {}).get('tasks', [])
        check('run task in %s' % folder, any(t.get('label') == vscode.TASK_LABEL for t in tasks), 'run `dsa setup`')
        keys = vscode.load_jsonc(os.path.join(folder, 'keybindings.json'), [])
        check("Ctrl+' shortcut", any(k.get('args') == vscode.TASK_LABEL for k in keys), 'run `dsa setup`')
        paths = vscode.load_jsonc(os.path.join(folder, 'settings.json'), {}).get(vscode.EXTRA_PATHS_KEY) or []
        check('editor resolves `from dsa import run`', vscode.package_path() in paths, 'run `dsa setup`')
    except ValueError as e:
        check('user config readable', False, str(e))
    return 0 if ok else 1


def check_all(root):
    """Run every solution under root that has a non-empty expected.txt and print a table."""
    results = []
    for folder, _dirs, files in sorted(os.walk(root)):
        if 'solution.py' not in files or 'expected.txt' not in files:
            continue
        if not open(os.path.join(folder, 'expected.txt')).read().strip():
            continue
        r = subprocess.run([sys.executable, '-m', 'dsa', 'run', os.path.join(folder, 'solution.py')],
                           capture_output=True, text=True)
        status = 'PASS' if r.returncode == 0 else 'FAIL'
        results.append((status, os.path.relpath(folder, root), r.stderr.strip()))
    for status, name, err in results:
        print('%s  %s' % (status, name))
        if status == 'FAIL':
            print('\n'.join('      ' + line for line in err.splitlines()))
    failed = sum(1 for s, _, _ in results if s == 'FAIL')
    print('\n%d checked, %d passed, %d failed' % (len(results), len(results) - failed, failed))
    return 1 if failed else 0


def main(argv=None):
    p = argparse.ArgumentParser(prog='dsa', description='Scaffold, run and check DSA practice problems.')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('new', help='same as the `new` command').add_argument('name', nargs='*')
    sub.add_parser('run', help='run a solution file (what Ctrl+\' does)').add_argument('file')
    s = sub.add_parser('setup', help='install the VS Code extension, run task and shortcut')
    s.add_argument('-y', '--yes', action='store_true', help="don't ask before editing VS Code's user config")
    s.add_argument('--user-dir', help="VS Code's User folder (auto-detected by default)")
    sub.add_parser('doctor', help='check that everything is set up')
    sub.add_parser('demo', help='create and run a finished example problem here')
    sub.add_parser('check', help='run every problem that has an expected.txt').add_argument('dir', nargs='?', default='.')
    a = p.parse_args(argv)
    if a.cmd == 'new':
        new_main(a.name)
    elif a.cmd == 'run':
        run_file(a.file)
    elif a.cmd == 'setup':
        setup(a.yes, a.user_dir)
    elif a.cmd == 'demo':
        demo()
    elif a.cmd == 'doctor':
        sys.exit(doctor())
    elif a.cmd == 'check':
        sys.exit(check_all(a.dir))
