$ErrorActionPreference = "Stop"

# 职责：执行 Backend 完整 Unit Regression，并把 RuntimeWarning 提升为失败，防止异步测试 double 泄漏。
# 边界：只运行 Backend Unit Regression，不启动 PostgreSQL、Redis、API、Scheduler 或 Worker。
# 失败语义：pytest 非零退出码即脚本失败；脚本未执行到 pytest 时直接终止。

$BackendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
Set-Location $BackendRoot

Write-Host "[TEST] Backend full unit regression + RuntimeWarning gate"
Write-Host "[TEST] Backend: $BackendRoot"

& uv run pytest -q -W error::RuntimeWarning
$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    Write-Error "[FAIL] Backend full unit regression failed. pytest exit code: $ExitCode"
    exit $ExitCode
}

Write-Host "[PASS] Backend full unit regression completed successfully without RuntimeWarning."
exit 0
