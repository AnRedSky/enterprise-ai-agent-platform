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
    $requestParams = @{ Uri = ('{0}{1}' -f $BaseUrl, $Path); Method = $Method; Headers = $Headers; DisableKeepAlive = $true; ErrorAction = 'Stop' }
    if ($null -ne $Body) {
        $requestParams.ContentType = 'application/json'
        $requestParams.Body = ($Body | ConvertTo-Json -Depth 10 -Compress)
    }
    try {
        $response = Invoke-WebRequest @requestParams
        $status = [int]$response.StatusCode
        if ($ExpectedStatus -notcontains $status) { throw ('Unexpected HTTP status {0}' -f $status) }
        Write-Host ('[ OK  ] {0} -> HTTP {1}' -f $Name, $status) -ForegroundColor Green
        if ([string]::IsNullOrWhiteSpace([string]$response.Content)) { return $null }
        try { return ($response.Content | ConvertFrom-Json) } catch { return $response.Content }
    } catch {
        $status = $null
        if ($_.Exception.Response) { try { $status = [int]$_.Exception.Response.StatusCode.value__ } catch {} }
        Write-Host ('[FAIL ] {0} -> HTTP {1}' -f $Name, $status) -ForegroundColor Red
        throw
    }
}

Write-Host '============================================================' -ForegroundColor DarkGray
Write-Host 'Enterprise AI Agent Platform - Knowledge Retrieval Scenario' -ForegroundColor White
Write-Host ('Base URL: {0}' -f $BaseUrl) -ForegroundColor Gray
Write-Host 'Scenario: Auth -> Version -> Ingest -> Retrieve -> RBAC filter' -ForegroundColor Gray
Write-Host '============================================================' -ForegroundColor DarkGray

if ([string]::IsNullOrWhiteSpace($Username)) { $Username = 'retrieval_{0}' -f (Get-Date -Format 'yyyyMMddHHmmssfff') }
Invoke-ScenarioRequest -Name 'Auth / register' -Method 'POST' -Path '/api/v1/auth/register' -Body @{ username = $Username; password = $Password } -ExpectedStatus @(200, 409) | Out-Null
$login = Invoke-ScenarioRequest -Name 'Auth / login' -Method 'POST' -Path '/api/v1/auth/login' -Body @{ username = $Username; password = $Password }
$headers = @{ Authorization = 'Bearer {0}' -f $login.access_token }

$kb = Invoke-ScenarioRequest -Name 'Knowledge / create' -Method 'POST' -Path '/api/v1/knowledge' -Headers $headers -Body @{ name = ('retrieval-{0}' -f $Username); description = 'Retrieval scenario' }
$kbId = [string]$kb.id
$doc = Invoke-ScenarioRequest -Name 'Knowledge / document create' -Method 'POST' -Path ('/api/v1/knowledge/{0}/documents' -f $kbId) -Headers $headers -Body @{ title = 'Retrieval Scenario Document'; source_type = 'manual' }
$docId = [string]$doc.id
$content = 'FastAPI Agent Runtime uses Knowledge Retrieval. PostgreSQL stores Knowledge documents and chunks. Retrieval results must include source document, source chunk, relevance score and citation.'
$version = Invoke-ScenarioRequest -Name 'Knowledge / version create' -Method 'POST' -Path ('/api/v1/knowledge/{0}/documents/{1}/versions' -f $kbId, $docId) -Headers $headers -Body @{ version = 'v1'; status = 'draft'; content_text = $content }
$versionId = [string]$version.id
Invoke-ScenarioRequest -Name 'Knowledge / ingest' -Method 'POST' -Path ('/api/v1/knowledge/versions/{0}/ingest' -f $versionId) -Headers $headers -Body @{ max_chars = 100; overlap_chars = 10 } | Out-Null

$retrieval = Invoke-ScenarioRequest -Name 'Knowledge / retrieve' -Method 'POST' -Path '/api/v1/knowledge/retrieve' -Headers $headers -Body @{ query = 'Knowledge Retrieval'; top_k = 3; knowledge_base_id = $kbId }
$results = @($retrieval.results)
if ($results.Count -lt 1) { throw 'Retrieval returned no matching result.' }
$first = $results[0]
if ([string]::IsNullOrWhiteSpace([string]$first.document_id)) { throw 'Retrieval result missing document_id.' }
if ([string]::IsNullOrWhiteSpace([string]$first.chunk_id)) { throw 'Retrieval result missing chunk_id.' }
if ([string]::IsNullOrWhiteSpace([string]$first.source_document)) { throw 'Retrieval result missing source_document.' }
if ([string]::IsNullOrWhiteSpace([string]$first.citation)) { throw 'Retrieval result missing citation.' }
if ([double]$first.relevance_score -le 0) { throw 'Retrieval result relevance_score must be greater than zero.' }

$other = Invoke-ScenarioRequest -Name 'Knowledge / retrieve with non-owned KB filter' -Method 'POST' -Path '/api/v1/knowledge/retrieve' -Headers $headers -Body @{ query = 'Knowledge'; top_k = 3; knowledge_base_id = '00000000-0000-0000-0000-000000000000' }
if (@($other.results).Count -ne 0) { throw 'Owner isolation failed for a non-owned knowledge base.' }

Write-Host '============================================================' -ForegroundColor DarkGray
Write-Host '[PASS] Knowledge Retrieval scenario completed' -ForegroundColor Green
Write-Host ('Test user: {0}' -f $Username) -ForegroundColor Gray
Write-Host ('Results : {0}' -f $results.Count) -ForegroundColor Gray
Write-Host '============================================================' -ForegroundColor DarkGray
