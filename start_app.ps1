$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$logDirectory = Join-Path $projectRoot 'artifacts\runtime-logs'

function Test-LocalUrl([string]$url) {
    try { return (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200 }
    catch { return $false }
}

function Start-ServiceIfNeeded([string]$name, [int]$port, [scriptblock]$start, [string]$healthUrl) {
    if (Test-LocalUrl $healthUrl) {
        Write-Host "$name is already running at $healthUrl" -ForegroundColor Green
        return
    }
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use, but $name is not responding. Close the application using that port, then run Start_App.cmd again."
    }
    & $start
}

if (!(Test-Path -LiteralPath $python)) { throw 'Python environment is missing. Run: .\.venv\Scripts\python.exe -m pip install -e .' }
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

# Keep the local CrossEncoder startup stable on Windows machines with limited
# native thread/virtual-memory capacity. These settings affect only the child
# API process; retrieval models and their configured names remain unchanged.
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:TOKENIZERS_PARALLELISM = 'false'

Start-ServiceIfNeeded 'PortProject API' 8001 {
    Start-Process -FilePath $python -ArgumentList '-m','portproject_rag.server' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory 'api.out.log') -RedirectStandardError (Join-Path $logDirectory 'api.error.log')
} 'http://127.0.0.1:8001/health'

Start-ServiceIfNeeded 'React UI' 5173 {
    Start-Process -FilePath $npm -ArgumentList 'run','dev','--','--host','127.0.0.1' -WorkingDirectory (Join-Path $projectRoot 'web') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDirectory 'web.out.log') -RedirectStandardError (Join-Path $logDirectory 'web.error.log')
} 'http://127.0.0.1:5173/'

for ($attempt = 1; $attempt -le 90; $attempt++) {
    if ((Test-LocalUrl 'http://127.0.0.1:8001/health') -and (Test-LocalUrl 'http://127.0.0.1:5173/')) { break }
    Start-Sleep -Seconds 1
}

if (!(Test-LocalUrl 'http://127.0.0.1:8001/health')) { throw "API did not start. Check $logDirectory\api.error.log" }
if (!(Test-LocalUrl 'http://127.0.0.1:5173/')) { throw "React UI did not start. Check $logDirectory\web.error.log" }

Write-Host 'PortProject RAG is running.' -ForegroundColor Green
Write-Host 'Open: http://127.0.0.1:5173'
Start-Process 'http://127.0.0.1:5173'
