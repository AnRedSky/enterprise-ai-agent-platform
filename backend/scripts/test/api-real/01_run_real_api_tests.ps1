$ErrorActionPreference="Stop"
Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Real API Test Gate"
Write-Host "============================================================"
if(-not $env:API_BASE_URL){$env:API_BASE_URL="http://127.0.0.1:8000/api/v1"}
$contextFile=Join-Path $PSScriptRoot ".real_api_context.json"
try{
  Write-Host "[1/2] Prepare real API test context"
  uv run python .\scripts\test\api-real\00_bootstrap_real_api.py
  if($LASTEXITCODE -ne 0){throw "Real API bootstrap failed."}
  if(-not(Test-Path $contextFile)){throw "Real API context file was not created."}
  uv run python .\scripts\test\api-real\00_grant_admin_fixture.py
  if($LASTEXITCODE -ne 0){throw "Real API admin fixture preparation failed."}
  $context=Get-Content $contextFile -Raw|ConvertFrom-Json
  $env:ACCESS_TOKEN=[string]$context.ACCESS_TOKEN
  $env:ADMIN_ACCESS_TOKEN=[string]$context.ADMIN_ACCESS_TOKEN
  $env:WORKFLOW_ID=[string]$context.WORKFLOW_ID
  $env:WORKFLOW_EXECUTION_ID=[string]$context.WORKFLOW_EXECUTION_ID
  $env:TRIGGER_WORKFLOW_ID=[string]$context.TRIGGER_WORKFLOW_ID
  $env:TRIGGER_ID=[string]$context.TRIGGER_ID
  $env:RETRY_WORKFLOW_ID=[string]$context.RETRY_WORKFLOW_ID
  $env:RETRY_EXECUTION_ID=[string]$context.RETRY_EXECUTION_ID
  $env:RETRY_BUDGET_WORKFLOW_ID=[string]$context.RETRY_BUDGET_WORKFLOW_ID
  $env:RETRY_BUDGET_EXECUTION_ID=[string]$context.RETRY_BUDGET_EXECUTION_ID
  $env:RETRY_DEADLINE_WORKFLOW_ID=[string]$context.RETRY_DEADLINE_WORKFLOW_ID
  $env:RETRY_DEADLINE_EXECUTION_ID=[string]$context.RETRY_DEADLINE_EXECUTION_ID
  $env:CIRCUIT_OPEN_WORKFLOW_ID=[string]$context.CIRCUIT_OPEN_WORKFLOW_ID
  $env:CIRCUIT_OPEN_EXECUTION_ID=[string]$context.CIRCUIT_OPEN_EXECUTION_ID
  $env:CIRCUIT_RECOVERY_WORKFLOW_ID=[string]$context.CIRCUIT_RECOVERY_WORKFLOW_ID
  $env:ORGANIZATION_ID=[string]$context.ORGANIZATION_ID
  $env:ORGANIZATION_MEMBERSHIP_ID=[string]$context.ORGANIZATION_MEMBERSHIP_ID
  $env:ORGANIZATION_MEMBER_USER_ID=[string]$context.ORGANIZATION_MEMBER_USER_ID
  $env:ORGANIZATION_MEMBER_ACCESS_TOKEN=[string]$context.ORGANIZATION_MEMBER_ACCESS_TOKEN
  Write-Host "[2/2] Execute all real HTTP API tests"
  uv run pytest -q tests/api_real -m real_api
  if($LASTEXITCODE -ne 0){throw "Real API test suite failed."}
  Write-Host "[PASS] Real API gate completed. Frontend/backend integration may proceed."
}finally{
  if(Test-Path $contextFile){Remove-Item $contextFile -Force -ErrorAction SilentlyContinue}
  Remove-Item Env:ACCESS_TOKEN -ErrorAction SilentlyContinue
  Remove-Item Env:ADMIN_ACCESS_TOKEN -ErrorAction SilentlyContinue
  Remove-Item Env:WORKFLOW_ID -ErrorAction SilentlyContinue
  Remove-Item Env:WORKFLOW_EXECUTION_ID -ErrorAction SilentlyContinue
  Remove-Item Env:TRIGGER_WORKFLOW_ID -ErrorAction SilentlyContinue
  Remove-Item Env:TRIGGER_ID -ErrorAction SilentlyContinue
  Remove-Item Env:RETRY_WORKFLOW_ID -ErrorAction SilentlyContinue
  Remove-Item Env:RETRY_EXECUTION_ID -ErrorAction SilentlyContinue
  Remove-Item Env:RETRY_BUDGET_WORKFLOW_ID -ErrorAction SilentlyContinue
  Remove-Item Env:RETRY_BUDGET_EXECUTION_ID -ErrorAction SilentlyContinue
  Remove-Item Env:RETRY_DEADLINE_WORKFLOW_ID -ErrorAction SilentlyContinue
  Remove-Item Env:RETRY_DEADLINE_EXECUTION_ID -ErrorAction SilentlyContinue
  Remove-Item Env:CIRCUIT_OPEN_WORKFLOW_ID -ErrorAction SilentlyContinue
  Remove-Item Env:CIRCUIT_OPEN_EXECUTION_ID -ErrorAction SilentlyContinue
  Remove-Item Env:CIRCUIT_RECOVERY_WORKFLOW_ID -ErrorAction SilentlyContinue
  Remove-Item Env:ORGANIZATION_ID -ErrorAction SilentlyContinue
  Remove-Item Env:ORGANIZATION_MEMBERSHIP_ID -ErrorAction SilentlyContinue
  Remove-Item Env:ORGANIZATION_MEMBER_USER_ID -ErrorAction SilentlyContinue
  Remove-Item Env:ORGANIZATION_MEMBER_ACCESS_TOKEN -ErrorAction SilentlyContinue
}