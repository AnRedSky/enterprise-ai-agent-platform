$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Backend Runtime Boundary Gate"
Write-Host "============================================================"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot "..\..\.."))

# 本 Gate 只验证 Runtime 领域的物理边界、唯一入口和中文职责说明；不重复 API v1 / Dependency / 全量 Regression Gate。
$requiredDirectories = @(
    "app/runtime/memory",
    "app/runtime/model",
    "app/runtime/workflow"
)
foreach ($directory in $requiredDirectories) {
    if (-not (Test-Path $directory -PathType Container)) {
        throw "Required Runtime module directory is missing: $directory"
    }
}

$requiredFiles = @(
    "app/runtime/memory/__init__.py",
    "app/runtime/memory/context.py",
    "app/runtime/model/__init__.py",
    "app/runtime/model/gateway.py",
    "app/runtime/workflow/__init__.py",
    "app/runtime/workflow/circuit_breaker.py",
    "app/runtime/workflow/runtime.py"
)
foreach ($path in $requiredFiles) {
    if (-not (Test-Path $path -PathType Leaf)) {
        throw "Required Runtime implementation is missing: $path"
    }
}

# Runtime 根目录只允许包目录与基础包文件，不得重新堆放旧的 Runtime 单文件实现。
$rootRuntimeFiles = @(Get-ChildItem "app/runtime" -File -Filter "*.py" -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne "__init__.py" })
if ($rootRuntimeFiles.Count -gt 0) {
    $rootRuntimeFiles | ForEach-Object { Write-Host "Unexpected root Runtime file: $($_.FullName)" }
    throw "Root app/runtime contains a legacy Runtime implementation."
}

$forbiddenPaths = @(
    "app/runtime/workflow_runtime.py",
    "app/runtime/model_gateway.py",
    "app/runtime/memory_context.py",
    "app/runtime/provider.py",
    "app/runtime/openai_provider.py",
    "app/runtime/agent_runtime.py",
    "app/services/runtime_model_governance.py",
    "app/services/model_provider_governance_contract.py",
    "app/services/circuit_breaker.py"
)
foreach ($path in $forbiddenPaths) {
    if (Test-Path $path -PathType Leaf) {
        throw "Forbidden legacy Runtime/Governance implementation still exists: $path"
    }
}

$legacyImportPatterns = @(
    "app\.runtime\.workflow_runtime",
    "app\.runtime\.model_gateway",
    "app\.runtime\.memory_context",
    "app\.runtime\.provider",
    "app\.runtime\.openai_provider",
    "app\.runtime\.agent_runtime",
    "app\.services\.runtime_model_governance",
    "app\.services\.model_provider_governance_contract",
    "app\.services\.circuit_breaker"
)
foreach ($pattern in $legacyImportPatterns) {
    $matches = @(git grep -n -E $pattern -- "*.py" 2>$null)
    if ($matches.Count -gt 0) {
        $matches | ForEach-Object { Write-Host $_ }
        throw "Legacy Runtime/Governance import path still exists: $pattern"
    }
}

# Governance 必须由 Model Service / Workflow Service 承担，Runtime 只负责执行编排；不得复制治理实现。
$forbiddenGovernanceSymbols = @(
    "class ModelProviderGovernance",
    "class RuntimeModelGovernance",
    "def select_provider",
    "def resolve_model_provider"
)
foreach ($symbol in $forbiddenGovernanceSymbols) {
    $matches = @(git grep -n -F $symbol -- "app/runtime/*.py" "app/runtime/**/*.py" 2>$null)
    if ($matches.Count -gt 0) {
        $matches | ForEach-Object { Write-Host $_ }
        throw "Runtime must not duplicate Governance implementation: $symbol"
    }
}

$descriptionFiles = $requiredFiles
$env:RUNTIME_BOUNDARY_DESCRIPTION_FILES = $descriptionFiles -join "|"
$descriptionCheck = @"
from pathlib import Path
import os
for name in os.environ["RUNTIME_BOUNDARY_DESCRIPTION_FILES"].split("|"):
    text = Path(name).read_text(encoding="utf-8")
    if "\u804c\u8d23\uff1a" not in text or "\u8fb9\u754c\uff1a" not in text:
        raise SystemExit(f"Runtime module description or boundary is missing: {name}")
"@
$descriptionCheck | uv run python -
if ($LASTEXITCODE -ne 0) { throw "Runtime module description validation failed." }

Write-Host "[Gate] Application import"
uv run python -c "from app.main import app; from app.runtime.model import ModelGateway; from app.runtime.workflow import WorkflowRuntime; print('RUNTIME_IMPORT_OK')"
if ($LASTEXITCODE -ne 0) { throw "Runtime application import failed." }

Write-Host "[Gate] Runtime targeted unit tests"
uv run pytest -q tests/unit -k "runtime or gateway or circuit_breaker" --disable-warnings
if ($LASTEXITCODE -ne 0) { throw "Runtime targeted unit tests failed." }

Write-Host "============================================================"
Write-Host "Backend Runtime Boundary Gate completed."
Write-Host "============================================================"