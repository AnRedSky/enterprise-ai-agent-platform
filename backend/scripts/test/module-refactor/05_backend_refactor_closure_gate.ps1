$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Backend Refactor Closure Gate"
Write-Host "============================================================"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot "..\..\.."))

# 本 Gate 是全部模块重构的最终静态收口检查；不重复执行领域测试，只确认旧边界、重复入口、目录结构和模块职责说明没有回退。
$requiredRoots = @(
    "app/api/v1",
    "app/services",
    "app/runtime",
    "app/infrastructure/providers"
)
foreach ($path in $requiredRoots) {
    if (-not (Test-Path $path -PathType Container)) {
        throw "Required refactor root is missing: $path"
    }
}

# 重构完成后，旧的扁平领域入口不得重新出现。
$forbiddenFiles = @(
    "app/services/agent_registry.py",
    "app/services/knowledge_ingestion.py",
    "app/services/knowledge_registry.py",
    "app/services/knowledge_retrieval.py",
    "app/services/knowledge_retrieval_contract.py",
    "app/services/knowledge_vector_indexing.py",
    "app/services/hybrid_knowledge_retrieval.py",
    "app/services/hybrid_knowledge_retrieval_service.py",
    "app/services/vector_knowledge_retrieval.py",
    "app/services/memory_service.py",
    "app/services/embedding_provider.py",
    "app/services/mock_embedding_provider.py",
    "app/services/ollama_embedding_provider.py",
    "app/services/vector_retrieval_provider.py",
    "app/services/model_provider.py",
    "app/services/model_provider_governance_contract.py",
    "app/services/runtime_model_governance.py",
    "app/services/circuit_breaker.py",
    "app/services/workflow_execution.py",
    "app/services/workflow_governance.py",
    "app/services/workflow_registry.py",
    "app/services/workflow_trigger.py",
    "app/services/workflow_trigger_schedule.py",
    "app/services/webhook_trigger.py",
    "app/services/organization.py",
    "app/services/observability_service.py",
    "app/services/retrieval_evaluation.py",
    "app/services/runtime_query.py",
    "app/services/session_service.py",
    "app/services/usage_accounting.py",
    "app/runtime/workflow_runtime.py",
    "app/runtime/model_gateway.py",
    "app/runtime/memory_context.py",
    "app/runtime/provider.py",
    "app/runtime/openai_provider.py",
    "app/runtime/agent_runtime.py",
    "app/tools/registry.py"
)
foreach ($path in $forbiddenFiles) {
    if (Test-Path $path -PathType Leaf) {
        throw "Legacy implementation still exists: $path"
    }
}

$forbiddenImports = @(
    "app\.api\.(agents|auth|chat|knowledge|knowledge_ingestion|knowledge_retrieval|model_providers|organizations|runtime|tools|usage|webhooks|workflows|workflow_executions)",
    "app\.services\.(agent_registry|knowledge_ingestion|knowledge_registry|knowledge_retrieval|knowledge_retrieval_contract|knowledge_vector_indexing|hybrid_knowledge_retrieval|hybrid_knowledge_retrieval_service|vector_knowledge_retrieval|memory_service|embedding_provider|mock_embedding_provider|ollama_embedding_provider|vector_retrieval_provider|model_provider|model_provider_governance_contract|runtime_model_governance|circuit_breaker|workflow_execution|workflow_governance|workflow_registry|workflow_trigger|workflow_trigger_schedule|webhook_trigger|organization|observability_service|retrieval_evaluation|runtime_query|session_service|usage_accounting)",
    "app\.runtime\.(workflow_runtime|model_gateway|memory_context|provider|openai_provider|agent_runtime)",
    "app\.tools\.registry"
)
foreach ($pattern in $forbiddenImports) {
    $matches = @(git grep -n -E $pattern -- "*.py" 2>$null)
    if ($matches.Count -gt 0) {
        $matches | ForEach-Object { Write-Host $_ }
        throw "Legacy import path still exists: $pattern"
    }
}

# 领域代码不能重新堆回 services/runtime 根目录；正式实现必须位于领域子模块。
foreach ($root in @("app/services", "app/runtime")) {
    $files = @(Get-ChildItem $root -File -Filter "*.py" -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne "__init__.py" })
    if ($files.Count -gt 0) {
        $files | ForEach-Object { Write-Host "Unexpected root module file: $($_.FullName)" }
        throw "Root $root contains a domain implementation outside its canonical submodule."
    }
}

# Provider 是技术适配的唯一入口；同名 Provider 类不得在领域 Service / Runtime 中再次实现。
$providerDefinitions = @(git grep -n -E "^class [A-Za-z0-9_]*Provider\b" -- "app/*.py" "app/**/*.py" 2>$null)
$providerOutsideInfrastructure = @($providerDefinitions | Where-Object { $_ -notmatch "^app/infrastructure/providers/" })
$providerOutsideInfrastructure = @($providerOutsideInfrastructure | Where-Object { $_ -notmatch "app/services/model/provider\.py" })
if ($providerOutsideInfrastructure.Count -gt 0) {
    $providerOutsideInfrastructure | ForEach-Object { Write-Host $_ }
    throw "Provider implementation exists outside the canonical infrastructure/providers boundary."
}

# Runtime 不得重新承担 Provider Governance / 路由职责。
$runtimeGovernancePatterns = @(
    "class ModelProviderGovernance",
    "class RuntimeModelGovernance",
    "def select_provider",
    "def resolve_model_provider"
)
foreach ($symbol in $runtimeGovernancePatterns) {
    $matches = @(git grep -n -F $symbol -- "app/runtime/*.py" "app/runtime/**/*.py" 2>$null)
    if ($matches.Count -gt 0) {
        $matches | ForEach-Object { Write-Host $_ }
        throw "Runtime contains duplicated Governance implementation: $symbol"
    }
}

# 所有当前正式领域包必须具备中文职责/边界说明；不允许通过空洞注释满足要求。
$descriptionFiles = @(
    "app/services/agent/__init__.py",
    "app/services/knowledge/__init__.py",
    "app/services/memory/__init__.py",
    "app/services/model/__init__.py",
    "app/services/observability/__init__.py",
    "app/services/organization/__init__.py",
    "app/services/retrieval_evaluation/__init__.py",
    "app/services/runtime_query/__init__.py",
    "app/services/session_service/__init__.py",
    "app/services/tool/__init__.py",
    "app/services/trigger/__init__.py",
    "app/services/usage_accounting/__init__.py",
    "app/services/workflow/__init__.py",
    "app/services/workflow_scheduler/__init__.py",
    "app/runtime/memory/__init__.py",
    "app/runtime/model/__init__.py",
    "app/runtime/workflow/__init__.py",
    "app/infrastructure/providers/__init__.py"
)
$env:REFACTOR_CLOSURE_DESCRIPTION_FILES = $descriptionFiles -join "|"
$descriptionCheck = @"
from pathlib import Path
import os
for name in os.environ["REFACTOR_CLOSURE_DESCRIPTION_FILES"].split("|"):
    text = Path(name).read_text(encoding="utf-8")
    if "职责：" not in text or "边界：" not in text:
        raise SystemExit(f"Canonical module description or boundary is missing: {name}")
"@
$descriptionCheck | uv run python -
if ($LASTEXITCODE -ne 0) { throw "Canonical module description validation failed." }

Write-Host "[Gate] Canonical application import"
uv run python -c "from app.main import app; from app.api.v1 import router as api_router; from app.runtime.model import ModelGateway; from app.runtime.workflow import WorkflowRuntime; print('REFACTOR_CLOSURE_IMPORT_OK')"
if ($LASTEXITCODE -ne 0) { throw "Canonical refactor import failed." }

Write-Host "============================================================"
Write-Host "Backend Refactor Closure Gate completed."
Write-Host "============================================================"
