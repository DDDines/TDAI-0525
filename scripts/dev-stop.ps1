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

function Stop-ProcessTree {
  param(
    [int]$ProcessId,
    [string]$ServiceName
  )

  if ($ProcessId -le 0) {
    return $false
  }

  try {
    taskkill /PID $ProcessId /T /F *> $null
    Write-Host "${ServiceName}: processo/tree encerrado (PID $ProcessId)."
    return $true
  }
  catch {
    try {
      Stop-Process -Id $ProcessId -Force -ErrorAction Stop
      Write-Host "${ServiceName}: processo encerrado (PID $ProcessId)."
      return $true
    }
    catch {
      Write-Host "${ServiceName}: PID $ProcessId nao estava ativo."
      return $false
    }
  }
}

function Stop-Service {
  param(
    [string]$ServiceName,
    [string]$PidFile,
    [int]$Port
  )

  $processIds = @()

  if (Test-Path $PidFile) {
    $processIdRaw = (Get-Content $PidFile -Raw).Trim()
    if (-not $processIdRaw) {
      Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
      Write-Host "${ServiceName}: pid file vazio removido."
    }
    else {
      $processIds += [int]$processIdRaw
    }
  }

  $processIds += Get-ListeningProcessIds -Port $Port
  $processIds = @($processIds | Select-Object -Unique)

  if (-not $processIds) {
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host "${ServiceName}: nada ativo encontrado (porta $Port livre)."
    return
  }

  foreach ($processId in $processIds) {
    Stop-ProcessTree -ProcessId $processId -ServiceName $ServiceName | Out-Null
  }

  Start-Sleep -Milliseconds 800
  $remaining = Get-ListeningProcessIds -Port $Port
  foreach ($processId in $remaining) {
    Stop-ProcessTree -ProcessId $processId -ServiceName $ServiceName | Out-Null
  }

  Remove-Item $PidFile -Force -ErrorAction SilentlyContinue

  if (Get-ListeningProcessIds -Port $Port) {
    Write-Host "${ServiceName}: porta $Port ainda ocupada apos tentativa de encerramento."
    return
  }

  Write-Host "${ServiceName}: porta $Port liberada."
}

Stop-Service -PidFile $frontendPidFile -ServiceName "Frontend" -Port $FrontendPort
Stop-Service -PidFile $backendPidFile -ServiceName "Backend" -Port $BackendPort

Write-Host "Finalizado."
