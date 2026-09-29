# One-command install on Windows: uv (if missing), the dsa-kit tool, then VS Code setup.
#   irm https://raw.githubusercontent.com/ahrazarfi/dsa-kit/main/install.ps1 | iex
$ErrorActionPreference = 'Stop'

$repo = 'git+https://github.com/ahrazarfi/dsa-kit'
$uvBin = Join-Path $env:USERPROFILE '.local\bin'
if ($env:Path -notlike "*$uvBin*") { $env:Path = "$uvBin;$env:Path" }

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host 'uv not found, installing it ...'
    powershell -NoProfile -ExecutionPolicy Bypass -Command 'irm https://astral.sh/uv/install.ps1 | iex'
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Error 'uv installed but not on PATH; open a new terminal and rerun.'; exit 1
    }
}

uv tool install --force $repo
uv tool update-shell

$bin = (uv tool dir --bin).Trim()
& (Join-Path $bin 'dsa.exe') setup --yes

Write-Host @'

Installed. Open a new terminal (so PATH is refreshed), then:

    mkdir my-problems; cd my-problems
    new two-sum

Check the setup any time with: dsa doctor
'@
