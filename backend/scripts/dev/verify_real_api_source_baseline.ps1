$ErrorActionPreference = 'Stop'

# 本脚本只验证测试源码与 main 基线的一致性，不启动、停止或重启任何服务。
Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Real API Source Baseline Gate'
Write-Host '============================================================'

$repoRoot = (git rev-parse --show-toplevel 2>$null).Trim()
if (-not $repoRoot) {
    throw '当前目录不在 Git 工作树中，无法验证 Real API 源码基线。'
}

$head = (git rev-parse HEAD 2>$null).Trim()
$originMain = (git rev-parse origin/main 2>$null).Trim()
if (-not $head -or -not $originMain) {
    throw '无法解析 HEAD 或 origin/main；请先执行 git fetch origin。'
}
if ($head -ne $originMain) {
    throw "Real API Gate 要求 HEAD 与 origin/main 完全一致。HEAD=$head, origin/main=$originMain。请先 git pull --ff-only origin main。"
}

# 当前仓库可能以 backend 目录作为 Git root，也可能以仓库根目录作为 Git root。
# 统一解析实际 Backend root，避免测试路径在不同本地工作目录下失效。
if (Test-Path (Join-Path $repoRoot 'tests/api_real')) {
    $backendRoot = $repoRoot
} elseif (Test-Path (Join-Path $repoRoot 'backend/tests/api_real')) {
    $backendRoot = Join-Path $repoRoot 'backend'
} else {
    throw "无法定位 backend/tests/api_real 或 tests/api_real；repoRoot=$repoRoot。"
}

$criticalPaths = @(
    'tests/api_real/execution_helpers.py',
    'tests/api_real/test_runtime_model_governance_api.py',
    'tests/api_real/test_workflow_checkpoint_api.py',
    'tests/unit/test_workflow_checkpoint_recovery.py'
)

Push-Location $backendRoot
try {
    $dirty = @(git status --short -- $criticalPaths)
    if ($dirty.Count -gt 0) {
        Write-Host '[ERROR] 关键 Real API / Checkpoint 测试源码存在未提交修改：'
        $dirty | ForEach-Object { Write-Host "  $_" }
        throw '禁止在源码基线不确定时执行 Real API Gate；请提交、丢弃或暂存这些修改后重新运行。'
    }

    $runtimeTest = Join-Path $backendRoot 'tests/api_real/test_runtime_model_governance_api.py'
    $helper = Join-Path $backendRoot 'tests/api_real/execution_helpers.py'
    $checkpointRecoveryTest = Join-Path $backendRoot 'tests/unit/test_workflow_checkpoint_recovery.py'

    if (-not (Test-Path $runtimeTest) -or -not (Test-Path $helper) -or -not (Test-Path $checkpointRecoveryTest)) {
        throw 'Real API 基线关键测试文件缺失。'
    }

    $runtimeText = Get-Content $runtimeTest -Raw
    $helperText = Get-Content $helper -Raw
    $checkpointRecoveryText = Get-Content $checkpointRecoveryTest -Raw

    if ($runtimeText -notmatch 'run_or_observe_execution\s*\(') {
        throw 'Runtime Model Governance Real API 测试未使用统一 Worker claim race helper。'
    }

    # 不允许在关键测试中重新复制直接 /run + 状态判断逻辑；统一通过 helper 处理 Worker claim race。
    $directRunPattern = 'run\s*=\s*client\.post\(f"/workflows/executions/\{execution_id\}/run"\)'
    if ($runtimeText -match $directRunPattern) {
        throw 'Runtime Model Governance Real API 测试仍存在直接 /run 触发实现，存在 Worker claim race 测试不一致风险。'
    }

    if ($helperText -notmatch 'expected_http_status:\s*int\s*\|\s*tuple\[int,\s*\.\.\.\]') {
        throw 'Real API Execution helper 未包含显式多 HTTP 结果契约。'
    }

    if ($checkpointRecoveryText -match '\bdatetime\.utcnow\s*\(') {
        throw 'Checkpoint Resume Candidate 测试仍使用已弃用的 datetime.utcnow()。'
    }
} finally {
    Pop-Location
}

Write-Host "[PASS] HEAD == origin/main: $head"
Write-Host '[PASS] Critical Real API / Checkpoint test sources are clean.'
Write-Host '[PASS] Runtime Model Governance tests use unified claim-race helper.'
Write-Host '[PASS] Checkpoint Resume Candidate tests do not use datetime.utcnow().'
Write-Host '[PASS] Real API source baseline verification completed.'
