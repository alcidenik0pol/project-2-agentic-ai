# scripts/stop-dev.ps1
# Reliably kill THIS project's dev servers on Windows.
#
# Why a script (not inline bash):
#   - netstat's PID column can be stale on Windows; Get-NetTCPConnection is the source of truth.
#   - uvicorn --reload spawns a worker child whose parent reloader can die independently,
#     leaving orphan workers holding no port. We sweep them by conda-env marker.
#
# Scope: ONLY this project. Identified by:
#   - Dev ports 8901/3456 (whoever owns them).
#   - python.exe run from the agentic-ai-p2 conda env (project-specific).
#   - node.exe next-dev under this repo's frontend dir.
# Other projects' node/python (e.g. F:\_Dev\website) are never touched.

$ErrorActionPreference = 'SilentlyContinue'

$projectRoot = (Resolve-Path "$PSScriptRoot/..").Path
$devPorts    = 8901, 3456
# Conda env python binary path fragment — unique to this project's backend env.
$bePattern   = 'conda-envs[\\/]agentic-ai-p2[\\/]python\.exe'
# This project's frontend next binary path fragment.
$fePattern   = '_Columbia[\\/]Agentic AI[\\/]project 2[\\/]frontend[\\/]node_modules[\\/]next'

$toKill = [System.Collections.Generic.HashSet[int]]::new()

# 1. Port owners (reliable — NOT netstat).
foreach ($port in $devPorts) {
    Get-NetTCPConnection -LocalPort $port -State Listen |
        ForEach-Object { [void]$toKill.Add([int]$_.OwningProcess) }
}

# 2. Orphaned backend uvicorn workers (reloader parent may already be dead).
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -and $_.CommandLine -match $bePattern } |
        ForEach-Object { [void]$toKill.Add([int]$_.ProcessId) }

# 3. Orphaned frontend next-dev tied to THIS project only.
Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
    Where-Object { $_.CommandLine -and $_.CommandLine -match $fePattern } |
        ForEach-Object { [void]$toKill.Add([int]$_.ProcessId) }

# Drop empty / self / PID recycled to 0.
[void]$toKill.Remove(0)
[void]$toKill.Remove($PID)

if ($toKill.Count -eq 0) {
    Write-Output "[stop-dev] nothing to kill (no project dev processes found)."
    exit 0
}

Write-Output "[stop-dev] killing PIDs: $($toKill -join ', ')"
foreach ($procId in $toKill) {
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
}
Write-Output "[stop-dev] done. Killed $($toKill.Count) process(es)."
