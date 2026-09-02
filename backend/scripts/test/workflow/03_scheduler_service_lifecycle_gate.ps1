$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Scheduler Service Lifecycle Gate"
Write-Host "============================================================"
Write-Host "[0/3] Local precondition checks"
Write-Host "Service policy: this Gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: lifecycle tests use mocks and require no manual IDs, credentials, or business data."
Write-Host "Warning policy: pytest warnings are treated as test errors."

$protectedPatterns = @(
    "uv.*run.*python.*run\.py",
    "uv.*run.*python.*run_scheduler\.py",
    "uvicorn.*app\.main:app",
    "postgres",
    "redis-server"
)

function Get-ProtectedProcessSnapshot {
    $processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
    return @(
        $processes | Where-Object {
            $commandLine = $_.CommandLine
            if ([string]::IsNullOrWhiteSpace($commandLine)) { return $false }
            foreach ($pattern in $protectedPatterns) {
                if ($commandLine -match $pattern) { return $true }
            }
            return $false
        } | Select-Object ProcessId, Name, CommandLine
    )
}

$before = Get-ProtectedProcessSnapshot
Write-Host "[1/3] Scheduler Service lifecycle unit tests"
uv run pytest -q -W error tests/unit/test_service_entrypoints.py
if ($LASTEXITCODE -ne 0) {
    throw "Scheduler Service lifecycle unit tests failed."
}

Write-Host "[2/3] Cancellation propagation and unified cleanup regression"
uv run pytest -q -W error tests/unit/test_service_entrypoints.py -k "scheduler_service"
if ($LASTEXITCODE -ne 0) {
    throw "Scheduler Service focused regression failed."
}

Write-Host "[3/3] Service boundary verification"
$after = Get-ProtectedProcessSnapshot
$unexpected = @($after | Where-Object {
    $beforeIds = @($before | ForEach-Object { $_.ProcessId })
    $beforeIds -notcontains $_.ProcessId
})
if ($unexpected.Count -gt 0) {
    $details = $unexpected | ForEach-Object { "PID=$($_.ProcessId) Name=$($_.Name) CommandLine=$($_.CommandLine)" }
    throw "Gate detected a protected service process created during the test:`n$($details -join "`n")"
}

Write-Host "[PASS] Scheduler dispatch, recovery, alert, and notification lifecycle tests passed."
Write-Host "[PASS] Scheduler cancellation propagates and unified stop/telemetry cleanup is verified."
Write-Host "[PASS] This Gate did not create or start any protected service."
Write-Host "[PASS] Scheduler Service Lifecycle Gate completed."
