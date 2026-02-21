$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$runtimeDir = Join-Path $projectRoot ".runtime"
$backendPidFile = Join-Path $runtimeDir "backend.pid"
$frontendPidFile = Join-Path $runtimeDir "frontend.pid"

function Stop-FromPidFile {
  param(
    [string]$PidFile,
    [string]$ServiceName
  )

  if (-not (Test-Path $PidFile)) {
    Write-Host "${ServiceName}: sem pid file."
    return
  }

  $processIdRaw = (Get-Content $PidFile -Raw).Trim()
  if (-not $processIdRaw) {
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host "${ServiceName}: pid file vazio removido."
    return
  }

  $processId = [int]$processIdRaw
  try {
    Stop-Process -Id $processId -Force -ErrorAction Stop
    Write-Host "${ServiceName} encerrado (PID $processId)."
  }
  catch {
    Write-Host "${ServiceName}: PID $processId nao estava ativo."
  }
  finally {
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
  }
}

Stop-FromPidFile -PidFile $frontendPidFile -ServiceName "Frontend"
Stop-FromPidFile -PidFile $backendPidFile -ServiceName "Backend"

Write-Host "Finalizado."
