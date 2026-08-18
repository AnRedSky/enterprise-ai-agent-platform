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
    $params = @{ Uri = "$BaseUrl$Path"; Method = $Method; Headers = $Headers; DisableKeepAlive = $true; ErrorAction = "Stop" }
    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Depth 10 -Compress)
    }
    try {
        $response = Invoke-WebRequest @params
        $status = [int]$response.StatusCode
        if ($ExpectedStatus -notcontains $status) { throw "Unexpected HTTP status $status. Expected: $($ExpectedStatus -join ', ')" }
        Write-Host "[ OK  ] $Name -> HTTP $status" -ForegroundColor Green
        if ($response.Content) { try { return ($response.Content | ConvertFrom-Json) } catch { return $response.Content } }
        return $null
    } catch {
        $status = $null
        if ($_.Exception.Response) { try { $status = [int]$_.Exception.Response.StatusCode.value__ } catch {} }
        if ($null -ne $status -and ($ExpectedStatus -contains $status)) {
            Write-Host "[ OK  ] $Name -> HTTP $status" -ForegroundColor Green
            return $null
        }
        Write-Host "[FAIL ] $Name -> HTTP $status" -ForegroundColor Red
        throw
    }
}

Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "Enterprise AI Agent Platform - Knowledge Registry Scenario" -ForegroundColor White
Write-Host "Base URL: $BaseUrl" -ForegroundColor Gray
Write-Host "Scenario: Auth -> Knowledge Base -> Document -> Version -> Pagination -> RBAC" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor DarkGray

if ([string]::IsNullOrWhiteSpace($Username)) { $Username = "knowledge_$(Get-Date -Format 'yyyyMMddHHmmssfff')" }
Invoke-ScenarioRequest -Name "Auth / register" -Method "POST" -Path "/api/v1/auth/register" -Body @{ username = $Username; password = $Password } -ExpectedStatus @(200, 409) | Out-Null
$login = Invoke-ScenarioRequest -Name "Auth / login" -Method "POST" -Path "/api/v1/auth/login" -Body @{ username = $Username; password = $Password }
if ([string]::IsNullOrWhiteSpace($login.access_token)) { throw "Login did not return access_token." }
$headers = @{ Authorization = "Bearer $($login.access_token)" }

Invoke-ScenarioRequest -Name "Knowledge / list empty or existing" -Path "/api/v1/knowledge" -Headers $headers | Out-Null
$kbName = "scenario-knowledge-$(Get-Date -Format 'yyyyMMddHHmmssfff')"
$kb = Invoke-ScenarioRequest -Name "Knowledge / create" -Method "POST" -Path "/api/v1/knowledge" -Headers $headers -Body @{ name = $kbName; description = "Knowledge Registry manual scenario" }
if ([string]::IsNullOrWhiteSpace([string]$kb.id)) { throw "Knowledge Base creation did not return id." }
$kbId = [string]$kb.id

$detail = Invoke-ScenarioRequest -Name "Knowledge / detail" -Path "/api/v1/knowledge/$kbId" -Headers $headers
if ($detail.name -ne $kbName) { throw "Knowledge Base detail returned an unexpected name." }
Invoke-ScenarioRequest -Name "Knowledge / update" -Method "PATCH" -Path "/api/v1/knowledge/$kbId" -Headers $headers -Body @{ description = "Updated by manual scenario" } | Out-Null

Invoke-ScenarioRequest -Name "Knowledge / documents empty" -Path "/api/v1/knowledge/$kbId/documents" -Headers $headers | Out-Null
$document = Invoke-ScenarioRequest -Name "Knowledge / document create" -Method "POST" -Path "/api/v1/knowledge/$kbId/documents" -Headers $headers -Body @{ title = "Scenario Document"; source_type = "manual" }
if ([string]::IsNullOrWhiteSpace([string]$document.id)) { throw "Document creation did not return id." }
$documentId = [string]$document.id

Invoke-ScenarioRequest -Name "Knowledge / document detail" -Path "/api/v1/knowledge/$kbId/documents/$documentId" -Headers $headers | Out-Null
Invoke-ScenarioRequest -Name "Knowledge / document update" -Method "PATCH" -Path "/api/v1/knowledge/$kbId/documents/$documentId" -Headers $headers -Body @{ title = "Scenario Document Updated" } | Out-Null

$version = Invoke-ScenarioRequest -Name "Knowledge / version create" -Method "POST" -Path "/api/v1/knowledge/$kbId/documents/$documentId/versions" -Headers $headers -Body @{ version = "v1"; status = "ready"; content_hash = "scenario-hash"; content_text = "Scenario content" }
if ([string]::IsNullOrWhiteSpace([string]$version.id)) { throw "Version creation did not return id." }
if ($version.status -ne "ready") { throw "Version status is not ready." }

$versions = Invoke-ScenarioRequest -Name "Knowledge / versions" -Path "/api/v1/knowledge/$kbId/documents/$documentId/versions" -Headers $headers
if ($versions.Count -lt 1) { throw "Version list is empty after creation." }
$documents = Invoke-ScenarioRequest -Name "Knowledge / documents pagination" -Path "/api/v1/knowledge/$kbId/documents?page=1&page_size=10" -Headers $headers
if ($null -eq $documents.items -or [int]$documents.total -lt 1) { throw "Document pagination did not return the created document." }

Invoke-ScenarioRequest -Name "Knowledge / delete document" -Method "DELETE" -Path "/api/v1/knowledge/$kbId/documents/$documentId" -Headers $headers -ExpectedStatus @(204) | Out-Null
Invoke-ScenarioRequest -Name "Knowledge / delete knowledge base" -Method "DELETE" -Path "/api/v1/knowledge/$kbId" -Headers $headers -ExpectedStatus @(204) | Out-Null
Invoke-ScenarioRequest -Name "Knowledge / deleted detail" -Path "/api/v1/knowledge/$kbId" -Headers $headers -ExpectedStatus @(404) | Out-Null

Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "[PASS] Knowledge Registry scenario completed" -ForegroundColor Green
Write-Host "Test user: $Username" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor DarkGray
