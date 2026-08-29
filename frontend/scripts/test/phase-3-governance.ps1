$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..\..\..')
Write-Host 'Phase P3 / 企业治理：Organization + Audit + Integration + Dashboard'
npx vitest run tests/views/Organizations.test.ts tests/views/OrganizationDetail.test.ts tests/views/AuditLog.test.ts tests/views/Integrations.test.ts tests/views/IntegrationEventConsole.test.ts tests/views/DeliveryConsole.test.ts tests/views/Dashboard.test.ts
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
