$ErrorActionPreference = "Stop"

# 职责：执行 Durable Resume / DAG / Frontier 当前回归单元测试。
# 边界：只运行 Backend Unit Regression，不启动 PostgreSQL、Redis、API、Scheduler 或 Worker。
# 失败语义：pytest 非零退出码即脚本失败；脚本未执行到 pytest 时直接终止。

$BackendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
Set-Location $BackendRoot

$TestFiles = @(
    "tests/unit/test_durable_resume_runtime.py",
    "tests/unit/test_workflow_execution_idempotency.py",
    "tests/unit/test_workflow_execution_governance.py",
    "tests/unit/test_workflow_dag_contract.py",
    "tests/unit/test_workflow_dag_runtime_initialization.py",
    "tests/unit/test_frontier_progression.py",
    "tests/unit/test_frontier_progression_lifecycle.py",
    "tests/unit/test_frontier_duplicate_completion.py",
    "tests/unit/test_frontier_duplicate_consumption.py",
    "tests/unit/test_frontier_claim_lock_order.py",
    "tests/unit/test_frontier_failure_terminalization.py",
    "tests/unit/test_frontier_failure_transaction.py",
    "tests/unit/test_frontier_claim_completion_fencing.py"
)

Write-Host "[TEST] Durable Resume / Execution / DAG / Frontier targeted regression"
Write-Host "[TEST] Backend: $BackendRoot"
Write-Host "[TEST] Tests:"
$TestFiles | ForEach-Object { Write-Host "  - $_" }

& uv run pytest -q @TestFiles
$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    Write-Error "[FAIL] Targeted regression failed. pytest exit code: $ExitCode"
    exit $ExitCode
}

Write-Host "[PASS] Targeted regression completed successfully."
exit 0
