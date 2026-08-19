$ErrorActionPreference = 'Stop'
$BaseUrl = if ($env:API_BASE_URL) { $env:API_BASE_URL } else { 'http://127.0.0.1:8000' }
$suffix = Get-Date -Format 'yyyyMMddHHmmssfff'
$username = "runtime_knowledge_$suffix"
$password = 'RuntimeKnowledge123!'

Write-Host '============================================================' -ForegroundColor DarkGray
Write-Host 'Enterprise AI Agent Platform - Runtime Knowledge Scenario' -ForegroundColor Cyan
Write-Host "Base URL: $BaseUrl" -ForegroundColor Gray
Write-Host 'Scenario: Auth -> Knowledge -> Ingest -> AgentVersion Knowledge -> Runtime Chat -> Citation' -ForegroundColor Gray
Write-Host '============================================================' -ForegroundColor DarkGray

function Invoke-Json {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Path,
        [hashtable]$Headers = @{},
        [object]$Body = $null
    )
    Write-Host "[RUN ] $Name" -ForegroundColor Gray
    $params = @{ Uri = "$BaseUrl$Path"; Method = $Method; Headers = $Headers; ContentType = 'application/json' }
    if ($null -ne $Body) { $params.Body = ($Body | ConvertTo-Json -Depth 10) }
    try {
        $response = Invoke-RestMethod @params
        Write-Host "[ OK  ] $Name" -ForegroundColor Green
        return $response
    } catch {
        Write-Host "[FAIL ] $Name" -ForegroundColor Red
        throw
    }
}

$register = Invoke-Json -Name 'Auth / register' -Method 'POST' -Path '/api/v1/auth/register' -Body @{ username = $username; password = $password }
$login = Invoke-Json -Name 'Auth / login' -Method 'POST' -Path '/api/v1/auth/login' -Body @{ username = $username; password = $password }
$headers = @{ Authorization = "Bearer $($login.access_token)" }

$kb = Invoke-Json -Name 'Knowledge / create' -Method 'POST' -Path '/api/v1/knowledge' -Headers $headers -Body @{ name = "Runtime Knowledge $suffix"; description = 'Runtime integration acceptance' }
$kbId = [string]$kb.id
if ([string]::IsNullOrWhiteSpace($kbId)) { throw 'Knowledge base id missing.' }

$doc = Invoke-Json -Name 'Knowledge / document create' -Method 'POST' -Path "/api/v1/knowledge/$kbId/documents" -Headers $headers -Body @{ title = 'Runtime Policy'; source_type = 'manual'; source_uri = 'manual://runtime-policy' }
$docId = [string]$doc.id
if ([string]::IsNullOrWhiteSpace($docId)) { throw 'Document id missing.' }

$content = 'Runtime 知识策略：员工提交申请后需要直属主管审批。知识检索必须保留 citation。'
$version = Invoke-Json -Name 'Knowledge / version create' -Method 'POST' -Path "/api/v1/knowledge/$kbId/documents/$docId/versions" -Headers $headers -Body @{ version = 'v1'; status = 'ready'; content_text = $content }
$versionId = [string]$version.id
if ([string]::IsNullOrWhiteSpace($versionId)) { throw 'Version id missing.' }

$ingest = Invoke-Json -Name 'Knowledge / ingest' -Method 'POST' -Path "/api/v1/knowledge/versions/$versionId/ingest" -Headers $headers -Body @{ max_chars = 100; overlap_chars = 10 }
if ($ingest.ingestion_status -ne 'ready') { throw 'Knowledge ingestion did not reach ready.' }
if ([int]$ingest.chunk_count -lt 1) { throw 'Knowledge ingestion produced no chunks.' }

$agent = Invoke-Json -Name 'Agent / create with knowledge config' -Method 'POST' -Path '/api/v1/agents' -Headers $headers -Body @{
    name = "Runtime Knowledge Agent $suffix"
    description = 'Runtime knowledge integration acceptance'
    system_prompt = '你是企业知识助手。'
    model_id = 'mock-model'
    knowledge_config = @{ knowledge_base_ids = @($kbId); top_k = 3 }
}
$agentId = [string]$agent.id
if ([string]::IsNullOrWhiteSpace($agentId)) { throw 'Agent id missing.' }
if ([string]$agent.knowledge_config.knowledge_base_ids[0] -ne $kbId) { throw 'Agent knowledge config was not persisted.' }

$versions = Invoke-Json -Name 'Agent / versions' -Method 'GET' -Path "/api/v1/agents/$agentId/versions" -Headers $headers
$agentVersion = @($versions) | Select-Object -First 1
if ($null -eq $agentVersion -or [string]::IsNullOrWhiteSpace([string]$agentVersion.id)) { throw 'Agent version was not returned.' }
if ([int]$agentVersion.knowledge_config.top_k -ne 3) { throw 'Agent version knowledge config mismatch.' }

$publish = Invoke-Json -Name 'Agent / publish' -Method 'POST' -Path "/api/v1/agents/$agentId/publish" -Headers $headers -Body @{ version_id = [string]$agentVersion.id }
if ($publish.status -ne 'published') { throw 'Agent was not published.' }

Write-Host '[RUN ] Runtime / chat with knowledge context' -ForegroundColor Gray
$chatBody = @{ agent_id = $agentId; input = '员工提交申请后谁审批？' } | ConvertTo-Json -Depth 10
$chatResponse = Invoke-WebRequest -Uri "$BaseUrl/api/v1/agents/stream" -Method 'POST' -Headers $headers -ContentType 'application/json' -Body $chatBody
if ($chatResponse.StatusCode -ne 200) { throw "Runtime chat returned HTTP $($chatResponse.StatusCode)." }
$raw = [string]$chatResponse.Content
if ($raw -notmatch 'knowledge_count') { throw 'Runtime start event did not expose knowledge_count.' }
if ($raw -notmatch 'Runtime Policy#0') { throw 'Runtime response did not expose expected citation.' }
if ($raw -notmatch 'execution_id') { throw 'Runtime response did not expose execution_id.' }
if ($raw -notmatch 'trace_id') { throw 'Runtime response did not expose trace_id.' }
Write-Host '[ OK  ] Runtime / chat with knowledge context' -ForegroundColor Green

Write-Host '============================================================' -ForegroundColor DarkGray
Write-Host '[PASS] Runtime Knowledge scenario completed' -ForegroundColor Green
Write-Host "Knowledge : $kbId" -ForegroundColor Gray
Write-Host "Agent     : $agentId" -ForegroundColor Gray
Write-Host "Chunks    : $($ingest.chunk_count)" -ForegroundColor Gray
Write-Host '============================================================' -ForegroundColor DarkGray
