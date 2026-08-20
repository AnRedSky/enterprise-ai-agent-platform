$ErrorActionPreference="Stop"
Write-Host "Backend full regression"
uv run pytest -q
if($LASTEXITCODE -ne 0){throw "Backend regression failed."}
Write-Host "[PASS] Backend regression"
