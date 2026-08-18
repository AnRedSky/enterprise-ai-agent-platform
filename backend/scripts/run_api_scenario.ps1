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
        $errorBody = $null
        if ($_.Exception.Response) {
            try { $status = [int]$_.Exception.Response.StatusCode.value__ } catch {}
            try {
                if ($_.Exception.Response.Content) {
                    $errorBody = $_.Exception.Response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
                }
            } catch {}
        }
        if ($null -ne $status -and ($ExpectedStatus -contains $status)) {
            Write-Host "[ OK  ] $Name -> HTTP $status" -ForegroundColor Green
            return $null
        }
        Write-Host "[FAIL ] $Name" -ForegroundColor Red
        if ($null -ne $status) { Write-Host "       HTTP status: $status" -ForegroundColor Yellow }
        if (-not [string]::IsNullOrWhiteSpace($errorBody)) { Write-Host "       Response: $errorBody" -ForegroundColor Yellow }
        Write-Host "       Request: $Method $BaseUrl$Path" -ForegroundColor DarkGray
        throw
    }
}

Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "Enterprise AI Agent Platform - API Scenario Smoke Test" -ForegroundColor White
Write-Host "Base URL: $BaseUrl" -ForegroundColor Gray
Write-Host "Scenario: Health -> Auth -> Agents -> Publish -> Chat -> Runtime -> Tools" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor DarkGray

$health = Invoke-ScenarioRequest -Name "Health" -Path "/health"
if ($health.status -ne "ok") { throw "Health check returned an unexpected status." }

if ([string]::IsNullOrWhiteSpace($Username)) { $Username = "scenario_$(Get-Date -Format 'yyyyMMddHHmmssfff')" }
Invoke-ScenarioRequest -Name "Auth / register" -Method "POST" -Path "/api/v1/auth/register" -Body @{ username = $Username; password = $Password } -ExpectedStatus @(200, 409) | Out-Null
$login = Invoke-ScenarioRequest -Name "Auth / login" -Method "POST" -Path "/api/v1/auth/login" -Body @{ username = $Username; password = $Password }
if ([string]::IsNullOrWhiteSpace($login.access_token)) { throw "Login succeeded but no access_token was returned." }
$headers = @{ Authorization = "Bearer $($login.access_token)" }

$agentName = "scenario-agent-$(Get-Date -Format 'yyyyMMddHHmmssfff')"
$agent = Invoke-ScenarioRequest -Name "Agents / create" -Method "POST" -Path "/api/v1/agents" -Headers $headers -Body @{ name = $agentName; description = "One-click API scenario agent"; system_prompt = "You are a test assistant."; model_id = "mock-model" }
if ([string]::IsNullOrWhiteSpace([string]$agent.id)) { throw "Agent creation did not return an id." }
$agentId = [string]$agent.id
Invoke-ScenarioRequest -Name "Agents / list" -Path "/api/v1/agents" -Headers $headers | Out-Null
$versions = Invoke-ScenarioRequest -Name "Agents / versions" -Path "/api/v1/agents/$agentId/versions" -Headers $headers
if ($null -eq $versions -or $versions.Count -lt 1) { throw "Agent version list did not contain a version." }
$versionId = [string]$versions[0].id
if ([string]::IsNullOrWhiteSpace($versionId)) { throw "Agent version did not return an id." }
$published = Invoke-ScenarioRequest -Name "Agents / publish" -Method "POST" -Path "/api/v1/agents/$agentId/publish" -Headers $headers -Body @{ version_id = $versionId }
if ($published.status -ne "published") { throw "Agent publish did not return published status." }

$chat = Invoke-ScenarioRequest -Name "Chat / stream" -Method "POST" -Path "/api/v1/agents/stream" -Headers $headers -Body @{ agent_id = $agentId; input = "请回复：scenario-ok" }
$chatText = if ($chat -is [string]) { $chat } else { $chat | Out-String }
if ($chatText -notmatch '\"type\"\s*:\s*\"start\"') { throw "Chat stream did not contain a start event." }
if ($chatText -notmatch '\"type\"\s*:\s*\"done\"') { throw "Chat stream did not contain a done event." }
Write-Host "[ OK  ] Chat / SSE contains start + done events" -ForegroundColor Green

$runtime = Invoke-ScenarioRequest -Name "Runtime / executions" -Path "/api/v1/runtime/executions" -Headers $headers
if ($null -eq $runtime.items) { throw "Runtime execution response did not contain an items field." }
if ([int]$runtime.total -gt 0 -and $runtime.items.Count -gt 0) {
    $executionId = [string]$runtime.items[0].execution_id
    if (-not [string]::IsNullOrWhiteSpace($executionId)) {
        Invoke-ScenarioRequest -Name "Runtime / execution detail" -Path "/api/v1/runtime/executions/$executionId" -Headers $headers | Out-Null
        Invoke-ScenarioRequest -Name "Runtime / execution events" -Path "/api/v1/runtime/executions/$executionId/events" -Headers $headers | Out-Null
    }
}
Invoke-ScenarioRequest -Name "Runtime / audit logs" -Path "/api/v1/runtime/audit-logs" -Headers $headers | Out-Null

# Tools: cover the full management lifecycle from the normal user's RBAC boundary.
Invoke-ScenarioRequest -Name "Tools / list" -Path "/api/v1/tools" -Headers $headers | Out-Null
$missingToolId = "00000000-0000-0000-0000-000000000001"
Invoke-ScenarioRequest -Name "Tools / create forbidden for normal user" -Method "POST" -Path "/api/v1/tools" -Headers $headers -Body @{ name = "scenario-tool"; description = "Scenario tool"; enabled = $true; input_schema = @{ type = "object" } } -ExpectedStatus @(401, 403) | Out-Null
Invoke-ScenarioRequest -Name "Tools / bind forbidden for normal user" -Method "POST" -Path "/api/v1/tools/$missingToolId/bind/$agentId" -Headers $headers -ExpectedStatus @(401, 403, 404) | Out-Null
Invoke-ScenarioRequest -Name "Tools / unbind forbidden for normal user" -Method "DELETE" -Path "/api/v1/tools/$missingToolId/bind/$agentId" -Headers $headers -ExpectedStatus @(401, 403, 404) | Out-Null
Invoke-ScenarioRequest -Name "Tools / enable forbidden for normal user" -Method "POST" -Path "/api/v1/tools/$missingToolId/enable" -Headers $headers -ExpectedStatus @(401, 403, 404) | Out-Null
Invoke-ScenarioRequest -Name "Tools / disable forbidden for normal user" -Method "POST" -Path "/api/v1/tools/$missingToolId/disable" -Headers $headers -ExpectedStatus @(401, 403, 404) | Out-Null
Invoke-ScenarioRequest -Name "Tools / execute missing tool" -Method "POST" -Path "/api/v1/tools/$missingToolId/execute" -Headers $headers -Body @{ agent_id = $agentId; arguments = @{} } -ExpectedStatus @(404, 403) | Out-Null

Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "[PASS] API scenario completed: Health -> Auth -> Agents -> Publish -> Chat -> Runtime -> Tools" -ForegroundColor Green
Write-Host "Test user : $Username" -ForegroundColor Gray
Write-Host "Agent ID  : $agentId" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor DarkGray
