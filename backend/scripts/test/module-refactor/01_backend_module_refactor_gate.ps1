$ErrorActionPreference = 'Stop'

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Backend Module Refactor Gate'
Write-Host '============================================================'

$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Set-Location $backendRoot

function Invoke-GateStep {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host "[Gate] $Name"
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "Gate failed: $Name (exit=$LASTEXITCODE)"
    }
}

# 1. 基础目标目录检查
$requiredDirectories = @(
    'app/services/agent',
    'app/infrastructure',
    'app/infrastructure/db',
    'app/middleware',
    'app/utils'
)

foreach ($directory in $requiredDirectories) {
    if (-not (Test-Path $directory -PathType Container)) {
        throw "Required module directory is missing: $directory"
    }
}

# 2. Agent 完整迁移检查：禁止旧文件、旧路径和兼容入口
$forbiddenPaths = @(
    'app/services/agent_registry.py',
    'app/services/agent/registry.py'
)

foreach ($path in $forbiddenPaths) {
    if (Test-Path $path) {
        throw "Forbidden legacy module still exists: $path"
    }
}

$legacyImportPatterns = @(
    'app\.services\.agent_registry',
    'app\.services\.agent\.registry'
)

foreach ($pattern in $legacyImportPatterns) {
    $matches = @(git grep -n -E $pattern -- '*.py' 2>$null)
    if ($matches.Count -gt 0) {
        $matches | ForEach-Object { Write-Host $_ }
        throw "Legacy import path still exists: $pattern"
    }
}

# 3. 检查 Agent 正式入口
if (-not (Test-Path 'app/services/agent/__init__.py' -PathType Leaf)) {
    throw 'Agent domain package entry is missing: app/services/agent/__init__.py'
}
if (-not (Test-Path 'app/services/agent/service.py' -PathType Leaf)) {
    throw 'Agent service implementation is missing: app/services/agent/service.py'
}
if (-not (Test-Path 'app/services/agent/repository.py' -PathType Leaf)) {
    throw 'Agent repository implementation is missing: app/services/agent/repository.py'
}

# 4. 禁止在公共 services 根目录继续新增 Agent 领域实现
$agentRootFiles = @(Get-ChildItem 'app/services' -File -Filter '*agent*' -ErrorAction SilentlyContinue)
if ($agentRootFiles.Count -gt 0) {
    $agentRootFiles | ForEach-Object { Write-Host "Unexpected root service file: $($_.FullName)" }
    throw 'Agent domain implementation remains in app/services root.'
}

# 5. 运行 Agent 相关测试；不存在对应测试时不虚构通过
$agentTests = @(Get-ChildItem 'tests' -Recurse -File -Filter '*agent*.py' -ErrorAction SilentlyContinue)
if ($agentTests.Count -gt 0) {
    Invoke-GateStep 'Agent targeted tests' {
        uv run pytest -q @($agentTests.FullName)
    }
} else {
    Write-Warning 'No Agent-specific test files were found. Targeted functional coverage was not executed.'
}

# 6. 全量 Backend regression
Invoke-GateStep 'Backend default regression' {
    uv run pytest -q
}

Write-Host '============================================================'
Write-Host 'Backend Module Refactor Gate completed.'
Write-Host '注意：脚本只报告实际执行结果；未执行的测试不会被标记为通过。'
Write-Host '============================================================'
