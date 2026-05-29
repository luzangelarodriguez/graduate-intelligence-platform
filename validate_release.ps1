$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )
    Write-Host ""
    Write-Host "==> $Name"
    & $Command
}

Invoke-Step "Backend import check" {
    python -c "from graduate_intelligence_platform.backend.app.main import app; print(app.title)"
}

Invoke-Step "Pytest suite" {
    python -m pytest tests
}

Invoke-Step "Py compile backend/ml/scrapers/microcurriculum_engine" {
    $paths = @("backend", "graduate_intelligence_platform/backend/app", "ml", "scrapers", "microcurriculum_engine")
    $files = foreach ($path in $paths) {
        if (Test-Path $path) {
            Get-ChildItem $path -Recurse -Filter *.py -File |
                Where-Object {
                    $_.FullName -notmatch "\\(deps|vendor|__pycache__|node_modules|\.venv|\.pytest_cache)\\"
                } |
                Select-Object -ExpandProperty FullName
        }
    }
    if ($files.Count -gt 0) {
        python -m py_compile @files
    }
}

Invoke-Step "ML inference smoke test" {
    python ml/run_inference.py --title "Analista BI" --description "SQL Power BI Python Big Data visual analytics" --skills "sql,power bi,python,big data"
}

if (Test-Path "tests/fixtures/microcurriculum_sample.txt") {
    Invoke-Step "Microcurriculum sample smoke test" {
        python -m microcurriculum_engine.pipelines.process_microcurriculum tests/fixtures/microcurriculum_sample.txt --no-persist --output outputs/microcurriculum_release_validation.json
    }
}

if (Test-Path "storage/test_microcurriculos") {
    $pdf = Get-ChildItem "storage/test_microcurriculos" -Filter *.pdf -File | Select-Object -First 1
    if ($pdf) {
        Invoke-Step "Microcurriculum batch validation" {
            python -m microcurriculum_engine.evaluation.batch_validator --input-dir storage/test_microcurriculos
        }
    }
}

Write-Host ""
Write-Host "Release validation completed."
