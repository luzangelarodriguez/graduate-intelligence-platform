$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = Join-Path $root '.venv_software\Scripts\python.exe'
if (-not (Test-Path $python)) {
    $python = 'python'
}
& $python (Join-Path $root 'scripts\run_daily_labor_acquisition.py') @args
