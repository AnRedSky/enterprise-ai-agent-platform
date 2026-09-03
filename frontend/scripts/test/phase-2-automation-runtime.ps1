$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..\..\..')
Write-Host 'Phase P2 / 自动化与运行：Workflow + Trigger + Runtime'
npx vitest run tests/views/Workflows.test.ts tests/views/WorkflowTriggers.test.ts tests/views/Runtime.test.ts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
