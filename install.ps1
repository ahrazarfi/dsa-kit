# One-command install on Windows: uv (if missing), the dsa-kit tool, then VS Code setup.
#   irm https://raw.githubusercontent.com/ahrazarfi/dsa-kit/main/install.ps1 | iex
# Skip the questions (for scripts):   $env:DSA_YES = '1'   before running it.
$ErrorActionPreference = 'Stop'

$repo = 'git+https://github.com/ahrazarfi/dsa-kit'

# ---- checks ----
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host 'git is required (the tool is installed from GitHub) but was not found.'
    Write-Host 'Install it (winget install Git.Git, or https://git-scm.com/download/win), open a new terminal, and rerun.'
    exit 1
}
if (-not (Get-Command code -ErrorAction SilentlyContinue)) {
    Write-Host "Note: VS Code's 'code' command was not found. The tool will still install, but the editor setup needs VS Code:"
    Write-Host "  install it from https://code.visualstudio.com and tick 'Add to PATH', then run 'dsa setup'."
}
if (Get-Command wsl -ErrorAction SilentlyContinue) {
    Write-Host 'Note: WSL is installed. If you use VS Code with WSL, run the Linux installer INSIDE WSL instead (it edits'
    Write-Host 'this same Windows VS Code config), and skip this one.'
}

# ---- uv ----
$uvBin = Join-Path $env:USERPROFILE '.local\bin'
if ($env:Path -notlike "*$uvBin*") { $env:Path = "$uvBin;$env:Path" }
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host 'uv not found, installing it ...'
    powershell -NoProfile -ExecutionPolicy Bypass -Command 'irm https://astral.sh/uv/install.ps1 | iex'
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Error 'uv installed but not on PATH; open a new terminal and rerun.'; exit 1
    }
}

# ---- the tool ----
uv tool install --force $repo
uv tool update-shell
$dsa = Join-Path ((uv tool dir --bin).Trim()) 'dsa.exe'

# ---- VS Code setup ----
if ($env:DSA_YES -eq '1') {
    & $dsa setup --yes
} else {
    $answer = Read-Host "`nNext: configure VS Code (layout extension, run task, Ctrl+' shortcut, editor path). Every edit is asked first and the original file is backed up. Continue? [Y/n]"
    if ($answer -match '^(n|no)$') { Write-Host "Skipped. Run 'dsa setup' whenever you want it." } else { & $dsa setup }
}

Write-Host @'

Installed. Three steps to finish:
  1. Open a NEW terminal (so the `new` and `dsa` commands are on PATH).
  2. Reload VS Code: Ctrl+Shift+P, then "Developer: Reload Window".
  3. Try the example:   mkdir my-problems; cd my-problems; dsa demo
Then for your own problems:   new two-sum
Anything wrong? Run:   dsa doctor
'@
