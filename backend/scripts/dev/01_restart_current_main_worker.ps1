# Enterprise AI Agent Platform - 当前 main Worker 清理启动辅助脚本
#
# 职责：清理当前项目残留的 run_worker.py 进程，并只启动一个当前工作目录对应的 Worker。
# 边界：仅用于开发者本地环境；不属于 Real API Gate，Gate 仍保持“不自动启动/停止服务”的约束。
# 依赖：Windows PowerShell、uv、backend/.venv。

$ErrorActionPreference = "Stop"

$backendPath = (Get-Location).Path
if (-not (Test-Path (Join-Path $backendPath "run_worker.py"))) {
    throw "当前目录不是 backend：$backendPath"
}

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Clean Current-main Worker"
Write-Host "============================================================"
Write-Host "[INFO] Backend: $backendPath"

$currentWorkers = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'pythonw.exe'" | Where-Object {
    $commandLine = [string]$_.CommandLine
    $commandLine -match "run_worker\.py" -and $commandLine -match [regex]::Escape($backendPath)
})

$uvWorkers = @(Get-CimInstance Win32_Process -Filter "Name = 'uv.exe'" | Where-Object {
    $commandLine = [string]$_.CommandLine
    $commandLine -match "run_worker\.py" -and $commandLine -match [regex]::Escape($backendPath)
})

$workers = @($currentWorkers + $uvWorkers | Sort-Object ProcessId -Unique)

if ($workers.Count -gt 0) {
    Write-Host "[INFO] Found $($workers.Count) current-project Worker process(es)."
    foreach ($process in $workers) {
        Write-Host ("[STOP] PID={0} CommandLine={1}" -f $process.ProcessId, $process.CommandLine)
        Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop
    }
    Start-Sleep -Seconds 1
} else {
    Write-Host "[INFO] No current-project Worker process found."
}

Write-Host "[START] Starting exactly one current-main Worker..."
$worker = Start-Process -FilePath "uv" -ArgumentList @("run", "python", "run_worker.py") -WorkingDirectory $backendPath -PassThru

Start-Sleep -Seconds 2
if ($worker.HasExited) {
    throw "Worker failed to start. ExitCode=$($worker.ExitCode)"
}

Write-Host "[PASS] Current-main Worker started. PID=$($worker.Id)"
Write-Host "[NEXT] Run the tenant-safe Real API Gate only after PostgreSQL, Redis and API are healthy."
Write-Host "[NEXT] Durable Resume Gate: .\scripts\test\api-real\05_run_durable_resume_real_tests.ps1"
Write-Host "[NEXT] Full tenant-safe Gate: .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1"
