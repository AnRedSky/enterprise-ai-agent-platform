$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..\..\..')
Write-Host 'Phase P2 / 自动化与运行：Workflow + Trigger + Runtime'
npx vitest run tests/views/Workflows.test.ts tests/views/WorkflowsUI03.test.ts tests/views/WorkflowsUI04UI05.test.ts tests/views/WorkflowTriggers.test.ts tests/views/Runtime.test.ts tests/views/RuntimeDeepLinkRecovery.test.ts tests/views/RuntimeCorrelationsUI03UI04.test.ts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
