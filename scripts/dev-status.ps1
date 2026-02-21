$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$runtimeDir = Join-Path $projectRoot ".runtime"
$backendPidFile = Join-Path $runtimeDir "backend.pid"
$frontendPidFile = Join-Path $runtimeDir "frontend.pid"

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

function Service-StatusFromPidFile {
  param(
    [string]$ServiceName,
    [string]$PidFile
  )

  if (-not (Test-Path $PidFile)) {
    return "${ServiceName}: pid file ausente"
  }

  $raw = (Get-Content $PidFile -Raw).Trim()
  if (-not $raw) {
    return "${ServiceName}: pid file vazio"
  }

  $processId = [int]$raw
  try {
    $proc = Get-Process -Id $processId -ErrorAction Stop
    return "${ServiceName}: running (PID $($proc.Id), Name $($proc.ProcessName))"
  }
  catch {
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    return "${ServiceName}: pid stale removido (PID $processId)"
  }
}

$backendUrl = "http://127.0.0.1:8000/health"
$frontendUrl = "http://127.0.0.1:5173/"

Write-Host (Service-StatusFromPidFile -ServiceName "Backend" -PidFile $backendPidFile)
Write-Host (Service-StatusFromPidFile -ServiceName "Frontend" -PidFile $frontendPidFile)
Write-Host "Backend URL:  $backendUrl -> $(Test-Http -Url $backendUrl)"
Write-Host "Frontend URL: $frontendUrl -> $(Test-Http -Url $frontendUrl)"
