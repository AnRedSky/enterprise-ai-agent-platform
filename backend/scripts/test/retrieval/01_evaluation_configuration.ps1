[CmdletBinding()]
param(
    [ValidateSet("ollama", "openai-compatible")]
    [string]$EmbeddingProvider,
    [string]$EmbeddingBaseUrl,
    [string]$EmbeddingModel,
    [int]$EmbeddingDimension = 0,
    [int]$K = 3,
    [double]$MinScore = 0.0,
    [double]$MinRecallAtK,
    [double]$MinPrecisionAtK,
    [double]$MinMrr,
    [double]$MinCitationCorrectness,
    [double]$MaxErrorRate = 0.0
)

$ErrorActionPreference = "Stop"
$BackendRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
Set-Location $BackendRoot

function Invoke-Gate([string]$Title, [scriptblock]$Command) {
    Write-Host "============================================================"
    Write-Host $Title
    Write-Host "============================================================"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Title failed with exit code $LASTEXITCODE."
    }
}

$runnerArgs = @(
    ".\scripts\evaluation\knowledge\run_knowledge_retrieval_real_provider.py",
    "--k", $K,
    "--min-score", $MinScore,
    "--max-error-rate", $MaxErrorRate
)

if ($EmbeddingProvider) { $runnerArgs += @("--embedding-provider", $EmbeddingProvider) }
if ($EmbeddingBaseUrl) { $runnerArgs += @("--embedding-base-url", $EmbeddingBaseUrl) }
if ($EmbeddingModel) { $runnerArgs += @("--embedding-model", $EmbeddingModel) }
if ($EmbeddingDimension -gt 0) { $runnerArgs += @("--embedding-dimension", $EmbeddingDimension) }
if ($PSBoundParameters.ContainsKey("MinRecallAtK")) { $runnerArgs += @("--min-recall-at-k", $MinRecallAtK) }
if ($PSBoundParameters.ContainsKey("MinPrecisionAtK")) { $runnerArgs += @("--min-precision-at-k", $MinPrecisionAtK) }
if ($PSBoundParameters.ContainsKey("MinMrr")) { $runnerArgs += @("--min-mrr", $MinMrr) }
if ($PSBoundParameters.ContainsKey("MinCitationCorrectness")) { $runnerArgs += @("--min-citation-correctness", $MinCitationCorrectness) }

Invoke-Gate "[1/4] Retrieval evaluation configuration unit tests" {
    uv run pytest -q tests/unit/test_retrieval_evaluation_config.py tests/unit/test_retrieval_evaluation.py
}

Invoke-Gate "[2/4] API runtime contract" {
    uv run pytest -q tests/api_contract/test_api_runtime_endpoints.py
}

Invoke-Gate "[3/4] Configured real provider evaluation" {
    uv run python @runnerArgs
}

Invoke-Gate "[4/4] Backend release regression gate" {
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
}

Write-Host "============================================================"
Write-Host "[PASS] Retrieval evaluation configuration gate completed."
Write-Host "============================================================"
