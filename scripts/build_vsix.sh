#!/usr/bin/env bash
# Rebuild dsa/data/dsa-layout.vsix from extension/. Run after changing anything in extension/.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../extension"
npx --yes @vscode/vsce package --out ../dsa/data/dsa-layout.vsix
