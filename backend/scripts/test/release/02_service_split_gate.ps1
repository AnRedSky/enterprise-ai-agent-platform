$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - API / Scheduler Service Split Gate"
Write-Host "Scope: process entrypoint boundary and API scheduler isolation"
Write-Host "============================================================"

Write-Host "[1/3] Targeted service boundary tests"
uv run pytest -q tests/unit/test_service_entrypoints.py
if ($LASTEXITCODE -ne 0) {
    throw "Service boundary unit tests failed."
}

Write-Host "[2/3] Verify API entrypoint import and Scheduler entrypoint import"
uv run python -c "from app.main import app; from app.entrypoints.scheduler import run_scheduler_service; print('SERVICE_ENTRYPOINT_IMPORT_OK')"
if ($LASTEXITCODE -ne 0) {
    throw "Service entrypoint import verification failed."
}

Write-Host "[3/3] Verify API process does not require Scheduler startup"
$env:SCHEDULER_ENABLED = "false"
$process = Start-Process -FilePath "uv" -ArgumentList "run python run.py" -WorkingDirectory (Get-Location) -PassThru -RedirectStandardOutput "$env:TEMP\enterprise-api-service.stdout.log" -RedirectStandardError "$env:TEMP\enterprise-api-service.stderr.log"
try {
    $deadline = (Get-Date).AddSeconds(20)
    $healthy = $false
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2
            if ($response.status -eq "ok" -and $response.service -eq "api") {
                $healthy = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $healthy) {
        throw "API Service health check did not return service=api."
    }

    $output = ""
    if (Test-Path "$env:TEMP\enterprise-api-service.stdout.log") {
        $output += Get-Content "$env:TEMP\enterprise-api-service.stdout.log" -Raw
    }
    if (Test-Path "$env:TEMP\enterprise-api-service.stderr.log") {
        $output += Get-Content "$env:TEMP\enterprise-api-service.stderr.log" -Raw
    }
    if ($output -match "Scheduler Service started|scheduled-trigger-scheduler") {
        throw "API Service unexpectedly started Scheduler."
    }

    Write-Host "[PASS] API Service is isolated from Scheduler startup."
} finally {
    if ($process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        Wait-Process -Id $process.Id -Timeout 5 -ErrorAction SilentlyContinue
    }
    Remove-Item Env:SCHEDULER_ENABLED -ErrorAction SilentlyContinue
}

Write-Host "============================================================"
Write-Host "[PASS] API / Scheduler Service Split Gate completed."
Write-Host "Scheduler runtime acceptance remains an independent gate."
Write-Host "============================================================"
