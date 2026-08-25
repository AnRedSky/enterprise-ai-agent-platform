$ErrorActionPreference="Stop"
Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Scheduler Real Restart Acceptance"
Write-Host "============================================================"

function Assert-NoProjectSchedulerProcess {
  # Restart Acceptance 必须保证目标 Trigger 在 PostgreSQL 中只有测试自身的 Scheduler worker 能够竞争。
  # 不能只检查固定端口，因为开发环境可能把 API/Scheduler 运行在任意本地端口。
  $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
    $_.CommandLine -and $_.CommandLine -match "app\.main:app"
  })
  if($processes.Count -gt 0){
    $details = ($processes | ForEach-Object { "PID=$($_.ProcessId) CommandLine=$($_.CommandLine)" }) -join "`n"
    throw "检测到已有项目 API/Scheduler 进程，restart acceptance 必须独占 Scheduler worker。请先停止以下进程后重新执行：`n$details"
  }
}

Assert-NoProjectSchedulerProcess

# 该 Gate 需要一个仅由自身控制的临时 API/Scheduler 进程。
# 不再固定占用 8000，而是启动前申请本机空闲端口作为 fixture bootstrap；真正 restart acceptance 的 Scheduler 仍由测试代码自行申请独立端口。
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
  Write-Host "[1/3] Start temporary real API process for tenant-safe fixture bootstrap"
  Write-Host "[INFO] Scheduler restart bootstrap port: $bootstrapPort"
  $backendDir=Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
  $bootstrapProcess=Start-Process -FilePath "uv" -ArgumentList @("run","uvicorn","app.main:app","--host","127.0.0.1","--port",$bootstrapPort) -WorkingDirectory $backendDir -PassThru -WindowStyle Hidden
  $deadline=(Get-Date).AddSeconds(20)
  do{
    Start-Sleep -Milliseconds 500
    try{$health=Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$bootstrapPort/health" -TimeoutSec 2}catch{$health=$null}
    if($health -and $health.StatusCode -eq 200){break}
    if($bootstrapProcess.HasExited){throw "Temporary real API process exited before health check."}
  }while((Get-Date) -lt $deadline)
  if(-not $health -or $health.StatusCode -ne 200){throw "Temporary real API process did not become healthy within 20 seconds."}

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
  # 通用 Real API Workflow ID 仅由 bootstrap 兼容输出；restart acceptance 已改为自行创建可执行 Workflow，避免共享 Fixture。
  $env:TRIGGER_WORKFLOW_ID=[string]$context.TRIGGER_WORKFLOW_ID

  Write-Host "[3/3] Start/stop/restart real Uvicorn process and verify PostgreSQL recovery"
  uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
  if($LASTEXITCODE -ne 0){throw "Application import failed."}
  uv run pytest -q tests/api_real/test_scheduler_restart_api.py -m real_api
  if($LASTEXITCODE -ne 0){throw "Scheduler real restart acceptance failed."}
  Write-Host "[PASS] Scheduler real restart acceptance completed."
}finally{
  if($bootstrapProcess -and -not $bootstrapProcess.HasExited){Stop-Process -Id $bootstrapProcess.Id -Force -ErrorAction SilentlyContinue; $bootstrapProcess.WaitForExit()}
  if(Test-Path $contextFile){Remove-Item $contextFile -Force -ErrorAction SilentlyContinue}
  Remove-Item Env:ACCESS_TOKEN -ErrorAction SilentlyContinue
  Remove-Item Env:TRIGGER_WORKFLOW_ID -ErrorAction SilentlyContinue
  Remove-Item Env:API_BASE_URL -ErrorAction SilentlyContinue
}
