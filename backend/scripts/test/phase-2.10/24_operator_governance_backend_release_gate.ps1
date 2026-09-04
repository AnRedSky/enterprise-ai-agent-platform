$ErrorActionPreference = "Stop"

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
Set-Location $backendRoot

function Get-ProtectedServiceSnapshot {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and (
                $_.CommandLine -match "uvicorn|app\.main|scheduler|worker|postgres|redis-server|redis-server\.exe"
            )
        } |
        Select-Object ProcessId, Name, CommandLine
}

$before = @(Get-ProtectedServiceSnapshot)
$beforeIds = @($before | ForEach-Object { $_.ProcessId })

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Operator Governance Backend Release Gate"
Write-Host "Scope: PostgreSQL Operator Governance -> Backend Regression -> migration/head"
Write-Host "Frontend tests/build are intentionally NOT executed here."
Write-Host "Warning policy: Python warnings are treated as test errors."
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Worker, Scheduler, PostgreSQL, or Redis."
Write-Host "Test data policy: tests generate and clean all identities and business facts; no manual IDs, tokens, or business data are required."
Write-Host "============================================================"

Write-Host "[1/4] Operator Governance PostgreSQL Acceptance"
& powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\database\01_operator_governance_idempotency_acceptance.ps1
$operatorExitCode = $LASTEXITCODE
if ($operatorExitCode -eq 2) {
    Write-Host "============================================================"
    Write-Host "[NOT RUN] Operator Governance PostgreSQL Acceptance requires a reachable configured PostgreSQL instance."
    Write-Host "[INFO] No protected service was started by this release gate."
    exit 2
}
if ($operatorExitCode -ne 0) {
    throw "Operator Governance PostgreSQL Acceptance failed. Backend Release Gate is blocked."
}

Write-Host "[2/4] Backend default regression with warning enforcement"
& uv run pytest -q -W error
if ($LASTEXITCODE -ne 0) {
    throw "Backend default regression failed. Backend Release Gate is blocked."
}

Write-Host "[3/4] Alembic migration/head verification"
& uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    throw "Alembic upgrade head failed. Backend Release Gate is blocked."
}
& uv run alembic current
if ($LASTEXITCODE -ne 0) {
    throw "Alembic current verification failed. Backend Release Gate is blocked."
}

Write-Host "[4/4] Protected service startup boundary"
$after = @(Get-ProtectedServiceSnapshot)
$created = @($after | Where-Object { $beforeIds -notcontains $_.ProcessId })
if ($created.Count -gt 0) {
    $created | Format-Table -AutoSize | Out-String | Write-Host
    throw "Service startup boundary violated: a protected service process appeared during the gate."
}

Write-Host "============================================================"
Write-Host "[PASS] Phase 2.10-II Operator Governance Backend Release Gate completed."
Write-Host "[PASS] Operator Governance PostgreSQL Acceptance passed."
Write-Host "[PASS] Backend regression passed with warnings treated as errors."
Write-Host "[PASS] Alembic head/current verification passed."
Write-Host "[PASS] No protected service process was created by this gate."
Write-Host "============================================================"
