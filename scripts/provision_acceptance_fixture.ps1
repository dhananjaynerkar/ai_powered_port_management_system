param(
    [string]$AcceptanceEnvFile = ".env.acceptance"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root $AcceptanceEnvFile
if (-not $env:PORTPROJECT_RAG_ACCEPTANCE_ADMIN_DATABASE_URL) {
    throw "Set PORTPROJECT_RAG_ACCEPTANCE_ADMIN_DATABASE_URL in the private process environment before provisioning. It must target a maintenance database, never portproject."
}
. (Join-Path $root "scripts\load_acceptance_env.ps1") -AcceptanceEnvFile $AcceptanceEnvFile
& (Join-Path $root ".venv\Scripts\python.exe") (Join-Path $root "scripts\acceptance_fixture.py") provision
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
