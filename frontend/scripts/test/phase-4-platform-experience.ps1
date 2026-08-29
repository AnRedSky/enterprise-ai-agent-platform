$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..\..\..')
Write-Host 'Phase P4 / 平台体验：AppShell 与共享平台体验'
npx vitest run tests/views/AppShell.test.ts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
