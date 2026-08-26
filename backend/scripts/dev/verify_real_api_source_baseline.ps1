$ErrorActionPreference="Stop"

# 本脚本只验证测试源码与 main 基线的一致性，不启动、停止或重启任何服务。
Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Real API Source Baseline Gate"
Write-Host "============================================================"

$repoRoot = (git rev-parse --show-toplevel 2>$null).Trim()
if(-not $repoRoot){
  throw "当前目录不在 Git 工作树中，无法验证 Real API 源码基线。"
}

$head = (git rev-parse HEAD 2>$null).Trim()
$originMain = (git rev-parse origin/main 2>$null).Trim()
if(-not $head -or -not $originMain){
  throw "无法解析 HEAD 或 origin/main；请先执行 git fetch origin。"
}
if($head -ne $originMain){
  throw "Real API Gate 要求 HEAD 与 origin/main 完全一致。HEAD=$head, origin/main=$originMain。请先 git pull --ff-only origin main。"
}

$criticalPaths = @(
  "backend/tests/api_real/execution_helpers.py",
  "backend/tests/api_real/test_runtime_model_governance_api.py",
  "backend/tests/api_real/test_workflow_checkpoint_api.py",
  "backend/tests/unit/test_workflow_checkpoint_recovery.py"
)

$dirty = @(git status --short -- $criticalPaths)
if($dirty.Count -gt 0){
  Write-Host "[ERROR] 关键 Real API / Checkpoint 测试源码存在未提交修改："
  $dirty | ForEach-Object { Write-Host "  $_" }
  throw "禁止在源码基线不确定时执行 Real API Gate；请提交、丢弃或暂存这些修改后重新运行。"
}

$runtimeTest = Join-Path $repoRoot "backend/tests/api_real/test_runtime_model_governance_api.py"
$helper = Join-Path $repoRoot "backend/tests/api_real/execution_helpers.py"
$runtimeText = Get-Content $runtimeTest -Raw
$helperText = Get-Content $helper -Raw

if($runtimeText -notmatch "run_or_observe_execution\("){
  throw "Runtime Model Governance Real API 测试未使用统一 Worker claim race helper。"
}
if($runtimeText -match "run = client\.post\(f\"/workflows/executions/\{execution_id\}/run\"\)"){
  throw "Runtime Model Governance Real API 测试仍存在直接 /run 触发实现，存在 Worker claim race 测试不一致风险。"
}
if($helperText -notmatch "expected_http_status: int \| tuple\[int, \.\.\.\]"){
  throw "Real API Execution helper 未包含显式多 HTTP 结果契约。"
}

Write-Host "[PASS] HEAD == origin/main: $head"
Write-Host "[PASS] Critical Real API / Checkpoint test sources are clean."
Write-Host "[PASS] Runtime Model Governance tests use unified claim-race helper."
Write-Host "[PASS] Real API source baseline verification completed."
