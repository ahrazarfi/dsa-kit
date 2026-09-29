#!/usr/bin/env sh
# One-command install: uv (if missing), the dsa-kit tool, then VS Code setup.
#   curl -LsSf https://raw.githubusercontent.com/ahrazarfi/dsa-kit/main/install.sh | sh
set -eu

REPO="git+https://github.com/ahrazarfi/dsa-kit"
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

uv tool install --force "$REPO"
uv tool update-shell || true

BIN="$(uv tool dir --bin)"
"$BIN/dsa" setup --yes

cat <<'MSG'

Installed. Open a new terminal (so PATH is refreshed), then:

    mkdir my-problems && cd my-problems
    new two-sum

Check the setup any time with: dsa doctor
MSG
