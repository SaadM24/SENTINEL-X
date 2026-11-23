[CmdletBinding()]
param([string]$Run = "local-smoke", [switch]$Resume)
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    & .\setup_windows.ps1
    $parameters = @("--mode", "smoke", "--tests", "--run", $Run)
    if ($Resume) { $parameters += "--resume" }
    & .\.venv\Scripts\python.exe scripts/run_pipeline.py @parameters
    if ($LASTEXITCODE -ne 0) { throw "Smoke workflow failed. See results/workflow/$Run." }
} finally {
    Pop-Location
}
