$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Backend Module Refactor Gate"
Write-Host "============================================================"

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Set-Location $backendRoot

function Invoke-GateStep {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "[Gate] $Name"
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "Gate failed: $Name (exit=$LASTEXITCODE)" }
}

$requiredDirectories = @('app/services/agent','app/services/knowledge','app/infrastructure','app/infrastructure/db','app/infrastructure/providers','app/middleware','app/utils')
foreach ($directory in $requiredDirectories) {
    if (-not (Test-Path $directory -PathType Container)) { throw "Required module directory is missing: $directory" }
}

$forbiddenPaths = @(
    'app/services/agent_registry.py','app/services/agent/registry.py',
    'app/services/knowledge_ingestion.py','app/services/knowledge_registry.py','app/services/knowledge_retrieval.py',
    'app/services/knowledge_retrieval_contract.py','app/services/knowledge_vector_indexing.py',
    'app/services/hybrid_knowledge_retrieval.py','app/services/hybrid_knowledge_retrieval_service.py','app/services/vector_knowledge_retrieval.py',
    'app/services/embedding_provider.py','app/services/mock_embedding_provider.py','app/services/ollama_embedding_provider.py','app/services/vector_retrieval_provider.py'
)
foreach ($path in $forbiddenPaths) {
    if (Test-Path $path) { throw "Forbidden legacy module still exists: $path" }
}

$legacyImportPatterns = @(
    'app\.services\.agent_registry','app\.services\.agent\.registry',
    'app\.services\.knowledge_ingestion','app\.services\.knowledge_registry','app\.services\.knowledge_retrieval',
    'app\.services\.knowledge_retrieval_contract','app\.services\.knowledge_vector_indexing',
    'app\.services\.hybrid_knowledge_retrieval','app\.services\.hybrid_knowledge_retrieval_service','app\.services\.vector_knowledge_retrieval',
    'app\.services\.embedding_provider','app\.services\.mock_embedding_provider','app\.services\.ollama_embedding_provider','app\.services\.vector_retrieval_provider'
)
foreach ($pattern in $legacyImportPatterns) {
    $matches = @(git grep -n -E $pattern -- '*.py' 2>$null)
    if ($matches.Count -gt 0) {
        $matches | ForEach-Object { Write-Host $_ }
        throw "Legacy import path still exists: $pattern"
    }
}

if (-not (Test-Path 'app/services/agent/service.py' -PathType Leaf)) { throw "Agent service implementation is missing." }
if (-not (Test-Path 'app/services/agent/repository.py' -PathType Leaf)) { throw "Agent repository implementation is missing." }
if (-not (Test-Path 'app/services/knowledge/__init__.py' -PathType Leaf)) { throw "Knowledge domain entry is missing." }
foreach ($file in @('registry.py','ingestion.py','retrieval.py','vector_indexing.py','vector_retrieval.py','hybrid.py','hybrid_service.py')) {
    if (-not (Test-Path "app/services/knowledge/$file" -PathType Leaf)) { throw "Knowledge implementation is missing: $file" }
}

foreach ($file in @('embedding.py','mock_embedding.py','ollama_embedding.py','vector_retrieval.py')) {
    if (-not (Test-Path "app/infrastructure/providers/$file" -PathType Leaf)) { throw "Provider implementation is missing: $file" }
}

# 已迁移领域禁止在 services 根目录保留第二套实现；Provider 也必须只存在于 infrastructure/providers。
foreach ($filter in @('*agent*','*knowledge*','*embedding_provider*','*vector_retrieval_provider*')) {
    $rootFiles = @(Get-ChildItem 'app/services' -File -Filter $filter -ErrorAction SilentlyContinue)
    if ($rootFiles.Count -gt 0) {
        $rootFiles | ForEach-Object { Write-Host "Unexpected root service file: $($_.FullName)" }
        throw "Duplicate domain/provider implementation remains in app/services root: $filter"
    }
}

$agentTests = @(Get-ChildItem 'tests' -Recurse -File -Filter '*agent*.py' -ErrorAction SilentlyContinue)
if ($agentTests.Count -gt 0) { Invoke-GateStep 'Agent targeted tests' { uv run pytest -q @($agentTests.FullName) } }

$knowledgeTests = @(Get-ChildItem 'tests' -Recurse -File -Filter '*knowledge*.py' -ErrorAction SilentlyContinue)
if ($knowledgeTests.Count -gt 0) { Invoke-GateStep 'Knowledge targeted tests' { uv run pytest -q @($knowledgeTests.FullName) } } else { Write-Warning 'No Knowledge-specific test files were found.' }

$providerTests = @(
    'tests/unit/test_embedding_provider.py',
    'tests/unit/test_mock_embedding_provider.py',
    'tests/unit/test_ollama_embedding_provider.py',
    'tests/unit/test_vector_retrieval_provider.py'
)
$existingProviderTests = @($providerTests | Where-Object { Test-Path $_ })
if ($existingProviderTests.Count -gt 0) { Invoke-GateStep 'Infrastructure provider targeted tests' { uv run pytest -q @($existingProviderTests) } }

Invoke-GateStep 'Backend default regression' { uv run pytest -q }

Write-Host "============================================================"
Write-Host "Backend Module Refactor Gate completed."
Write-Host "注意：脚本只报告实际执行结果；未执行的测试不会被标记为通过。"
Write-Host "============================================================"
