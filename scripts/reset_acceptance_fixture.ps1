param(
    [string]$AcceptanceEnvFile = ".env.acceptance"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root $AcceptanceEnvFile
. (Join-Path $root "scripts\load_acceptance_env.ps1") -AcceptanceEnvFile $AcceptanceEnvFile
& (Join-Path $root ".venv\Scripts\python.exe") (Join-Path $root "scripts\acceptance_fixture.py") reset
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
