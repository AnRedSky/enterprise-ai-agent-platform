[CmdletBinding()]
param(
    [switch]$WarningsAsErrors
)

$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
Set-Location $backend

Write-Host "[TEST] Phase 2.7 workflow full regression" -ForegroundColor Cyan
Write-Host "[TEST] Backend: $backend"

$tests = @(
    "tests/unit/test_durable_resume_runtime.py",
    "tests/unit/test_workflow_execution_idempotency.py",
    "tests/unit/test_workflow_execution_governance.py",
    "tests/unit/test_workflow_dag_contract.py",
    "tests/unit/test_workflow_dag_runtime_initialization.py",
    "tests/unit/test_frontier_duplicate_completion.py",
    "tests/unit/test_frontier_duplicate_consumption.py",
    "tests/unit/test_frontier_claim_lock_order.py",
    "tests/unit/test_frontier_claim_fencing.py",
    "tests/unit/test_frontier_claim_completion_fencing.py",
    "tests/unit/test_frontier_failure_terminalization.py",
    "tests/unit/test_frontier_failure_transaction.py",
    "tests/unit/test_frontier_progression.py",
    "tests/unit/test_frontier_progression_lifecycle.py",
    "tests/unit/test_frontier_progression_worker_epoch.py",
    "tests/unit/test_frontier_recovery_contract.py",
    "tests/unit/test_frontier_replay_lifecycle_audit.py",
    "tests/unit/test_frontier_stale_lease_completion.py",
    "tests/unit/test_frontier_tenant_candidate.py",
    "tests/unit/test_frontier_terminal_replay_lifecycle.py",
    "tests/unit/test_frontier_terminalization_atomicity.py",
    "tests/unit/test_workflow_checkpoint_frontier_idempotency.py",
    "tests/unit/test_workflow_checkpoint_integration.py",
    "tests/unit/test_workflow_checkpoint_sequence_allocation.py",
    "tests/unit/test_workflow_checkpoint_tenant_boundary.py",
    "tests/unit/test_workflow_condition_evaluator.py",
    "tests/unit/test_workflow_dag_decision_trace_idempotency.py",
    "tests/unit/test_workflow_dag_executor.py",
    "tests/unit/test_workflow_dag_frontier_progression.py",
    "tests/unit/test_workflow_dag_join_executor.py",
    "tests/unit/test_workflow_dag_runtime_join.py",
    "tests/unit/test_workflow_execution_checkpoint.py",
    "tests/unit/test_workflow_execution_concurrency.py",
    "tests/unit/test_workflow_execution_resume.py",
    "tests/unit/test_workflow_execution_terminal_ownership.py",
    "tests/unit/test_workflow_execution_worker_fencing.py",
    "tests/unit/test_workflow_frontier.py",
    "tests/unit/test_workflow_frontier_repository.py",
    "tests/unit/test_workflow_automatic_recovery_service.py",
    "tests/unit/test_workflow_automatic_recovery_telemetry.py",
    "tests/unit/test_workflow_recovery_lifecycle_closure.py",
    "tests/unit/test_workflow_recovery_scheduler.py",
    "tests/unit/test_workflow_recovery_trace_link.py",
    "tests/unit/test_workflow_recovery_worker_trace.py",
    "tests/unit/test_workflow_resume_api_contract.py",
    "tests/unit/test_workflow_resume_contract.py",
    "tests/unit/test_workflow_resume_contract_tenant_scope.py",
    "tests/unit/test_workflow_resume_reconciliation.py",
    "tests/unit/test_workflow_resume_transaction_boundary.py",
    "tests/unit/test_workflow_runtime.py",
    "tests/unit/test_workflow_runtime_resume.py"
)

$missing = $tests | Where-Object { -not (Test-Path $_) }
if ($missing.Count -gt 0) {
    Write-Host "[FAIL] Missing test files:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" }
    exit 2
}

$args = @("pytest", "-q")
if ($WarningsAsErrors) {
    $args += "-W"
    $args += "error"
}
$args += $tests

Write-Host "[TEST] Tests: $($tests.Count) files"
& uv run @args
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "[FAIL] Phase 2.7 workflow regression failed with exit code $exitCode." -ForegroundColor Red
    exit $exitCode
}

Write-Host "[PASS] Phase 2.7 workflow regression completed successfully." -ForegroundColor Green
