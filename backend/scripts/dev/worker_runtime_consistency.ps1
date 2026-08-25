$ErrorActionPreference = 'Stop'

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Worker Runtime Consistency Gate'
Write-Host '============================================================'
Write-Host '[INFO] Read-only diagnostic. No API, Scheduler, or Worker process is started or stopped.'

uv run python .\scripts\dev\inspect_worker_runtime_consistency.py
if ($LASTEXITCODE -eq 2) {
    throw 'Worker runtime consistency check found persistent execution/node state anomalies.'
}
if ($LASTEXITCODE -ne 0) {
    throw 'Worker runtime consistency diagnostic failed to execute.'
}

Write-Host '[PASS] Worker runtime consistency diagnostic completed.'
