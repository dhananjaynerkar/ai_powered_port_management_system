param(
    [string]$AcceptanceEnvFile = ".env.acceptance",
    [int]$ApiPort = 8016,
    [int]$WebPort = 5180
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$null = Set-Location $root
$envFile = Join-Path $root $AcceptanceEnvFile
. (Join-Path $root "scripts\load_acceptance_env.ps1") -AcceptanceEnvFile $AcceptanceEnvFile
& (Join-Path $root ".venv\Scripts\python.exe") (Join-Path $root "scripts\acceptance_fixture.py") check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$normalServiceRunning = $false
try {
    $normalHealth = Invoke-WebRequest -Uri 'http://127.0.0.1:8001/health' -UseBasicParsing -TimeoutSec 2
    $normalServiceRunning = $normalHealth.StatusCode -eq 200
} catch {
    # Connection refusal/timeout is the expected safe state for the normal
    # service. Only an actual healthy response blocks acceptance startup.
}
if (-not $normalServiceRunning -and (Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue)) {
    $normalServiceRunning = $true
}
if ($normalServiceRunning) {
    throw 'The normal RAG API is already running on port 8001. Stop it before starting the isolated acceptance API.'
}
Write-Output "Start the API in one terminal:"
Write-Output ".\.venv\Scripts\python.exe -m uvicorn pms_api.app:create_runtime_app --factory --host 127.0.0.1 --port $ApiPort --workers 1"
Write-Output "Start the UI in another terminal:"
Write-Output "Set-Location web; npm run dev -- --host 127.0.0.1 --port $WebPort"
Write-Output "The API will now run in this terminal. Press Ctrl+C to stop it."
& (Join-Path $root ".venv\Scripts\python.exe") -m uvicorn pms_api.app:create_runtime_app --factory --host 127.0.0.1 --port $ApiPort --workers 1
