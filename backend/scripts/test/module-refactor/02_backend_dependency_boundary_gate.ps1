$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Dependency Boundary Gate"
Write-Host "============================================================"

$BackendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
Set-Location $BackendRoot

Write-Host "[Gate] Python application import"
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
if ($LASTEXITCODE -ne 0) { throw "Application import failed (exit=$LASTEXITCODE)" }

Write-Host "[Gate] Canonical dependency test"
uv run pytest -q tests/unit/test_dependency_boundary.py
if ($LASTEXITCODE -ne 0) { throw "Dependency boundary test failed (exit=$LASTEXITCODE)" }

Write-Host "[Gate] Legacy dependency path search"
$legacyPatterns = @(
    "app\.dependencies\.db",
    "app/api/dependencies.py",
    "app\\api\\dependencies.py"
)

$matches = Get-ChildItem -Path "app" -Recurse -File -Include *.py |
    Select-String -Pattern $legacyPatterns -SimpleMatch:$false

if ($matches) {
    $details = $matches | ForEach-Object { "$($_.Path):$($_.LineNumber):$($_.Line.Trim())" }
    throw "Legacy dependency path still exists:`n$($details -join "`n")"
}

Write-Host "[Gate] Canonical dependency implementation search"
$canonical = Get-ChildItem -Path "app/dependencies" -Recurse -File -Include *.py |
    Select-String -Pattern "from app.infrastructure.db import get_db_session|async def get_db" -SimpleMatch:$false

if (-not $canonical) {
    throw "Canonical database dependency implementation was not found under app/dependencies"
}

Write-Host "PASS: dependency boundary gate"
