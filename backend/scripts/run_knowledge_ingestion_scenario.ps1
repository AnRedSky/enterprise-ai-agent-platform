# PowerShell 5.1 / PowerShell 7 compatible manual acceptance scenario.
# Keep this script ASCII-only and parser-stable for Windows PowerShell 5.1.
[CmdletBinding()]
param(
    [string]$BaseUrl = $(if ($env:API_BASE_URL) { $env:API_BASE_URL } else { 'http://127.0.0.1:8000' }),
    [string]$Username = '',
    [string]$Password = 'TestPassword123!'
)

$ErrorActionPreference = 'Stop'
$BaseUrl = $BaseUrl.TrimEnd('/')

function Invoke-ScenarioRequest {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string]$Method = 'GET',
        [Parameter(Mandatory = $true)][string]$Path,
        [hashtable]$Headers = @{},
        [object]$Body = $null,
        [int[]]$ExpectedStatus = @(200)
    )

    Write-Host ('[RUN ] {0}' -f $Name) -ForegroundColor Cyan
    $requestParams = @{
        Uri = ('{0}{1}' -f $BaseUrl, $Path)
        Method = $Method
        Headers = $Headers
        DisableKeepAlive = $true
        ErrorAction = 'Stop'
    }

    if ($null -ne $Body) {
        $requestParams.ContentType = 'application/json'
        $requestParams.Body = ($Body | ConvertTo-Json -Depth 10 -Compress)
    }

    try {
        $response = Invoke-WebRequest @requestParams
        $status = [int]$response.StatusCode
        if ($ExpectedStatus -notcontains $status) {
            throw ('Unexpected HTTP status {0}. Expected: {1}' -f $status, ($ExpectedStatus -join ', '))
        }
        Write-Host ('[ OK  ] {0} -> HTTP {1}' -f $Name, $status) -ForegroundColor Green
        if ([string]::IsNullOrWhiteSpace([string]$response.Content)) { return $null }
        try { return ($response.Content | ConvertFrom-Json) } catch { return $response.Content }
    }
    catch {
        $status = $null
        if ($_.Exception.Response) {
            try { $status = [int]$_.Exception.Response.StatusCode.value__ } catch {}
        }
        if ($null -ne $status -and ($ExpectedStatus -contains $status)) {
            Write-Host ('[ OK  ] {0} -> HTTP {1}' -f $Name, $status) -ForegroundColor Green
            return $null
        }
        Write-Host ('[FAIL ] {0} -> HTTP {1}' -f $Name, $status) -ForegroundColor Red
        throw
    }
}

Write-Host '============================================================' -ForegroundColor DarkGray
Write-Host 'Enterprise AI Agent Platform - Knowledge Ingestion Scenario' -ForegroundColor White
Write-Host ('Base URL: {0}' -f $BaseUrl) -ForegroundColor Gray
Write-Host 'Scenario: Auth -> Version -> Ingest -> Chunks -> Re-ingest' -ForegroundColor Gray
Write-Host '============================================================' -ForegroundColor DarkGray

if ([string]::IsNullOrWhiteSpace($Username)) {
    $Username = 'ingestion_{0}' -f (Get-Date -Format 'yyyyMMddHHmmssfff')
}

$register = @{
    Name = 'Auth / register'
    Method = 'POST'
    Path = '/api/v1/auth/register'
    Body = @{ username = $Username; password = $Password }
    ExpectedStatus = @(200, 409)
}
Invoke-ScenarioRequest @register | Out-Null

$login = Invoke-ScenarioRequest -Name 'Auth / login' -Method 'POST' -Path '/api/v1/auth/login' -Body @{ username = $Username; password = $Password }
if ([string]::IsNullOrWhiteSpace($login.access_token)) { throw 'Login did not return access_token.' }
$headers = @{ Authorization = 'Bearer {0}' -f $login.access_token }

$kb = Invoke-ScenarioRequest -Name 'Knowledge / create' -Method 'POST' -Path '/api/v1/knowledge' -Headers $headers -Body @{ name = ('ingestion-{0}' -f $Username); description = 'Document ingestion scenario' }
$kbId = [string]$kb.id
if ([string]::IsNullOrWhiteSpace($kbId)) { throw 'Knowledge create did not return an id.' }

$docPath = '/api/v1/knowledge/{0}/documents' -f $kbId
$doc = Invoke-ScenarioRequest -Name 'Knowledge / document create' -Method 'POST' -Path $docPath -Headers $headers -Body @{ title = 'Ingestion Scenario Document'; source_type = 'manual' }
$docId = [string]$doc.id
if ([string]::IsNullOrWhiteSpace($docId)) { throw 'Document create did not return an id.' }

$content = 'Enterprise AI Agent Platform. Knowledge Registry, Document, Version and Chunk form the ingestion foundation. This scenario validates cleaning, deterministic chunking, persistence and repeated ingestion.'
$versionPath = '/api/v1/knowledge/{0}/documents/{1}/versions' -f $kbId, $docId
$versionBody = @{ version = 'v1'; status = 'draft'; content_text = $content }
$version = Invoke-ScenarioRequest -Name 'Knowledge / version create' -Method 'POST' -Path $versionPath -Headers $headers -Body $versionBody
$versionId = [string]$version.id
if ([string]::IsNullOrWhiteSpace($versionId)) { throw 'Version create did not return an id.' }

$ingestPath = '/api/v1/knowledge/versions/{0}/ingest' -f $versionId
$ingestBody = @{ max_chars = 80; overlap_chars = 10 }
$ingest = Invoke-ScenarioRequest -Name 'Knowledge / ingest' -Method 'POST' -Path $ingestPath -Headers $headers -Body $ingestBody
if ($ingest.ingestion_status -ne 'ready') { throw 'Ingestion did not reach ready status.' }
if ([int]$ingest.chunk_count -lt 2) { throw 'Expected at least 2 chunks.' }

$chunksPath = '/api/v1/knowledge/versions/{0}/chunks' -f $versionId
$chunks = Invoke-ScenarioRequest -Name 'Knowledge / chunks' -Path $chunksPath -Headers $headers
$chunkItems = @($chunks)
if ($chunkItems.Count -ne [int]$ingest.chunk_count) { throw 'Chunk list count does not match ingestion result.' }
if ([string]$chunkItems[0].document_version_id -ne $versionId) { throw 'Chunk is not linked to the expected document version.' }

$ingestAgain = Invoke-ScenarioRequest -Name 'Knowledge / re-ingest' -Method 'POST' -Path $ingestPath -Headers $headers -Body $ingestBody
if ($ingestAgain.ingestion_status -ne 'ready') { throw 'Re-ingestion did not reach ready status.' }
if ([int]$ingestAgain.chunk_count -ne [int]$ingest.chunk_count) { throw 'Re-ingestion changed the chunk count unexpectedly.' }

Write-Host '============================================================' -ForegroundColor DarkGray
Write-Host '[PASS] Knowledge Ingestion scenario completed' -ForegroundColor Green
Write-Host ('Test user: {0}' -f $Username) -ForegroundColor Gray
Write-Host ('Version : {0}' -f $versionId) -ForegroundColor Gray
Write-Host ('Chunks  : {0}' -f $ingestAgain.chunk_count) -ForegroundColor Gray
Write-Host '============================================================' -ForegroundColor DarkGray
