$ErrorActionPreference="Stop"
Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Scheduler / Worker Restart Acceptance"
Write-Host "============================================================"

function Assert-NoSchedulerBackgroundProcess {
  # Acceptance 必须独占 Scheduler；API 与 Worker 可以作为本地独立服务继续运行。
  # Worker 使用 PostgreSQL claim/lease 竞争消费，因此允许既有 Worker 参与本验收；
  # Scheduler 则会改变同一持久化 schedule 的生命周期，不能与验收 Scheduler 并存。
  $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
    $_.CommandLine -and $_.CommandLine -match "run_scheduler\.py"
  })
  if($processes.Count -gt 0){
    $details = ($processes | ForEach-Object { "PID=$($_.ProcessId) CommandLine=$($_.CommandLine)" }) -join "`n"
    throw "检测到已有 Scheduler Service 进程，Acceptance 必须独占 Scheduler。请先停止以下 Scheduler 进程后重新执行：`n$details"
  }
}

Assert-NoSchedulerBackgroundProcess

# Gate 只使用临时 API Service 完成 tenant-safe fixture bootstrap；真实验收由独立 Scheduler + Worker 完成。
$bootstrapListener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
try {
  $bootstrapListener.Start()
  $bootstrapPort = ([System.Net.IPEndPoint]$bootstrapListener.LocalEndpoint).Port
} finally {
  $bootstrapListener.Stop()
}

$env:API_BASE_URL="http://127.0.0.1:$bootstrapPort/api/v1"
$contextFile=Join-Path $PSScriptRoot ".real_api_context.json"
$bootstrapProcess=$null
try{
  Write-Host "[1/3] Start temporary API Service for tenant-safe fixture bootstrap"
  Write-Host "[INFO] Fixture bootstrap port: $bootstrapPort"
  $backendDir=Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
  $bootstrapProcess=Start-Process -FilePath "uv" -ArgumentList @("run","uvicorn","app.main:app","--host","127.0.0.1","--port",$bootstrapPort) -WorkingDirectory $backendDir -PassThru -WindowStyle Hidden
  $deadline=(Get-Date).AddSeconds(20)
  do{
    Start-Sleep -Milliseconds 500
    try{$health=Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$bootstrapPort/health" -TimeoutSec 2}catch{$health=$null}
    if($health -and $health.StatusCode -eq 200){break}
    if($bootstrapProcess.HasExited){throw "Temporary API Service exited before health check."}
  }while((Get-Date) -lt $deadline)
  if(-not $health -or $health.StatusCode -ne 200){throw "Temporary API Service did not become healthy within 20 seconds."}

  Write-Host "[2/3] Prepare tenant-safe real API context"
  uv run python .\scripts\test\api-real\00_bootstrap_real_api_tenant_safe.py
  if($LASTEXITCODE -ne 0){throw "Real API bootstrap failed."}
  if(-not(Test-Path $contextFile)){throw "Real API context file was not created."}
  uv run python .\scripts\test\api-real\00_grant_admin_fixture.py
  if($LASTEXITCODE -ne 0){throw "Real API admin fixture preparation failed."}
  if($bootstrapProcess -and -not $bootstrapProcess.HasExited){Stop-Process -Id $bootstrapProcess.Id -Force; $bootstrapProcess.WaitForExit()}
  $bootstrapProcess=$null

  $context=Get-Content $contextFile -Raw|ConvertFrom-Json
  $env:ACCESS_TOKEN=[string]$context.ACCESS_TOKEN
  $env:TRIGGER_WORKFLOW_ID=[string]$context.TRIGGER_WORKFLOW_ID

  Write-Host "[3/3] Start/stop/restart independent Scheduler + Worker Services and verify PostgreSQL execution recovery"
  uv run python -c "from app.main import app; print('API_IMPORT_OK')"
  if($LASTEXITCODE -ne 0){throw "Application import failed."}
  uv run python -c "from app.entrypoints.scheduler import run_scheduler_service; print('SCHEDULER_ENTRYPOINT_IMPORT_OK')"
  if($LASTEXITCODE -ne 0){throw "Scheduler entrypoint import failed."}
  uv run python -c "from app.entrypoints.worker import run_worker_service; print('WORKER_ENTRYPOINT_IMPORT_OK')"
  if($LASTEXITCODE -ne 0){throw "Worker entrypoint import failed."}
  uv run pytest -q tests/api_real/test_scheduler_restart_api.py -m real_api
  if($LASTEXITCODE -ne 0){throw "Scheduler / Worker restart acceptance failed."}
  Write-Host "[PASS] Independent Scheduler / Worker restart acceptance completed."
  Write-Host "[INFO] Existing API/Worker processes were not treated as conflicts; only Scheduler process isolation is mandatory."
}finally{
  if($bootstrapProcess -and -not $bootstrapProcess.HasExited){Stop-Process -Id $bootstrapProcess.Id -Force -ErrorAction SilentlyContinue; $bootstrapProcess.WaitForExit()}
  if(Test-Path $contextFile){Remove-Item $contextFile -Force -ErrorAction SilentlyContinue}
  Remove-Item Env:ACCESS_TOKEN -ErrorAction SilentlyContinue
  Remove-Item Env:TRIGGER_WORKFLOW_ID -ErrorAction SilentlyContinue
  Remove-Item Env:API_BASE_URL -ErrorAction SilentlyContinue
}
