$ErrorActionPreference="Stop"
Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Scheduler Real Restart Acceptance"
Write-Host "============================================================"
$restartPort=8000
$portProbe=New-Object System.Net.Sockets.TcpClient
try{
  try{
    $portProbe.Connect("127.0.0.1",$restartPort)
    throw "Port $restartPort is already occupied. Scheduler real restart acceptance requires exclusive ownership of the local Scheduler process; stop the existing API/Scheduler service before running this gate."
  }catch [System.Net.Sockets.SocketException]{
    # 连接失败表示目标端口当前未被监听，可以继续启动独占的临时服务。
  }
}finally{
  $portProbe.Dispose()
}
if(-not $env:API_BASE_URL){$env:API_BASE_URL="http://127.0.0.1:$restartPort/api/v1"}
$contextFile=Join-Path $PSScriptRoot ".real_api_context.json"
$bootstrapProcess=$null
try{
  Write-Host "[1/3] Start temporary real API process for tenant-safe fixture bootstrap"
  $backendDir=Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
  $bootstrapProcess=Start-Process -FilePath "uv" -ArgumentList @("run","uvicorn","app.main:app","--host","127.0.0.1","--port",$restartPort) -WorkingDirectory $backendDir -PassThru -WindowStyle Hidden
  $deadline=(Get-Date).AddSeconds(20)
  do{
    Start-Sleep -Milliseconds 500
    try{$health=Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$restartPort/health" -TimeoutSec 2}catch{$health=$null}
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
}
