param(
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$runtimeDir = Join-Path $projectRoot ".runtime"

function Get-PidFilePath {
  param(
    [string]$BaseName,
    [int]$Port,
    [int]$DefaultPort
  )

  if ($Port -eq $DefaultPort) {
    return (Join-Path $runtimeDir "${BaseName}.pid")
  }
  return (Join-Path $runtimeDir "${BaseName}-${Port}.pid")
}

$backendPidFile = Get-PidFilePath -BaseName "backend" -Port $BackendPort -DefaultPort 8000
$frontendPidFile = Get-PidFilePath -BaseName "frontend" -Port $FrontendPort -DefaultPort 5173

function Test-Http {
  param([string]$Url)
  try {
    $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
    return "HTTP $($r.StatusCode)"
  }
  catch {
    return "DOWN ($($_.Exception.Message))"
  }
}

function Test-ProcessRunning {
  param([int]$ProcessId)

  try {
    Get-Process -Id $ProcessId -ErrorAction Stop | Out-Null
    return $true
  }
  catch {
    return $false
  }
}

function Get-ListeningProcessIds {
  param([int]$Port)

  try {
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
  }
  catch {
    return @()
  }

  return @(
    $connections |
      Select-Object -ExpandProperty OwningProcess -Unique |
      Where-Object { $_ -and $_ -gt 0 }
  )
}

function Service-Status {
  param(
    [string]$ServiceName,
    [string]$PidFile,
    [int]$Port
  )

  $portProcessIds = Get-ListeningProcessIds -Port $Port
  $trackedPid = $null

  if (-not (Test-Path $PidFile)) {
    if ($portProcessIds) {
      return "${ServiceName}: running via porta $Port (PID(s) $($portProcessIds -join ', '); pid file ausente)"
    }
    return "${ServiceName}: parado (pid file ausente, porta $Port livre)"
  }

  $raw = (Get-Content $PidFile -Raw).Trim()
  if (-not $raw) {
    if ($portProcessIds) {
      Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
      return "${ServiceName}: running via porta $Port (PID(s) $($portProcessIds -join ', '); pid file vazio removido)"
    }
    return "${ServiceName}: pid file vazio"
  }

  $trackedPid = [int]$raw
  if (-not (Test-ProcessRunning -ProcessId $trackedPid)) {
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    if ($portProcessIds) {
      return "${ServiceName}: running via porta $Port (PID(s) $($portProcessIds -join ', '); pid stale removido $trackedPid)"
    }
    return "${ServiceName}: parado (pid stale removido $trackedPid)"
  }

  $proc = Get-Process -Id $trackedPid -ErrorAction SilentlyContinue
  $procName = if ($proc) { $proc.ProcessName } else { "desconhecido" }

  if ($portProcessIds -contains $trackedPid) {
    return "${ServiceName}: running (PID $trackedPid, Name $procName, ouvindo porta $Port)"
  }

  if ($portProcessIds) {
    return "${ServiceName}: running (PID rastreado $trackedPid, Name $procName; porta $Port em PID(s) $($portProcessIds -join ', '))"
  }

  return "${ServiceName}: running (PID $trackedPid, Name $procName; porta $Port ainda nao esta ouvindo)"
}

$backendUrl = "http://127.0.0.1:$BackendPort/health"
$frontendUrl = "http://127.0.0.1:$FrontendPort/"

Write-Host (Service-Status -ServiceName "Backend" -PidFile $backendPidFile -Port $BackendPort)
Write-Host (Service-Status -ServiceName "Frontend" -PidFile $frontendPidFile -Port $FrontendPort)
Write-Host "Backend URL:  $backendUrl -> $(Test-Http -Url $backendUrl)"
Write-Host "Frontend URL: $frontendUrl -> $(Test-Http -Url $frontendUrl)"
