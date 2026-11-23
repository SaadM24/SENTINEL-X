[CmdletBinding()]
param([ValidateRange(1024,65535)][int]$Port = 8765)
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    if (!(Test-Path ".venv\Scripts\python.exe")) { & .\setup_windows.ps1 }
    Write-Host "Open http://127.0.0.1:$Port in your browser. Press Ctrl+C to stop."
    & .\.venv\Scripts\python.exe -m sentinel_x.dashboard --port $Port --root .
    if ($LASTEXITCODE -ne 0) { throw "Dashboard process failed." }
} finally {
    Pop-Location
}
