$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Scheduler Runtime Gate'
Write-Host '============================================================'

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Set-Location $backendRoot

function Invoke-GateStep {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "[Gate] $Name"
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "Gate failed: $Name (exit=$LASTEXITCODE)" }
}

Invoke-GateStep 'Scheduler Runtime targeted tests' {
    uv run pytest -q tests/unit/test_workflow_scheduler_runtime.py
}

Invoke-GateStep 'Scheduler Persistence Gate' {
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\01_scheduler_persistence_gate.ps1
}

Write-Host '============================================================'
Write-Host 'Scheduler Runtime Gate completed.'
Write-Host 'Only locally executed test results are reported.'
Write-Host '============================================================'
