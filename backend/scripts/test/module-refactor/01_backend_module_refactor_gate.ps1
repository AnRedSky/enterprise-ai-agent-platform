$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Backend Module Refactor Gate"
Write-Host "============================================================"

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
Set-Location $backendRoot

function Invoke-GateStep {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )

    Write-Host "[Gate] $Name"
    $global:LASTEXITCODE = 0
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Gate failed: $Name (exit=$LASTEXITCODE)"
    }
}

$requiredDirectories = @(
    "app/services/agent",
    "app/services/knowledge",
    "app/services/memory",
    "app/services/model",
    "app/services/workflow",
    "app/infrastructure",
    "app/infrastructure/db",
    "app/infrastructure/providers",
    "app/middleware",
    "app/utils",
    "app/runtime/memory",
    "app/runtime/model"
)
foreach ($directory in $requiredDirectories) {
    if (-not (Test-Path $directory -PathType Container)) {
        throw "Required module directory is missing: $directory"
    }
}

$forbiddenPaths = @(
    "app/services/agent_registry.py",
    "app/services/agent/registry.py",
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
    "app/runtime/memory_context.py",
    "app/runtime/model_gateway.py",
    "app/runtime/provider.py",
    "app/runtime/openai_provider.py",
    "app/services/workflow_execution.py",
    "app/services/workflow_governance.py",
    "app/services/workflow_registry.py"
)
foreach ($path in $forbiddenPaths) {
    if (Test-Path $path) {
        throw "Forbidden legacy module still exists: $path"
    }
}

$legacyImportPatterns = @(
    "app\.services\.agent_registry",
    "app\.services\.agent\.registry",
    "app\.services\.knowledge_ingestion",
    "app\.services\.knowledge_registry",
    "app\.services\.knowledge_retrieval",
    "app\.services\.knowledge_retrieval_contract",
    "app\.services\.knowledge_vector_indexing",
    "app\.services\.hybrid_knowledge_retrieval",
    "app\.services\.hybrid_knowledge_retrieval_service",
    "app\.services\.vector_knowledge_retrieval",
    "app\.services\.memory_service",
    "app\.runtime\.memory_context",
    "app\.services\.embedding_provider",
    "app\.services\.mock_embedding_provider",
    "app\.services\.ollama_embedding_provider",
    "app\.services\.vector_retrieval_provider",
    "app\.services\.model_provider",
    "app\.services\.model_provider_governance_contract",
    "app\.services\.runtime_model_governance",
    "app\.runtime\.model_gateway",
    "app\.runtime\.provider",
    "app\.runtime\.openai_provider",
    "app\.services\.workflow_execution",
    "app\.services\.workflow_governance",
    "app\.services\.workflow_registry"
)
foreach ($pattern in $legacyImportPatterns) {
    $matches = @(git grep -n -E $pattern -- "*.py" 2>$null)
    if ($matches.Count -gt 0) {
        $matches | ForEach-Object { Write-Host $_ }
        throw "Legacy import path still exists: $pattern"
    }
}

$forbiddenDatabaseDependencyPatterns = @(
    "app\.api\.dependencies",
    "from app\.dependencies\.db import SessionLocal",
    "from app\.dependencies\.db import .*SessionLocal"
)
foreach ($pattern in $forbiddenDatabaseDependencyPatterns) {
    $matches = @(git grep -n -E $pattern -- "*.py" 2>$null)
    if ($matches.Count -gt 0) {
        $matches | ForEach-Object { Write-Host $_ }
        throw "Forbidden database dependency boundary import exists: $pattern"
    }
}

$requiredMigratedFiles = @(
    "app/services/agent/service.py",
    "app/services/agent/repository.py",
    "app/services/knowledge/__init__.py",
    "app/services/memory/__init__.py",
    "app/services/memory/service.py",
    "app/services/model/__init__.py",
    "app/services/model/contract.py",
    "app/services/model/provider.py",
    "app/services/model/routing.py",
    "app/services/model/governance.py",
    "app/services/workflow/__init__.py",
    "app/services/workflow/execution.py",
    "app/services/workflow/governance.py",
    "app/services/workflow/registry.py",
    "app/runtime/memory/__init__.py",
    "app/runtime/memory/context.py",
    "app/runtime/model/__init__.py",
    "app/runtime/model/gateway.py"
)
foreach ($path in $requiredMigratedFiles) {
    if (-not (Test-Path $path -PathType Leaf)) {
        throw "Required migrated implementation is missing: $path"
    }
}

foreach ($file in @(
    "registry.py",
    "ingestion.py",
    "retrieval.py",
    "vector_indexing.py",
    "vector_retrieval.py",
    "hybrid.py",
    "hybrid_service.py"
)) {
    if (-not (Test-Path "app/services/knowledge/$file" -PathType Leaf)) {
        throw "Knowledge implementation is missing: $file"
    }
}

foreach ($file in @(
    "embedding.py",
    "mock_embedding.py",
    "ollama_embedding.py",
    "vector_retrieval.py",
    "model.py",
    "mock_model.py",
    "openai_model.py"
)) {
    if (-not (Test-Path "app/infrastructure/providers/$file" -PathType Leaf)) {
        throw "Provider implementation is missing: $file"
    }
}

$workflowModules = @(
    "app/services/workflow/__init__.py",
    "app/services/workflow/execution.py",
    "app/services/workflow/governance.py",
    "app/services/workflow/registry.py"
)
foreach ($module in $workflowModules) {
    $content = Get-Content $module -Raw
    if ($content -notmatch "职责：") {
        throw "Workflow module description is missing: $module"
    }
}

foreach ($filter in @(
    "*agent*",
    "*knowledge*",
    "*memory*",
    "*embedding_provider*",
    "*vector_retrieval_provider*",
    "*model_provider*",
    "*runtime_model_governance*",
    "*workflow*"
)) {
    $rootFiles = @(Get-ChildItem "app/services" -File -Filter $filter -ErrorAction SilentlyContinue)
    if ($rootFiles.Count -gt 0) {
        $rootFiles | ForEach-Object { Write-Host "Unexpected root service file: $($_.FullName)" }
        throw "Duplicate domain/provider implementation remains in app/services root: $filter"
    }
}

$agentTests = @(Get-ChildItem "tests" -Recurse -File -Filter "*agent*.py" -ErrorAction SilentlyContinue)
if ($agentTests.Count -eq 0) { throw "Agent module tests are missing." }
$knowledgeTests = @(Get-ChildItem "tests" -Recurse -File -Filter "*knowledge*.py" -ErrorAction SilentlyContinue)
if ($knowledgeTests.Count -eq 0) { throw "Knowledge module tests are missing." }
$providerTests = @(Get-ChildItem "tests" -Recurse -File -Filter "*provider*.py" -ErrorAction SilentlyContinue)
if ($providerTests.Count -eq 0) { throw "Provider module tests are missing." }
$workflowTests = @(Get-ChildItem "tests" -Recurse -File -Filter "*workflow*.py" -ErrorAction SilentlyContinue)
if ($workflowTests.Count -eq 0) { throw "Workflow module tests are missing." }

Invoke-GateStep "Agent targeted tests" { uv run pytest -q tests/unit -k "agent" --disable-warnings }
Invoke-GateStep "Knowledge targeted tests" { uv run pytest -q tests/unit -k "knowledge" --disable-warnings }
Invoke-GateStep "Infrastructure provider targeted tests" { uv run pytest -q tests/unit -k "provider" --disable-warnings }
Invoke-GateStep "Model targeted tests" { uv run pytest -q tests/unit/test_model_gateway.py tests/unit/test_model_provider_governance_contract.py tests/unit/test_runtime_model_governance.py --disable-warnings }
Invoke-GateStep "Workflow targeted tests" { uv run pytest -q tests/unit -k "workflow" --disable-warnings }
Invoke-GateStep "Backend default regression" { uv run pytest -q }

Write-Host "============================================================"
Write-Host "Backend Module Refactor Gate completed."
Write-Host "Only locally executed test results are reported."
Write-Host "============================================================"
