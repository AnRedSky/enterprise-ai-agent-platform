$ErrorActionPreference="Stop"
Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Scheduler Real Restart Acceptance"
Write-Host "============================================================"
if(-not $env:API_BASE_URL){$env:API_BASE_URL="http://127.0.0.1:8000/api/v1"}
$contextFile=Join-Path $PSScriptRoot ".real_api_context.json"
try{
  Write-Host "[1/3] Prepare tenant-safe real API context"
  uv run python .\scripts\test\api-real\00_bootstrap_real_api_tenant_safe.py
  if($LASTEXITCODE -ne 0){throw "Real API bootstrap failed."}
  if(-not(Test-Path $contextFile)){throw "Real API context file was not created."}
  uv run python .\scripts\test\api-real\00_grant_admin_fixture.py
  if($LASTEXITCODE -ne 0){throw "Real API admin fixture preparation failed."}

  $context=Get-Content $contextFile -Raw|ConvertFrom-Json
  $env:ACCESS_TOKEN=[string]$context.ACCESS_TOKEN
  $env:TRIGGER_WORKFLOW_ID=[string]$context.TRIGGER_WORKFLOW_ID

  Write-Host "[2/3] Verify real application import before process lifecycle acceptance"
  uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
  if($LASTEXITCODE -ne 0){throw "Application import failed."}

  Write-Host "[3/3] Start/stop/restart real Uvicorn process and verify PostgreSQL recovery"
  uv run pytest -q tests/api_real/test_scheduler_restart_api.py -m real_api
  if($LASTEXITCODE -ne 0){throw "Scheduler real restart acceptance failed."}
  Write-Host "[PASS] Scheduler real restart acceptance completed."
}finally{
  if(Test-Path $contextFile){Remove-Item $contextFile -Force -ErrorAction SilentlyContinue}
  Remove-Item Env:ACCESS_TOKEN -ErrorAction SilentlyContinue
  Remove-Item Env:TRIGGER_WORKFLOW_ID -ErrorAction SilentlyContinue
}
