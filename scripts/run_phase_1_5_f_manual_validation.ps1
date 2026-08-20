[CmdletBinding()]
param(
    [string]$ApiBaseUrl = $(if ($env:API_BASE_URL) { $env:API_BASE_URL } else { "http://127.0.0.1:8000/api/v1" }),
    [string]$AccessToken = $env:ACCESS_TOKEN,
    [string]$AdminAccessToken = $env:ADMIN_ACCESS_TOKEN,
    [string]$ExecutionId = $env:WORKFLOW_EXECUTION_ID,
    [switch]$SkipCreate
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 1.5-F"
Write-Host "Workflow / Governance Frontend + Backend Manual Validation"
Write-Host "============================================================"
Write-Host "API: $ApiBaseUrl"

if (-not $AccessToken) {
    throw "ACCESS_TOKEN is required. Set it with: `$env:ACCESS_TOKEN='<token>'"
}

function Invoke-Api {
    param(
        [ValidateSet("GET", "POST", "PATCH")][string]$Method,
        [string]$Path,
        [object]$Body = $null,
        [string]$Token = $AccessToken
    )

    $headers = @{ Authorization = "Bearer $Token" }
    $params = @{
        Method = $Method
        Uri = "$ApiBaseUrl$Path"
        Headers = $headers
        ContentType = "application/json"
    }
    if ($null -ne $Body) {
        $params.Body = ($Body | ConvertTo-Json -Depth 20)
    }
    return Invoke-RestMethod @params
}

Write-Host "[1/8] Workflow Registry list"
$workflows = Invoke-Api -Method GET -Path "/workflows"
if ($null -eq $workflows) { throw "Workflow list returned null." }
Write-Host "      PASS: Workflow registry reachable."

$workflow = $null
$version = $null

if (-not $SkipCreate) {
    Write-Host "[2/8] Create Workflow"
    $suffix = Get-Date -Format "yyyyMMdd-HHmmss"
    $workflow = Invoke-Api -Method POST -Path "/workflows" -Body @{
        name = "phase-1-5-f-manual-$suffix"
        description = "Phase 1.5-F local manual integration validation"
    }
    if (-not $workflow.id) { throw "Create Workflow response does not contain id." }
    Write-Host "      PASS: workflow_id=$($workflow.id)"

    Write-Host "[3/8] Read Workflow Versions"
    $versions = Invoke-Api -Method GET -Path "/workflows/$($workflow.id)/versions"
    if ($null -eq $versions) { throw "Workflow versions returned null." }
    Write-Host "      PASS: Version endpoint reachable."

    Write-Host "[4/8] Create Definition Version"
    $version = Invoke-Api -Method POST -Path "/workflows/$($workflow.id)/versions" -Body @{
        definition = @{
            schema_version = "1.0"
            nodes = @(
                @{ id = "start"; type = "start"; config = @{} }
            )
            edges = @()
        }
    }
    if (-not $version.id) { throw "Create Version response does not contain id." }
    Write-Host "      PASS: version_id=$($version.id)"

    Write-Host "[5/8] Publish Version"
    $published = Invoke-Api -Method POST -Path "/workflows/$($workflow.id)/versions/$($version.id)/publish"
    if (-not $published.id) { throw "Publish response does not contain id." }
    Write-Host "      PASS: published_version_id=$($published.id)"
} else {
    Write-Host "[2-5/8] Create / Version / Publish skipped."
    Write-Host "      Use an existing workflow and version in the UI for manual validation."
}

$workflowIdForAudit = if ($workflow) { $workflow.id } else { $env:WORKFLOW_ID }
if (-not $workflowIdForAudit) {
    Write-Warning "WORKFLOW_ID is not set; Audit API check will be skipped."
} else {
    Write-Host "[6/8] Workflow Audit"
    $audit = Invoke-Api -Method GET -Path "/runtime/audit-logs?workflow_id=$workflowIdForAudit"
    if ($null -eq $audit) { throw "Audit response returned null." }
    Write-Host "      PASS: Audit endpoint reachable; total=$($audit.total)"
}

if ($ExecutionId) {
    Write-Host "[7/8] Execution Trace"
    $trace = Invoke-Api -Method GET -Path "/runtime/executions/$ExecutionId/trace"
    if ($null -eq $trace) { throw "Trace response returned null." }
    Write-Host "      PASS: Trace endpoint reachable; items=$(@($trace.items).Count)"
} else {
    Write-Host "[7/8] Execution Trace skipped"
    Write-Host "      Set WORKFLOW_EXECUTION_ID to a real execution ID and rerun this script."
}

Write-Host "[8/8] RBAC / Tenant Isolation Manual Checks"
Write-Host "      A. Login as normal user and open /workflows."
Write-Host "      B. Confirm only permitted tenant/owner workflows are visible."
Write-Host "      C. Attempt another tenant's workflow/version/audit/trace by ID; expect backend authorization rejection."
Write-Host "      D. Login as administrator and confirm governance query scope matches RBAC contract."
if ($AdminAccessToken) {
    Write-Host "      ADMIN_ACCESS_TOKEN is supplied; administrator API checks should be performed manually against the same IDs."
} else {
    Write-Host "      ADMIN_ACCESS_TOKEN not supplied; administrator checks remain manual-only."
}

Write-Host ""
Write-Host "============================================================"
Write-Host "API contract checks completed."
Write-Host "Now perform the Vue UI scenarios:"
Write-Host "1. Open /workflows"
Write-Host "2. Create / select Workflow"
Write-Host "3. Inspect Version list"
Write-Host "4. Create legal JSON Definition Version"
Write-Host "5. Publish Version and confirm status"
Write-Host "6. Query Audit"
Write-Host "7. Query Trace with a real Execution ID"
Write-Host "8. Verify normal-user tenant/owner isolation"
Write-Host "9. Verify administrator governance scope"
Write-Host "============================================================"
