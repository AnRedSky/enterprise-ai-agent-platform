[CmdletBinding()]
param(
    [string]$BaseUrl = $(if ($env:API_BASE_URL) { $env:API_BASE_URL } else { "http://127.0.0.1:8000" }),
    [string]$Username = "",
    [string]$Password = "TestPassword123!"
)

$ErrorActionPreference = "Stop"
$BaseUrl = $BaseUrl.TrimEnd('/')

function Invoke-ScenarioRequest {
    param(
        [string]$Name,
        [string]$Method = "GET",
        [string]$Path,
        [hashtable]$Headers = @{},
        [object]$Body = $null,
        [int[]]$ExpectedStatus = @(200)
    )

    Write-Host "[RUN ] $Name" -ForegroundColor Cyan
    $params = @{
        Uri = "$BaseUrl$Path"
        Method = $Method
        Headers = $Headers
        DisableKeepAlive = $true
        ErrorAction = "Stop"
    }
    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Depth 10 -Compress)
    }

    try {
        $response = Invoke-WebRequest @params
        $status = [int]$response.StatusCode
        if ($ExpectedStatus -notcontains $status) {
            throw "Unexpected HTTP status $status. Expected: $($ExpectedStatus -join ', ')"
        }
        Write-Host "[ OK  ] $Name -> HTTP $status" -ForegroundColor Green
        if ($response.Content) {
            try { return ($response.Content | ConvertFrom-Json) }
            catch { return $response.Content }
        }
        return $null
    }
    catch {
        $status = $null
        if ($_.Exception.Response) {
            try { $status = [int]$_.Exception.Response.StatusCode.value__ } catch {}
        }
        if ($null -ne $status -and ($ExpectedStatus -contains $status)) {
            Write-Host "[ OK  ] $Name -> HTTP $status" -ForegroundColor Green
            return $null
        }
        Write-Host "[FAIL ] $Name -> HTTP $status" -ForegroundColor Red
        throw
    }
}

Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "Enterprise AI Agent Platform - Knowledge Ingestion Scenario" -ForegroundColor White
Write-Host "Base URL: $BaseUrl" -ForegroundColor Gray
Write-Host "Scenario: Auth -> Version Content -> Ingest -> Chunks -> Idempotent Re-ingest" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor DarkGray

if ([string]::IsNullOrWhiteSpace($Username)) {
    $Username = "ingestion_$(Get-Date -Format 'yyyyMMddHHmmssfff')"
}

Invoke-ScenarioRequest `
    -Name "Auth / register" `
    -Method POST `
    -Path "/api/v1/auth/register" `
    -Body @{ username = $Username; password = $Password } `
    -ExpectedStatus @(200, 409) | Out-Null

$login = Invoke-ScenarioRequest `
    -Name "Auth / login" `
    -Method POST `
    -Path "/api/v1/auth/login" `
    -Body @{ username = $Username; password = $Password }

if ([string]::IsNullOrWhiteSpace($login.access_token)) {
    throw "Login did not return access_token."
}
$headers = @{ Authorization = "Bearer $($login.access_token)" }

$kb = Invoke-ScenarioRequest `
    -Name "Knowledge / create" `
    -Method POST `
    -Path "/api/v1/knowledge" `
    -Headers $headers `
    -Body @{ name = "ingestion-$Username"; description = "Document ingestion scenario" }
$kbId = [string]$kb.id

$doc = Invoke-ScenarioRequest `
    -Name "Knowledge / document create" `
    -Method POST `
    -Path "/api/v1/knowledge/$kbId/documents" `
    -Headers $headers `
    -Body @{ title = "Ingestion Scenario Document"; source_type = "manual" }
$docId = [string]$doc.id

$content = "第一段：企业 AI Agent 平台。`n`n第二段：Knowledge Registry、Document、Version 与 Chunk 构成知识处理基础。`n`n第三段：本场景验证清洗、确定性分块、持久化与重复摄取。"
$version = Invoke-ScenarioRequest `
    -Name "Knowledge / version create" `
    -Method POST `
    -Path "/api/v1/knowledge/$kbId/documents/$docId/versions" `
    -Headers $headers `
    -Body @{ version = "v1"; status = "draft"; content_text = $content }
$versionId = [string]$version.id

$ingest = Invoke-ScenarioRequest `
    -Name "Knowledge / ingest" `
    -Method POST `
    -Path "/api/v1/knowledge/versions/$versionId/ingest" `
    -Headers $headers `
    -Body @{ max_chars = 80; overlap_chars = 10 }

if ($ingest.ingestion_status -ne "ready") {
    throw "Ingestion did not reach ready status."
}
if ([int]$ingest.chunk_count -lt 2) {
    throw "Expected at least 2 chunks."
}

$chunks = Invoke-ScenarioRequest `
    -Name "Knowledge / chunks" `
    -Path "/api/v1/knowledge/versions/$versionId/chunks" `
    -Headers $headers
$chunkItems = @($chunks)

if ($chunkItems.Count -ne [int]$ingest.chunk_count) {
    throw "Chunk list count does not match ingestion result."
}
if ([string]$chunkItems[0].document_version_id -ne $versionId) {
    throw "Chunk is not linked to the expected document version."
}

$ingestAgain = Invoke-ScenarioRequest `
    -Name "Knowledge / re-ingest" `
    -Method POST `
    -Path "/api/v1/knowledge/versions/$versionId/ingest" `
    -Headers $headers `
    -Body @{ max_chars = 80; overlap_chars = 10 }

if ($ingestAgain.ingestion_status -ne "ready") {
    throw "Re-ingestion did not reach ready status."
}
if ([int]$ingestAgain.chunk_count -ne [int]$ingest.chunk_count) {
    throw "Re-ingestion changed the chunk count unexpectedly."
}

Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "[PASS] Knowledge Ingestion scenario completed" -ForegroundColor Green
Write-Host "Test user: $Username" -ForegroundColor Gray
Write-Host "Version : $versionId" -ForegroundColor Gray
Write-Host "Chunks  : $($ingestAgain.chunk_count)" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor DarkGray
