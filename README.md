# dsa-kit

Tooling for DSA practice. Keep a folder that contains only problems; everything else
happens under the hood.

```
mkdir my-problems && cd my-problems
new two-sum          # scaffolds the problem and opens the 3-pane layout in VS Code
                     # edit input.txt, press Ctrl+', read output.txt
```

## Install (one command)

Linux / macOS / WSL:
```
curl -LsSf https://raw.githubusercontent.com/ahrazarfi/dsa-kit/main/install.sh | sh
```
Windows (PowerShell):
```
irm https://raw.githubusercontent.com/ahrazarfi/dsa-kit/main/install.ps1 | iex
```

This installs [uv](https://docs.astral.sh/uv/) if it's missing, installs the tool with
`uv tool install`, and runs `dsa setup --yes`. Then open a new terminal so PATH refreshes,
and reload VS Code. There is no per-project virtualenv and nothing is copied into your
problems folder.

Update: `uv tool upgrade dsa-kit`. Remove: `uv tool uninstall dsa-kit`.
Check everything: `dsa doctor`.

## What you get

| Command | Does |
|---|---|
| `new <name>` | Creates `<name>/` in the **current directory** with `solution.py`, `input.txt`, `expected.txt`, `output.txt` and opens the panes in VS Code. Reopens it if it exists. |
| `dsa run <file>` | Runs a solution (this is what Ctrl+' triggers). Failures print and exit non-zero, which pops the terminal open. |
| `dsa check [dir]` | Runs every problem under `dir` that has an `expected.txt` and prints a PASS/FAIL table. |
| `dsa setup` | Installs the VS Code extension, the run task and the Ctrl+' shortcut (asks before editing your config; `-y` skips the questions). |
| `dsa doctor` | Reports what is or isn't set up, with a fix for each. |

### What `dsa setup` changes

- Installs the bundled **DSA Layout** extension (`local.dsa-layout`).
- Adds `python.analysis.extraPaths` to your user `settings.json` (one inserted line, the rest of the file untouched) so the editor resolves `from dsa import run`.
- Adds a `run-current-python` task to your **user** `tasks.json` and a `ctrl+'` entry to
  your **user** `keybindings.json`. Existing entries are kept, an existing binding to the task
  is left as is, and the original file is saved as `*.bak` (comments in it aren't preserved).
- From **WSL** it edits the Windows-side VS Code config, where the editor UI keeps it.
  Run `dsa setup` inside WSL so the extension lands in the VS Code server.

## Writing a solution

```
input.txt        expected.txt (optional)
[1, 2, 3, 4, 5]  [3, 4, 5, 1, 2]
2
```
```python
from dsa import run

class Solution:
    def rotateArray(self, nums, k): ...

if __name__ == '__main__':
    run(Solution().rotateArray, in_place=True)
```
Paste just the class into LeetCode.

- **Pass:** silent, `output.txt` has your answer. **Fail:** every failing case is printed with
  its input, expected and got values.
- **Several test cases:** separate them with a blank line in `input.txt`, one line per case in
  `expected.txt`.
- **Input values** are JSON first (`null`, `true`), then Python literals, then a bare string,
  so `abcba` works unquoted. Quote a string that looks like a literal (`"123"`).
- **Expected values** use the same syntax as input; `output.txt` shows matrices one row per line.

| Problem | Call |
|---|---|
| Ordinary function | `run(Solution().solve)` |
| Edits its first argument, returns nothing | `run(..., in_place=True)` |
| Order of results doesn't matter | `run(..., unordered=True)` |
| Several valid answers | `run(..., check=lambda args, out: ...)`, no `expected.txt` needed |
| Floating point | `run(..., tol=1e-5)` |
| Linked list / tree arguments | `run(..., parse=[to_linked, None])` or `to_tree`, imported from `dsa`; `ListNode` / `TreeNode` results are converted back automatically |
| Design problems (LRUCache, ...) | `run_design(LRUCache)`: line 1 of `input.txt` is the operations, line 2 the arguments |

Not supported: interactive problems, Codeforces-style stdin, SQL. Solutions run in the tool's
own environment, so they can import the standard library and `dsa` only.

## How it works

`new` writes the folder path to `~/.dsa/open-request`. The extension (running in the same
environment as the VS Code window) watches that file, lays out `solution.py | input.txt /
output.txt`, and empties the file. If nothing picks it up within a second, `new` falls back to
`code -r` with plain tabs. Only the focused VS Code window reacts.

## Development

```
python -m pip install -e .
python -m unittest discover -s tests
./scripts/build_vsix.sh      # rebuild dsa/data/dsa-layout.vsix after editing extension/
```
The extension source is in `extension/`; the built `.vsix` is committed because it ships inside
the Python package.
