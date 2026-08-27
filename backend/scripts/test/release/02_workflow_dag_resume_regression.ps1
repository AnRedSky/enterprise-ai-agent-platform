$ErrorActionPreference="Stop"

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Workflow DAG Resume Regression"
Write-Host "Scope: DAG runtime / resume / conditional branching / decision trace"
Write-Host "Mode: backend unit tests only; no database, Redis, Provider or HTTP service"
Write-Host "============================================================"

Push-Location $backendRoot
try {
    $tests = @(
        "tests/unit/test_workflow_dag_runtime.py",
        "tests/unit/test_workflow_runtime_resume.py",
        "tests/unit/test_workflow_conditional_branching.py",
        "tests/unit/test_workflow_dag_runtime_join.py",
        "tests/unit/test_workflow_dag_runtime_sequence.py",
        "tests/unit/test_workflow_dag_runtime_sequence_metadata.py",
        "tests/unit/test_workflow_dag_decision_trace.py"
    )

    Write-Host "[1/1] Running Workflow DAG Resume regression tests"
    & uv run pytest -q @tests
    if($LASTEXITCODE -ne 0){
        throw "Workflow DAG Resume regression failed. Review pytest output before continuing the Backend Gate."
    }

    Write-Host "============================================================"
    Write-Host "[PASS] Workflow DAG Resume regression completed."
    Write-Host "============================================================"
} finally {
    Pop-Location
}
