$ErrorActionPreference = 'Stop'

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$target = 'tests/unit/test_webhook_delivery_worker.py'

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Webhook Provider Unit Gate'
Write-Host 'Scope: offline provider contract, endpoint policy injection, HTTP outcome mapping'
Write-Host 'Service policy: this gate never starts, restarts, or stops API / Worker / Scheduler / DB / Redis.'
Write-Host '============================================================'

Push-Location $backendRoot
try {
    Write-Host '[1/3] Targeted Webhook Provider tests'
    & uv run pytest -q $target --maxfail=1 -x --tb=long
    if ($LASTEXITCODE -ne 0) {
        throw "Webhook Provider unit tests failed: $target"
    }

    Write-Host '[2/3] Backend collection/import smoke check'
    & uv run pytest --collect-only -q
    if ($LASTEXITCODE -ne 0) {
        throw 'Backend test collection failed. Do not continue to full regression.'
    }

    Write-Host '[3/3] Full backend regression'
    & uv run pytest -q --maxfail=1 -x --tb=long
    if ($LASTEXITCODE -ne 0) {
        throw 'Full backend regression failed at the first deterministic failure.'
    }

    Write-Host '============================================================'
    Write-Host '[PASS] Webhook Provider unit gate and backend regression completed.'
    Write-Host '============================================================'
} finally {
    Pop-Location
}
