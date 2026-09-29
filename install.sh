#!/usr/bin/env sh
# One-command install: uv (if missing), the dsa-kit tool, then VS Code setup.
#   curl -LsSf https://raw.githubusercontent.com/ahrazarfi/dsa-kit/main/install.sh | sh
# Skip the questions (for scripts/CI):   ... | sh -s -- --yes      (or DSA_YES=1)
set -eu

REPO="git+https://github.com/ahrazarfi/dsa-kit"
YES="${DSA_YES:-0}"
for arg in "$@"; do
  case "$arg" in -y|--yes) YES=1 ;; esac
done

# ---- checks ----
if ! command -v git >/dev/null 2>&1; then
  cat >&2 <<'MSG'
git is required (the tool is installed from GitHub) but was not found. Install it, then rerun:
  Debian/Ubuntu: sudo apt install git      Fedora: sudo dnf install git
  macOS:         xcode-select --install    Windows: https://git-scm.com/download/win
MSG
  exit 1
fi
if ! command -v code >/dev/null 2>&1; then
  cat <<'MSG'
Note: VS Code's `code` command was not found. The tool will still install, but the editor setup needs VS Code:
  install it from https://code.visualstudio.com (macOS: run "Shell Command: Install 'code' command in PATH"
  from its command palette), then run `dsa setup`.
MSG
fi
if grep -qi microsoft /proc/version 2>/dev/null; then
  echo "WSL detected: this installs into WSL and edits your Windows-side VS Code settings. Don't also run the Windows installer."
fi

# ---- uv ----
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found, installing it ..."
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- https://astral.sh/uv/install.sh | sh
  else
    echo "Need curl or wget to install uv. See https://docs.astral.sh/uv/" >&2
    exit 1
  fi
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

# ---- the tool ----
uv tool install --force "$REPO"
uv tool update-shell || true
BIN="$(uv tool dir --bin)"

# ---- VS Code setup ----
if [ "$YES" = "1" ]; then
  "$BIN/dsa" setup --yes
elif (: < /dev/tty) 2>/dev/null; then
  printf "\nNext: configure VS Code (layout extension, run task, Ctrl+' shortcut, editor path).\nEvery edit is asked first and the original file is backed up. Continue? [Y/n] " > /dev/tty
  read -r answer < /dev/tty || answer=""
  case "$answer" in
    n|N|no|NO) echo "Skipped. Run 'dsa setup' whenever you want it." ;;
    *) "$BIN/dsa" setup < /dev/tty ;;
  esac
else
  "$BIN/dsa" setup --yes   # no terminal to ask on
fi

cat <<'MSG'

Installed. Three steps to finish:
  1. Open a NEW terminal (so the `new` and `dsa` commands are on PATH).
  2. Reload VS Code: Ctrl+Shift+P, then "Developer: Reload Window".
  3. Try the example:   mkdir my-problems && cd my-problems && dsa demo
Then for your own problems:   new two-sum
Anything wrong? Run:   dsa doctor
MSG
