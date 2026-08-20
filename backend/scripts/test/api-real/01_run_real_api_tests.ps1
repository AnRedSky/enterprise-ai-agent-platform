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
  $context=Get-Content $contextFile -Raw|ConvertFrom-Json
  $env:ACCESS_TOKEN=[string]$context.ACCESS_TOKEN
  $env:WORKFLOW_ID=[string]$context.WORKFLOW_ID
  $env:WORKFLOW_EXECUTION_ID=[string]$context.WORKFLOW_EXECUTION_ID
  $env:RETRY_WORKFLOW_ID=[string]$context.RETRY_WORKFLOW_ID
  $env:RETRY_EXECUTION_ID=[string]$context.RETRY_EXECUTION_ID
  Write-Host "[2/2] Execute all real HTTP API tests"
  uv run pytest -q tests/api_real -m real_api
  if($LASTEXITCODE -ne 0){throw "Real API test suite failed."}
  Write-Host "[PASS] Real API gate completed. Frontend/backend integration may proceed."
}finally{
  if(Test-Path $contextFile){Remove-Item $contextFile -Force -ErrorAction SilentlyContinue}
  Remove-Item Env:ACCESS_TOKEN -ErrorAction SilentlyContinue
  Remove-Item Env:WORKFLOW_ID -ErrorAction SilentlyContinue
  Remove-Item Env:WORKFLOW_EXECUTION_ID -ErrorAction SilentlyContinue
  Remove-Item Env:RETRY_WORKFLOW_ID -ErrorAction SilentlyContinue
  Remove-Item Env:RETRY_EXECUTION_ID -ErrorAction SilentlyContinue
}
