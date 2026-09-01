$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Scheduler Service Lifecycle Gate"
Write-Host "============================================================"
Write-Host "[0/3] 本地前置检查"
Write-Host "服务策略：本 Gate 不创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis。"
Write-Host "测试数据策略：生命周期测试全部使用 Mock，不要求手工填写 ID、凭据或业务数据。"
Write-Host "告警策略：pytest warning 视为测试错误。"

$protectedPatterns = @(
    "uv.*run.*python.*run\.py",
    "uv.*run.*python.*run_scheduler\.py",
    "uvicorn.*app\.main:app",
    "postgres",
    "redis-server"
)

function Get-ProtectedProcessSnapshot {
    $processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
    return @(
        $processes | Where-Object {
            $commandLine = $_.CommandLine
            if ([string]::IsNullOrWhiteSpace($commandLine)) { return $false }
            foreach ($pattern in $protectedPatterns) {
                if ($commandLine -match $pattern) { return $true }
            }
            return $false
        } | Select-Object ProcessId, Name, CommandLine
    )
}

$before = Get-ProtectedProcessSnapshot
Write-Host "[1/3] Scheduler Service 生命周期单元测试"
uv run pytest -q tests/unit/test_service_entrypoints.py
if ($LASTEXITCODE -ne 0) {
    throw "Scheduler Service lifecycle unit test failed."
}

Write-Host "[2/3] 取消传播与统一清理回归"
uv run pytest -q tests/unit/test_service_entrypoints.py -k "scheduler_service"
if ($LASTEXITCODE -ne 0) {
    throw "Scheduler Service focused regression failed."
}

Write-Host "[3/3] 服务边界复核"
$after = Get-ProtectedProcessSnapshot
$unexpected = @($after | Where-Object {
    $beforeIds = @($before | ForEach-Object { $_.ProcessId })
    $beforeIds -notcontains $_.ProcessId
})
if ($unexpected.Count -gt 0) {
    $details = $unexpected | ForEach-Object { "PID=$($_.ProcessId) Name=$($_.Name) CommandLine=$($_.CommandLine)" }
    throw "Gate detected a protected service process created during the test:`n$($details -join "`n")"
}

Write-Host "[PASS] Scheduler Dispatch / Recovery / Alert / Notification 生命周期监督测试通过。"
Write-Host "[PASS] Scheduler 循环取消会传播，并统一执行 stop / telemetry cleanup。"
Write-Host "[PASS] 本 Gate 未创建或启动任何受保护服务。"
Write-Host "[PASS] Scheduler Service Lifecycle Gate completed."
