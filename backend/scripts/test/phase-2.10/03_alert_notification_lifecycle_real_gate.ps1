$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendRoot = (Resolve-Path (Join-Path $ScriptRoot "..\..\..")).Path
Set-Location $BackendRoot

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-I Runtime Notification Lifecycle Real Gate"
Write-Host "============================================================"
Write-Host "[0/6] 本地前置条件检查"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw "未找到 uv，请先安装 uv。" }
if (-not (Test-Path (Join-Path $BackendRoot ".env.example"))) { throw "缺少 backend/.env.example。" }
Write-Host "配置策略：使用 backend/.env.example 作为统一本地测试基线。"
Write-Host "测试数据策略：验收脚本自动创建并清理 tenant/rule/policy/destination 等测试数据。"
Write-Host "服务策略：本 Gate 严禁自动创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis。"

function Test-SchedulerAvailable {
    $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.CommandLine -and $_.CommandLine -match 'run_scheduler\.py'
    })
    if ($processes.Count -eq 0) {
        Write-Host "[NOT EXECUTED] Scheduler Service 未运行。请由开发者提前启动：uv run python run_scheduler.py"
        return $false
    }
    Write-Host "[PASS] Scheduler Service 已存在：$($processes.Count) 个进程。"
    return $true
}

function Test-WorkerAvailable {
    $processes = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.CommandLine -and $_.CommandLine -match 'run_worker\.py'
    })
    if ($processes.Count -eq 0) {
        Write-Host "[NOT EXECUTED] Worker Service 未运行。请由开发者提前启动：uv run python run_worker.py"
        return $false
    }
    Write-Host "[PASS] Worker Service 已存在：$($processes.Count) 个进程。"
    return $true
}

Write-Host "[1/6] Migration/head verification"
& uv run alembic heads
if ($LASTEXITCODE -ne 0) { throw "Alembic heads 检查失败。" }
& uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Alembic upgrade head 执行失败。" }
& uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Alembic current 检查失败。" }

Write-Host "[2/6] Targeted migration/runtime test collection"
& uv run pytest -q tests/unit/test_migration_graph.py tests/api_real/test_alert_notification_runtime_acceptance.py --collect-only --tb=short
if ($LASTEXITCODE -ne 0) { throw "Runtime Notification 测试收集失败。" }

Write-Host "[3/6] 检查 Runtime 服务（不自动启动任何服务）"
$schedulerReady = Test-SchedulerAvailable
$workerReady = Test-WorkerAvailable
if (-not ($schedulerReady -and $workerReady)) {
    Write-Host "[NOT EXECUTED] Runtime Notification Lifecycle Real Acceptance 未执行，因为必需服务未全部预先运行。"
    Write-Host "[INFO] 本 Gate 不会自动启动服务，也不会要求手工填写测试数据。"
    exit 0
}

Write-Host "[4/6] Alert -> Notification -> Worker Runtime Acceptance"
& uv run pytest -q tests/api_real/test_alert_notification_runtime_acceptance.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Alert Notification Runtime Acceptance 失败。" }

Write-Host "[5/6] Migration graph regression"
& uv run pytest -q tests/unit/test_migration_graph.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Migration graph regression 失败。" }

Write-Host "[6/6] Runtime lifecycle handoff"
Write-Host "已验证链路：Alert Evaluation -> Firing/Recovery -> Policy -> Group/Dedup/Cooldown -> Provider Routing -> Worker -> Outcome -> Fallback -> SLO/Metrics -> Audit。"
Write-Host "[PASS] Phase 2.10-I Runtime Notification Lifecycle Real Gate completed."
Write-Host "[INFO] 本 Gate 从不启动或停止任何服务，并自动生成全部测试身份与业务数据。"
