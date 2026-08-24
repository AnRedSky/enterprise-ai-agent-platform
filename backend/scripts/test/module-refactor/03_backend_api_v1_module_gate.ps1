$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Backend API v1 Module Gate"
Write-Host "============================================================"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot "..\..\.."))

$requiredDirectories = @(
    "app/api/v1",
    "app/api/v1/auth",
    "app/api/v1/agents",
    "app/api/v1/knowledge",
    "app/api/v1/model_providers",
    "app/api/v1/organizations",
    "app/api/v1/runtime",
    "app/api/v1/tools",
    "app/api/v1/usage",
    "app/api/v1/webhooks",
    "app/api/v1/workflows"
)
foreach ($directory in $requiredDirectories) {
    if (-not (Test-Path $directory -PathType Container)) { throw "Required API v1 directory is missing: $directory" }
}

$legacyFiles = @(
    "app/api/agents.py", "app/api/auth.py", "app/api/chat.py", "app/api/knowledge.py",
    "app/api/knowledge_ingestion.py", "app/api/knowledge_retrieval.py", "app/api/model_providers.py",
    "app/api/organizations.py", "app/api/runtime.py", "app/api/tools.py", "app/api/usage.py",
    "app/api/webhooks.py", "app/api/workflow_executions.py", "app/api/workflows.py"
)
foreach ($path in $legacyFiles) {
    if (Test-Path $path -PathType Leaf) { throw "Legacy API module still exists: $path" }
}

$legacyPatterns = @(
    "app\.api\.agents", "app\.api\.auth", "app\.api\.chat", "app\.api\.knowledge",
    "app\.api\.knowledge_ingestion", "app\.api\.knowledge_retrieval", "app\.api\.model_providers",
    "app\.api\.organizations", "app\.api\.runtime", "app\.api\.tools", "app\.api\.usage",
    "app\.api\.webhooks", "app\.api\.workflow_executions", "app\.api\.workflows"
)
foreach ($pattern in $legacyPatterns) {
    $matches = @(git grep -n -E $pattern -- "*.py" 2>$null)
    if ($matches.Count -gt 0) {
        $matches | ForEach-Object { Write-Host $_ }
        throw "Legacy API import path still exists: $pattern"
    }
}

$descriptionFiles = @(
    "app/api/__init__.py", "app/api/v1/__init__.py",
    "app/api/v1/auth/__init__.py", "app/api/v1/agents/__init__.py",
    "app/api/v1/knowledge/__init__.py", "app/api/v1/model_providers/__init__.py",
    "app/api/v1/organizations/__init__.py", "app/api/v1/runtime/__init__.py",
    "app/api/v1/tools/__init__.py", "app/api/v1/usage/__init__.py",
    "app/api/v1/webhooks/__init__.py", "app/api/v1/workflows/__init__.py"
)
$env:API_V1_DESCRIPTION_FILES = $descriptionFiles -join "|"
$descriptionCheck = @"
from pathlib import Path
import os
for name in os.environ["API_V1_DESCRIPTION_FILES"].split("|"):
    text = Path(name).read_text(encoding="utf-8")
    if "\u804c\u8d23\uff1a" not in text or "\u8fb9\u754c\uff1a" not in text:
        raise SystemExit(f"API module description or boundary is missing: {name}")
"@
$descriptionCheck | uv run python -
if ($LASTEXITCODE -ne 0) { throw "API v1 module description validation failed." }

Write-Host "[Gate] Application import"
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
if ($LASTEXITCODE -ne 0) { throw "Application import failed." }

Write-Host "[Gate] API Contract tests"
uv run pytest -q tests/api_contract
if ($LASTEXITCODE -ne 0) { throw "API Contract tests failed." }

Write-Host "[Gate] Backend regression"
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw "Backend regression failed." }

Write-Host "============================================================"
Write-Host "Backend API v1 Module Gate completed."
Write-Host "============================================================"
