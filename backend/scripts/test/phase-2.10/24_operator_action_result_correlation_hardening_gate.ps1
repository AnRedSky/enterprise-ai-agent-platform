$ErrorActionPreference = "Stop"
$backendRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
Set-Location $backendRoot

function Get-ServiceProcessSnapshot {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and (
                $_.CommandLine -match "uvicorn|app\.main|scheduler|worker|postgres|redis-server|redis-server\.exe"
            )
        } |
        Select-Object ProcessId, Name, CommandLine
}

$beforeServices = @(Get-ServiceProcessSnapshot)

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Operator Action Result Correlation Hardening Gate"
Write-Host "============================================================"
Write-Host "[0/5] Local precondition checks"
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: unit tests generate all identifiers automatically; PostgreSQL acceptance creates no business fixtures."
Write-Host "Service startup is a boundary check only; missing services are never auto-started."

Write-Host "[1/5] Migration/head verification"
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current failed." }
uv run alembic heads
if ($LASTEXITCODE -ne 0) { throw "Alembic heads failed." }

Write-Host "[2/5] Migration upgrade verification"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade head failed." }

Write-Host "[3/5] Operator Action result correlation unit regression"
uv run pytest -q tests/unit/test_operator_action_result_correlation.py tests/unit/test_runtime_audit_trace_correlation.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Operator Action result correlation unit regression failed." }

Write-Host "[4/5] PostgreSQL schema acceptance"
uv run pytest -q tests/api_real/test_operator_action_result_correlation_acceptance.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Operator Action result correlation PostgreSQL acceptance failed." }

Write-Host "[5/5] Service startup boundary"
$afterServices = @(Get-ServiceProcessSnapshot)
$beforeIds = @($beforeServices | ForEach-Object { $_.ProcessId })
$created = @($afterServices | Where-Object { $beforeIds -notcontains $_.ProcessId })

if ($created.Count -gt 0) {
    $created | Format-Table -AutoSize | Out-String | Write-Host
    throw "Service startup boundary violated: a protected service process appeared during the gate."
}

Write-Host "[PASS] No protected service process appeared during the gate."
Write-Host "[PASS] No API/Scheduler/Worker/PostgreSQL/Redis process was intentionally created, started, restarted, or stopped by this gate."
Write-Host "[PASS] Operator Action Result Correlation Hardening Gate completed."
