[CmdletBinding()]
param([string]$PythonExe = "")
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    $venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (!(Test-Path $venvPython)) {
        if ($PythonExe) {
            & $PythonExe -m venv .venv
        } elseif (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3.11 -m venv .venv
        } else {
            & python -m venv .venv
        }
        if ($LASTEXITCODE -ne 0) { throw "Install 64-bit Python 3.11 or pass -PythonExe pointing to its executable." }
    }
    & $venvPython -c "import sys,struct; assert (3,11)<=sys.version_info[:2]<=(3,13) and struct.calcsize('P')==8, 'Requires 64-bit Python 3.11 to 3.13'"
    if ($LASTEXITCODE -ne 0) { throw "The existing .venv uses an unsupported Python. Move it and rerun setup." }
    & $venvPython -m pip install -r requirements/research.txt -e ".[test]"
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed. Check PyPI connectivity and free disk space." }
    & $venvPython scripts/check_environment.py --require-tests
    if ($LASTEXITCODE -ne 0) { throw "Environment check failed." }
} finally {
    Pop-Location
}
