"""VS Code integration: user-level task + keybinding, and installing the layout extension."""
import glob
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile

TASK_LABEL = 'run-current-python'
EXT_NAME = 'local.dsa-layout'
VSIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'dsa-layout.vsix')
KEYBINDING = {'key': "ctrl+'", 'command': 'workbench.action.tasks.runTask', 'args': TASK_LABEL}

_STRING_OR_COMMENT = re.compile(r'("(?:\\.|[^"\\])*")|//[^\n]*|/\*.*?\*/', re.S)
_TRAILING_COMMA = re.compile(r'("(?:\\.|[^"\\])*")|,(\s*[\]}])')


def _os_key():
    if os.name == 'nt':
        return 'windows'
    return 'osx' if sys.platform == 'darwin' else 'linux'


def _is_wsl():
    return 'microsoft' in platform.uname().release.lower()


def user_dir():
    """VS Code's User folder. From WSL that is the Windows side, where the editor UI keeps its config."""
    if os.environ.get('DSA_VSCODE_USER_DIR'):
        return os.environ['DSA_VSCODE_USER_DIR']
    if os.name == 'nt':
        return os.path.join(os.environ['APPDATA'], 'Code', 'User')
    if sys.platform == 'darwin':
        return os.path.expanduser('~/Library/Application Support/Code/User')
    if _is_wsl():
        try:
            appdata = subprocess.run(['cmd.exe', '/c', 'echo %APPDATA%'], capture_output=True, text=True,
                                     cwd='/mnt/c', timeout=10).stdout.strip()
            path = subprocess.run(['wslpath', appdata], capture_output=True, text=True, timeout=10).stdout.strip()
            if path and os.path.isdir(path):
                return os.path.join(path, 'Code', 'User')
        except (OSError, subprocess.SubprocessError):
            pass
        found = glob.glob('/mnt/c/Users/*/AppData/Roaming/Code/User')
        if len(found) == 1:
            return found[0]
    return os.path.expanduser('~/.config/Code/User')


def load_jsonc(path, default):
    """Read a VS Code JSON file (comments and trailing commas allowed)."""
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8-sig') as f:
        text = f.read()
    if not text.strip():
        return default
    text = _STRING_OR_COMMENT.sub(lambda m: m.group(1) or '', text)
    text = _TRAILING_COMMA.sub(lambda m: m.group(1) or m.group(2), text)
    return json.loads(text)


def _newline(path):
    """The line ending an existing file uses ('\r\n' for files edited on Windows), else '\n'."""
    if os.path.exists(path):
        with open(path, 'rb') as f:
            if b'\r\n' in f.read(4096):
                return '\r\n'
    return '\n'


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    newline = _newline(path)
    if os.path.exists(path):
        shutil.copyfile(path, path + '.bak')  # comments in the original are not preserved
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(json.dumps(data, indent=4).replace('\n', newline) + newline)


def ensure_task(folder, dsa_exe):
    """Add the run task (or refresh this OS's command). Returns 'added', 'updated' or 'ok'."""
    path = os.path.join(folder, 'tasks.json')
    data = load_jsonc(path, {'version': '2.0.0', 'tasks': []})
    tasks = data.setdefault('tasks', [])
    task = next((t for t in tasks if t.get('label') == TASK_LABEL), None)
    status = 'ok'
    if task is None:
        task = {
            'label': TASK_LABEL,
            'type': 'process',
            'command': 'dsa',
            'args': ['run', '${file}'],
            'presentation': {'reveal': 'silent', 'panel': 'shared', 'clear': True, 'showReuseMessage': False},
            'problemMatcher': ['$python'],
        }
        tasks.append(task)
        status = 'added'
    block = task.setdefault(_os_key(), {})
    if block.get('command') != dsa_exe:
        block['command'] = dsa_exe  # absolute path: VS Code's PATH often lacks ~/.local/bin
        status = 'updated' if status == 'ok' else status
    if status != 'ok':
        save_json(path, data)
    return status


def ensure_keybinding(folder):
    """Bind Ctrl+' to the task unless something already runs it. Returns 'added', 'ok' or 'conflict'."""
    path = os.path.join(folder, 'keybindings.json')
    data = load_jsonc(path, [])
    if any(k.get('command') == KEYBINDING['command'] and k.get('args') == TASK_LABEL for k in data):
        return 'ok'
    if any(k.get('key') in ("ctrl+'", 'ctrl+oem_7') and not str(k.get('command', '')).startswith('-') for k in data):
        return 'conflict'  # the user already bound that key to something else
    data.append(dict(KEYBINDING))
    save_json(path, data)
    return 'added'


EXTRA_PATHS_KEY = 'python.analysis.extraPaths'


def package_path():
    """Folder that contains the installed `dsa` package (the tool's site-packages)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ensure_extra_path(folder, path=None):
    """Let Pylance resolve `from dsa import run` by adding the package folder to
    python.analysis.extraPaths in the user settings. Returns 'added' or 'ok'."""
    path = path or package_path()
    file = os.path.join(folder, 'settings.json')
    data = load_jsonc(file, {})
    current = data.get(EXTRA_PATHS_KEY)
    if current and path in current:
        return 'ok'
    if current is None and os.path.exists(file):
        # key absent: insert one line and leave the rest of the user's file (comments included) untouched
        newline = _newline(file)
        with open(file, encoding='utf-8-sig', newline='') as f:
            text = f.read()
        head = text.index('{')
        rest = text[head + 1:]
        line = '%s    "%s": %s,' % (newline, EXTRA_PATHS_KEY, json.dumps([path]))
        if rest.lstrip().startswith('}'):
            line = line.rstrip(',')
        shutil.copyfile(file, file + '.bak')
        with open(file, 'w', encoding='utf-8', newline='') as f:
            f.write(text[:head + 1] + line + rest)
        return 'added'
    data[EXTRA_PATHS_KEY] = (current or []) + [path]
    save_json(file, data)
    return 'added'


def _extension_dirs():
    return [d for d in (os.path.expanduser('~/.vscode-server/extensions'), os.path.expanduser('~/.vscode/extensions'))
            if os.path.isdir(d)]


def _vsix_version():
    with zipfile.ZipFile(VSIX) as z:
        return json.loads(z.read('extension/package.json'))['version']


def install_extension():
    """Install the bundled layout extension. Returns a short description of what happened."""
    version = _vsix_version()
    for base in _extension_dirs():  # drop older copies so two versions never both react
        for old in glob.glob(os.path.join(base, EXT_NAME + '-*')):
            if not old.endswith('-' + version):
                shutil.rmtree(old, ignore_errors=True)
    code = shutil.which('code')
    if code:
        try:
            r = subprocess.run([code, '--install-extension', VSIX, '--force'], capture_output=True, text=True,
                               timeout=120)
            if r.returncode == 0:
                return 'installed with `code --install-extension`'
        except (OSError, subprocess.SubprocessError):
            pass
    copied = []
    with zipfile.ZipFile(VSIX) as z:
        for base in _extension_dirs():
            target = os.path.join(base, '%s-%s' % (EXT_NAME, version))
            shutil.rmtree(target, ignore_errors=True)
            for name in z.namelist():
                if name.startswith('extension/') and not name.endswith('/'):
                    dest = os.path.join(target, name[len('extension/'):])
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    with open(dest, 'wb') as f:
                        f.write(z.read(name))
            copied.append(base)
    if copied:
        return 'copied into ' + ', '.join(copied)
    return None


def extension_present():
    version = _vsix_version()
    return any(os.path.isdir(os.path.join(b, '%s-%s' % (EXT_NAME, version))) for b in _extension_dirs())
