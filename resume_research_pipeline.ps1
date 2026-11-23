[CmdletBinding()]
param([string]$Run = "", [int]$Seed = 42, [switch]$Full,
      [ValidateSet("cpu","cuda","auto")][string]$Device = "cpu",
      [ValidateSet("adfa","fixture")][string]$Sequence = "adfa")
$ErrorActionPreference = "Stop"
& "$PSScriptRoot\run_research_pipeline.ps1" -Run $Run -Seed $Seed -Full:$Full -Device $Device -Sequence $Sequence -Resume
