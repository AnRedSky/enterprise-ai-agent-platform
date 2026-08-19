$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
Write-Host '============================================================' -ForegroundColor DarkGray
Write-Host 'Enterprise AI Agent Platform - Knowledge Frontend Manual Suite' -ForegroundColor Cyan
Write-Host "Frontend: $root" -ForegroundColor Gray
Write-Host '============================================================' -ForegroundColor DarkGray
Write-Host '[RUN ] Knowledge API / UI Vitest' -ForegroundColor Yellow
npm test -- --run tests/api/knowledge.test.ts tests/views/knowledge/KnowledgeWorkbench.test.ts
if ($LASTEXITCODE -ne 0) { throw "Knowledge frontend Vitest failed with exit code $LASTEXITCODE." }
Write-Host '[ OK  ] Knowledge API / UI Vitest' -ForegroundColor Green
Write-Host '[RUN ] Frontend production build' -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) { throw "Frontend build failed with exit code $LASTEXITCODE." }
Write-Host '[ OK  ] Frontend production build' -ForegroundColor Green
Write-Host '============================================================' -ForegroundColor DarkGray
Write-Host '[PASS] Knowledge frontend manual suite completed' -ForegroundColor Green
Write-Host '============================================================' -ForegroundColor DarkGray
