$ErrorActionPreference="Stop"
Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Scheduler / Worker Restart Acceptance"
Write-Host "============================================================"

# 本 Gate 只执行验收，不负责启动或停止任何服务。
# Scheduler / Worker / API 必须由开发者提前手动启动；Acceptance 只验证真实持久化链路。
if(-not $env:API_BASE_URL){$env:API_BASE_URL="http://127.0.0.1:8000/api/v1"}
$contextFile=Join-Path $PSScriptRoot ".real_api_context.json"

function Assert-ApiAvailable {
  $healthUrl=($env:API_BASE_URL -replace "/api/v1$", "") + "/health"
  try {
    $response=Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 3
    if($response.StatusCode -ne 200){throw "API health check returned HTTP $($response.StatusCode)."}
  } catch {
    throw "Required API Service is not available at $env:API_BASE_URL. Start it manually before running this gate."
  }
}

function Assert-BackgroundProcess {
  param([string]$Pattern,[string]$ServiceName,[string]$StartCommand)
  $processes=@(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
    $_.CommandLine -and $_.CommandLine -match $Pattern
  })
  if($processes.Count -eq 0){
    throw "Required $ServiceName is not running. Start it manually before running this gate: $StartCommand"
  }
  $processes | ForEach-Object { Write-Host "[INFO] Existing $ServiceName PID=$($_.ProcessId) CommandLine=$($_.CommandLine)" }
}

try{
  Write-Host "[1/3] Verify manually managed services (this gate starts nothing)"
  Assert-ApiAvailable
  Assert-BackgroundProcess "run_scheduler\.py" "Scheduler Service" "uv run python run_scheduler.py"
  Assert-BackgroundProcess "run_worker\.py" "Worker Service" "uv run python run_worker.py"

  Write-Host "[2/3] Prepare tenant-safe real API context"
  uv run python .\scripts\test\api-real\00_bootstrap_real_api_tenant_safe.py
  if($LASTEXITCODE -ne 0){throw "Real API bootstrap failed."}
  if(-not(Test-Path $contextFile)){throw "Real API context file was not created."}
  uv run python .\scripts\test\api-real\00_grant_admin_fixture.py
  if($LASTEXITCODE -ne 0){throw "Real API admin fixture preparation failed."}
  $context=Get-Content $contextFile -Raw|ConvertFrom-Json
  $env:ACCESS_TOKEN=[string]$context.ACCESS_TOKEN
  $env:TRIGGER_WORKFLOW_ID=[string]$context.TRIGGER_WORKFLOW_ID

  Write-Host "[3/3] Execute externally managed Scheduler / Worker recovery acceptance"
  Write-Host "[INFO] No service process will be started, stopped, or restarted by this gate."
  uv run pytest -q tests/api_real/test_scheduler_restart_api.py -m real_api
  if($LASTEXITCODE -ne 0){throw "Scheduler / Worker recovery acceptance failed."}
  Write-Host "[PASS] Scheduler / Worker recovery acceptance completed."
}finally{
  if(Test-Path $contextFile){Remove-Item $contextFile -Force -ErrorAction SilentlyContinue}
  Remove-Item Env:ACCESS_TOKEN -ErrorAction SilentlyContinue
  Remove-Item Env:TRIGGER_WORKFLOW_ID -ErrorAction SilentlyContinue
  Remove-Item Env:API_BASE_URL -ErrorAction SilentlyContinue
}
