param(
    [string]$AcceptanceEnvFile = ".env.acceptance"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root $AcceptanceEnvFile
if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Missing $AcceptanceEnvFile. Copy .env.acceptance.example to .env.acceptance and set only the private acceptance database URL."
}
Get-Content -LiteralPath $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
        $parts = $line.Split('=', 2)
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim().Trim('"').Trim("'"), 'Process')
    }
}
# Acceptance tests are opt-in so a plain project-wide pytest run cannot
# mutate the isolated database or consume shared fixture state accidentally.
[Environment]::SetEnvironmentVariable('PORTPROJECT_RAG_RUN_ACCEPTANCE_TESTS', '1', 'Process')
Write-Output "Acceptance environment loaded for this PowerShell process."
