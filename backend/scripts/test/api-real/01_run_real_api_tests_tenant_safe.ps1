$ErrorActionPreference="Stop"
Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Real API Test Gate (Tenant Safe)"
Write-Host "============================================================"
if(-not $env:API_BASE_URL){$env:API_BASE_URL="http://127.0.0.1:8000/api/v1"}
$contextFile=Join-Path $PSScriptRoot ".real_api_context.json"
$workerProcess=$null
$ownsWorkerProcess=$false
try{
  Write-Host "[1/3] Prepare real API test context"
  uv run python .\scripts\test\api-real\00_bootstrap_real_api_tenant_safe.py
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

  Write-Host "[2/3] Ensure Worker Service is available for scheduled Execution consumption"
  $existingWorker = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
    $_.CommandLine -and $_.CommandLine -match "run_worker\.py"
  })
  if($existingWorker.Count -gt 0){
    Write-Host "[INFO] Detected existing Worker Service process; reusing it instead of starting a duplicate consumer."
    $existingWorker | ForEach-Object {
      Write-Host "[INFO] Reused Worker PID=$($_.ProcessId) CommandLine=$($_.CommandLine)"
    }
  }else{
    $backendDir=Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
    $workerProcess=Start-Process -FilePath "uv" -ArgumentList @("run","python","run_worker.py") -WorkingDirectory $backendDir -PassThru -WindowStyle Hidden
    $ownsWorkerProcess=$true
    $workerDeadline=(Get-Date).AddSeconds(15)
    do{
      Start-Sleep -Milliseconds 500
      if($workerProcess.HasExited){throw "Worker Service exited before Real API tests started. exit_code=$($workerProcess.ExitCode)"}
    }while((Get-Date) -lt $workerDeadline)
    Write-Host "[INFO] Temporary Worker Service started with PID=$($workerProcess.Id)."
  }

  Write-Host "[3/3] Execute tenant-safe real HTTP API tests (Scheduler lifecycle restart acceptance is independent)"
  uv run pytest -q tests/api_real -m real_api --ignore=tests/api_real/test_scheduler_restart_api.py
  if($LASTEXITCODE -ne 0){throw "Real API test suite failed."}
  Write-Host "[PASS] Tenant-safe Real API gate completed."
  if($ownsWorkerProcess){
    Write-Host "[INFO] Temporary Worker Service was started by this gate and will be stopped during cleanup."
  }else{
    Write-Host "[INFO] Existing Worker Service was reused and will not be stopped by this gate."
  }
  Write-Host "[INFO] Scheduler real service restart acceptance is intentionally excluded from this gate."
  Write-Host "[INFO] Run .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1 separately with no other Scheduler/Worker process active."
}finally{
  if($ownsWorkerProcess -and $workerProcess -and -not $workerProcess.HasExited){Stop-Process -Id $workerProcess.Id -Force -ErrorAction SilentlyContinue; $workerProcess.WaitForExit()}
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
