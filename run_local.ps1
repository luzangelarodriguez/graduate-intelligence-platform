param(
    [int]$BackendPort = 8010,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Import-EnvFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return
    }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }
        $parts = $line.Split("=", 2)
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
}

Import-EnvFile ".env.development"

Write-Host "Graduate Intelligence Platform local runtime"
Write-Host "Backend API: http://127.0.0.1:$BackendPort/"
Write-Host "Health:      http://127.0.0.1:$BackendPort/api/health"

$backendArgs = @(
    "-m", "uvicorn",
    "graduate_intelligence_platform.backend.app.main:app",
    "--host", "127.0.0.1",
    "--port", "$BackendPort",
    "--reload"
)
Start-Process -FilePath "python" -ArgumentList $backendArgs -WorkingDirectory $Root -WindowStyle Hidden

$frontendDir = Join-Path $Root "graduate_intelligence_platform/frontend"
if (Test-Path (Join-Path $frontendDir "package.json")) {
    Write-Host "Frontend:    http://127.0.0.1:$FrontendPort/"
    $npmArgs = @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$FrontendPort")
    Start-Process -FilePath "npm" -ArgumentList $npmArgs -WorkingDirectory $frontendDir -WindowStyle Hidden
} else {
    Write-Host "Frontend:    no valid frontend package found"
}

Write-Host "Services started in background windows. Use Task Manager or Stop-Process for shutdown."
