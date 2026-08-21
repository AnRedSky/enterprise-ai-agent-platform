$ErrorActionPreference = "Stop"

$baseUrl = ($env:API_BASE_URL ?? "http://127.0.0.1:8000/api/v1").TrimEnd("/")
$timeoutSec = 20

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Frontend Trigger Real HTTP Contract"
Write-Host "Scope: frontend Trigger page request contract against real Backend HTTP"
Write-Host "Backend pytest, migration and frontend Vitest are intentionally NOT executed here."
Write-Host "============================================================"

function Invoke-JsonApi {
    param(
        [Parameter(Mandatory=$true)][string]$Method,
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][hashtable]$Headers,
        [object]$Body = $null,
        [int[]]$ExpectedStatus = @(200)
    )

    $uri = "$baseUrl$Path"
    $json = if ($null -ne $Body) { $Body | ConvertTo-Json -Depth 20 -Compress } else { $null }
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Method $Method -Uri $uri -Headers $Headers -ContentType "application/json" -Body $json -TimeoutSec $timeoutSec
        $status = [int]$response.StatusCode
        $text = [string]$response.Content
    } catch {
        $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode.value__ } else { 0 }
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $text = $reader.ReadToEnd()
            $reader.Dispose()
        } else {
            $text = $_.Exception.Message
        }
    }

    if ($ExpectedStatus -notcontains $status) {
        throw "$Method $Path -> expected HTTP $($ExpectedStatus -join ', '), got $status: $text"
    }

    if ([string]::IsNullOrWhiteSpace($text)) { return $null }
    return ($text | ConvertFrom-Json)
}

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "Assertion failed: $Message" }
}

$nonce = [guid]::NewGuid().ToString("N").Substring(0, 12)
$username = if ($env:API_TEST_USERNAME) { $env:API_TEST_USERNAME } else { "frontend_trigger_real_$nonce" }
$password = if ($env:API_TEST_PASSWORD) { $env:API_TEST_PASSWORD } else { "FrontendReal!$nonce" }

Write-Host "[1/8] Register/login isolated frontend integration user"
if (-not $env:API_TEST_USERNAME) {
    Invoke-JsonApi -Method POST -Path "/auth/register" -Headers @{} -Body @{ username=$username; password=$password } | Out-Null
}
$login = Invoke-JsonApi -Method POST -Path "/auth/login" -Headers @{} -Body @{ username=$username; password=$password }
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$login.access_token)) "login must return access_token"
$headers = @{ Authorization = "Bearer $($login.access_token)" }

Write-Host "[2/8] Create a published workflow fixture"
$workflow = Invoke-JsonApi -Method POST -Path "/workflows" -Headers $headers -Body @{ name="Frontend Trigger HTTP $nonce"; description="Frontend real HTTP Trigger contract fixture" }
$definition = @{ nodes=@(
    @{ id="input"; type="input"; config=@{} },
    @{ id="output"; type="output"; config=@{} }
); edges=@() }
$version = Invoke-JsonApi -Method POST -Path "/workflows/$($workflow.id)/versions" -Headers $headers -Body @{ definition=$definition }
Invoke-JsonApi -Method POST -Path "/workflows/$($workflow.id)/versions/$($version.id)/publish" -Headers $headers | Out-Null

Write-Host "[3/8] Create/list/detail Trigger exactly as the frontend page does"
$trigger = Invoke-JsonApi -Method POST -Path "/workflows/$($workflow.id)/triggers" -Headers $headers -Body @{ name="Frontend Manual Trigger $nonce"; trigger_type="manual"; config=@{ source="frontend-real-http" } }
$list = Invoke-JsonApi -Method GET -Path "/workflows/$($workflow.id)/triggers" -Headers $headers
$detail = Invoke-JsonApi -Method GET -Path "/workflows/$($workflow.id)/triggers/$($trigger.id)" -Headers $headers
Assert-True (@($list | Where-Object { $_.id -eq $trigger.id }).Count -eq 1) "created Trigger must appear in list"
Assert-True ($detail.workflow_id -eq $workflow.id) "Trigger detail must belong to selected workflow"
Assert-True ($detail.trigger_type -eq "manual") "Trigger type must be manual"
Assert-True ($detail.status -eq "enabled") "new Trigger must be enabled"

Write-Host "[4/8] Invoke Trigger with Idempotency-Key and verify completed execution"
$idempotencyKey = "frontend-trigger-$nonce"
$invokeBody = @{ input_data=@{ source="frontend-real-http" } }
$first = Invoke-JsonApi -Method POST -Path "/workflows/$($workflow.id)/triggers/$($trigger.id)/invoke" -Headers ($headers + @{ "Idempotency-Key"=$idempotencyKey }) -Body $invokeBody
Assert-True ($first.workflow_id -eq $workflow.id) "invoke response must contain workflow_id"
Assert-True ($first.status -eq "completed") "invoke response must be completed for executable fixture"

Write-Host "[5/8] Repeat the exact Trigger invocation and verify idempotency"
$second = Invoke-JsonApi -Method POST -Path "/workflows/$($workflow.id)/triggers/$($trigger.id)/invoke" -Headers ($headers + @{ "Idempotency-Key"=$idempotencyKey }) -Body @{ input_data=@{ source="frontend-real-http-repeated" } }
Assert-True ($second.id -eq $first.id) "same Idempotency-Key must return the same execution"

Write-Host "[6/8] Disable Trigger and verify UI action contract fast-fails"
$disabled = Invoke-JsonApi -Method PATCH -Path "/workflows/$($workflow.id)/triggers/$($trigger.id)" -Headers $headers -Body @{ status="disabled" }
Assert-True ($disabled.status -eq "disabled") "toggle action must persist disabled status"
$disabledInvoke = Invoke-JsonApi -Method POST -Path "/workflows/$($workflow.id)/triggers/$($trigger.id)/invoke" -Headers $headers -Body @{ input_data=@{ source="frontend-disabled-trigger" } } -ExpectedStatus @(409)
Assert-True ($disabledInvoke.detail -match "禁用|disabled") "disabled Trigger must reject invocation"

Write-Host "[7/8] Re-enable and delete Trigger through the same frontend API contract"
$enabled = Invoke-JsonApi -Method PATCH -Path "/workflows/$($workflow.id)/triggers/$($trigger.id)" -Headers $headers -Body @{ status="enabled" }
Assert-True ($enabled.status -eq "enabled") "toggle action must persist enabled status"
Invoke-JsonApi -Method DELETE -Path "/workflows/$($workflow.id)/triggers/$($trigger.id)" -Headers $headers | Out-Null
$afterDelete = Invoke-JsonApi -Method GET -Path "/workflows/$($workflow.id)/triggers" -Headers $headers
Assert-True (@($afterDelete | Where-Object { $_.id -eq $trigger.id }).Count -eq 0) "deleted Trigger must disappear from inventory"

Write-Host "[8/8] Frontend Trigger real HTTP contract passed"
Write-Host "============================================================"
Write-Host "[PASS] Frontend Trigger real HTTP integration completed."
Write-Host "Frontend Vitest and backend gates remain independent."
Write-Host "============================================================"
