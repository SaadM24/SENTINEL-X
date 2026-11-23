[CmdletBinding()]
param([string]$Run = "", [int]$Seed = 42, [switch]$Full, [switch]$Resume,
      [ValidateSet("cpu","cuda","auto")][string]$Device = "cpu",
      [ValidateSet("adfa","fixture")][string]$Sequence = "adfa")
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    if (!(Test-Path ".venv\Scripts\python.exe")) { & .\setup_windows.ps1 }
    $parameters = @("--mode", "research", "--seed", "$Seed", "--device", $Device, "--sequence", $Sequence)
    if ($Run) { $parameters += @("--run", $Run) }
    if ($Full) { $parameters += "--full" }
    if ($Resume) { $parameters += "--resume" }
    & .\.venv\Scripts\python.exe scripts/run_pipeline.py @parameters
    if ($LASTEXITCODE -ne 0) { throw "Research workflow failed. Read the latest attempt under results/workflow." }
} finally {
    Pop-Location
}
