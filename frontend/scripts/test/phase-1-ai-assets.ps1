$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..\..\..')
Write-Host 'Phase P1 / AI 资产：Agent + Knowledge + Tool + Model Provider'
npx vitest run tests/views/Agents.test.ts tests/views/knowledge/KnowledgeWorkbench.test.ts tests/views/Tools.test.ts tests/views/ModelProviders.test.ts tests/views/AgentWorkbenchUI05.test.ts tests/views/AgentDebugExperienceUI04.test.ts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
