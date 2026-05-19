$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = Join-Path $root '.venv_software\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw "No se encontro la venv de SOFTWARE en $python"
}
& $python (Join-Path $root 'scrapers\unir_market_scraper.py') --ticjob-pages 12 --min-date 2024-01-01 --min-other-score 18
