$ErrorActionPreference = 'Stop'

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$target = 'tests/unit/test_execution_frontier_terminalization.py'

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Backend Failure Diagnostic Gate'
Write-Host 'Scope: deterministic unit failure -> targeted verification -> optional full regression'
Write-Host 'Service policy: this gate never starts, restarts, or stops any service.'
Write-Host '============================================================'

Push-Location $backendRoot
try {
    Write-Host '[1/3] Targeted terminalization regression'
    & uv run pytest -q $target --maxfail=1 -x --tb=long
    if ($LASTEXITCODE -ne 0) {
        throw "Targeted regression failed: $target"
    }

    Write-Host '[2/3] Backend collection/import smoke check'
    & uv run pytest --collect-only -q
    if ($LASTEXITCODE -ne 0) {
        throw 'Backend test collection failed. Do not continue to the full regression gate.'
    }

    Write-Host '[3/3] Full backend regression'
    & uv run pytest -q --maxfail=1 -x --tb=long
    if ($LASTEXITCODE -ne 0) {
        throw 'Full backend regression failed at the first deterministic failure.'
    }

    Write-Host '============================================================'
    Write-Host '[PASS] Backend failure diagnostic gate completed.'
    Write-Host '============================================================'
} finally {
    Pop-Location
}
