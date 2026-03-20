param(
  [string]$BackendHost = "127.0.0.1",
  [int]$BackendPort = 8000,
  [string]$FrontendHost = "127.0.0.1",
  [int]$FrontendPort = 5173,
  [int]$HealthTimeoutSec = 60,
  [switch]$WaitForHealth,
  [switch]$SkipBackend,
  [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$runtimeDir = Join-Path $projectRoot ".runtime"

New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

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

function Test-HttpOk {
  param([string]$Url)
  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
    return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
  }
  catch {
    return $false
  }
}

function Wait-Http {
  param(
    [string]$Url,
    [int]$Retries = 60,
    [int]$DelaySec = 1,
    [int]$ProcessId = 0
  )

  for ($i = 0; $i -lt $Retries; $i++) {
    if (Test-HttpOk -Url $Url) {
      return $true
    }
    if ($ProcessId -gt 0 -and -not (Test-ProcessRunning -ProcessId $ProcessId)) {
      return $false
    }
    Start-Sleep -Seconds $DelaySec
  }
  return $false
}

function Get-HealthRetries {
  $retries = [int][Math]::Ceiling($HealthTimeoutSec / 1.0)
  if ($retries -lt 1) { return 1 }
  return $retries
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

function Get-ProcessCommandLine {
  param([int]$ProcessId)

  try {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
    return [string]$process.CommandLine
  }
  catch {
    return ""
  }
}

function Test-BackendProcessOwnedByProject {
  param([int]$ProcessId)

  $commandLine = Get-ProcessCommandLine -ProcessId $ProcessId
  if (-not $commandLine) {
    return $false
  }

  return (
    $commandLine.Contains($projectRoot) -or
    $commandLine.Contains("run_backend.py")
  )
}

function Get-ProjectBackendProcessIds {
  param([int]$Port)

  return @(
    Get-ListeningProcessIds -Port $Port |
      Where-Object { Test-BackendProcessOwnedByProject -ProcessId $_ }
  )
}

function Sync-PidFileWithPort {
  param(
    [string]$PidFile,
    [int]$Port,
    [int]$FallbackProcessId = 0
  )

  $candidateIds = @()
  $candidateIds += Get-ListeningProcessIds -Port $Port
  if ($FallbackProcessId -gt 0) {
    $candidateIds += $FallbackProcessId
  }
  $candidateIds = @($candidateIds | Select-Object -Unique)

  foreach ($candidateId in $candidateIds) {
    if (-not (Test-ProcessRunning -ProcessId $candidateId)) {
      continue
    }
    Set-Content -Path $PidFile -Value $candidateId -Encoding ASCII
    return $candidateId
  }

  if ($FallbackProcessId -gt 0 -and (Test-ProcessRunning -ProcessId $FallbackProcessId)) {
    Set-Content -Path $PidFile -Value $FallbackProcessId -Encoding ASCII
    return $FallbackProcessId
  }

  return $null
}

function Resolve-BackendPython {
  $candidates = @()
  if ($env:BACKEND_PYTHON) {
    $candidates += $env:BACKEND_PYTHON
  }

  $candidates += Join-Path (Split-Path -Parent $projectRoot) ".venv\Scripts\python.exe"
  $candidates += Join-Path $projectRoot "venv\Scripts\python.exe"
  $candidates += Join-Path (Split-Path -Parent $projectRoot) "pythagora-core\venv\Scripts\python.exe"

  foreach ($candidate in $candidates) {
    if ($candidate -and (Test-Path $candidate)) {
      & $candidate -c "import uvicorn" 2>$null
      if ($LASTEXITCODE -eq 0) {
        return $candidate
      }
    }
  }

  $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
  if ($pythonCommand) {
    & $pythonCommand.Source -c "import uvicorn" 2>$null
    if ($LASTEXITCODE -eq 0) {
      return $pythonCommand.Source
    }
  }

  throw "Nenhum Python com uvicorn encontrado. Defina BACKEND_PYTHON apontando para um ambiente valido."
}

function Resolve-NodeExe {
  if ($env:NODE_EXE -and (Test-Path $env:NODE_EXE)) {
    return $env:NODE_EXE
  }

  $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
  if ($nodeCommand) {
    return $nodeCommand.Source
  }

  $defaultNode = "C:\Program Files\nodejs\node.exe"
  if (Test-Path $defaultNode) {
    return $defaultNode
  }

  throw "Node nao encontrado. Instale Node.js ou defina NODE_EXE."
}

function Start-Backend {
  $backendUrl = "http://${BackendHost}:$BackendPort/health"
  $backendOut = Join-Path $runtimeDir "backend.out.log"
  $backendErr = Join-Path $runtimeDir "backend.err.log"
  $listeningProcessIds = Get-ListeningProcessIds -Port $BackendPort
  $projectBackendProcessIds = Get-ProjectBackendProcessIds -Port $BackendPort

  if ($listeningProcessIds -and -not $projectBackendProcessIds) {
    $externalProcessSummary = @(
      $listeningProcessIds |
        ForEach-Object {
          $commandLine = Get-ProcessCommandLine -ProcessId $_
          if (-not $commandLine) {
            $commandLine = "<command line indisponivel>"
          }
          "PID $_ => $commandLine"
        }
    ) -join [Environment]::NewLine

    throw "A porta $BackendPort esta ocupada por um backend externo a este projeto. Pare esse processo antes de iniciar o ambiente correto.`n$externalProcessSummary"
  }

  if (Test-Path $backendPidFile) {
    $existingPid = [int](Get-Content $backendPidFile -Raw).Trim()
    if ((Test-ProcessRunning -ProcessId $existingPid) -or $projectBackendProcessIds) {
      $trackedPid = Sync-PidFileWithPort -PidFile $backendPidFile -Port $BackendPort -FallbackProcessId $existingPid
      if ($trackedPid) {
        Write-Host "Backend ja em execucao (PID rastreado $trackedPid)."
      }
      else {
        Write-Host "Backend ja em execucao."
      }
      return
    }
    Remove-Item $backendPidFile -Force
  }

  if (Test-HttpOk -Url $backendUrl) {
    $trackedPid = Sync-PidFileWithPort -PidFile $backendPidFile -Port $BackendPort
    if ($trackedPid) {
      Write-Host "Backend ja responde em $backendUrl (PID adotado $trackedPid)."
    }
    else {
      Write-Host "Backend ja responde em $backendUrl (processo externo ao script)."
    }
    return
  }

  $pythonExe = Resolve-BackendPython
  $backendArgs = @(
    ".\run_backend.py",
    "--host", $BackendHost,
    "--port", $BackendPort.ToString(),
    "--reload", "true",
    "--workers", "1"
  )

  Write-Host "Iniciando backend com $pythonExe ..."
  $proc = Start-Process -FilePath $pythonExe `
    -ArgumentList $backendArgs `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $backendOut `
    -RedirectStandardError $backendErr `
    -PassThru

  Set-Content -Path $backendPidFile -Value $proc.Id -Encoding ASCII

  if ($WaitForHealth) {
    if (-not (Wait-Http -Url $backendUrl -Retries (Get-HealthRetries) -DelaySec 1 -ProcessId $proc.Id)) {
      Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
      Remove-Item $backendPidFile -Force -ErrorAction SilentlyContinue
      throw "Backend nao respondeu em $backendUrl. Verifique $backendErr e $backendOut."
    }

    $trackedPid = Sync-PidFileWithPort -PidFile $backendPidFile -Port $BackendPort -FallbackProcessId $proc.Id
    if ($trackedPid) {
      Write-Host "Backend OK em $backendUrl (PID rastreado $trackedPid; launcher $($proc.Id))."
    }
    else {
      Write-Host "Backend OK em $backendUrl (launcher PID $($proc.Id))."
    }
    return
  }

  Start-Sleep -Seconds 2
  if (-not (Test-ProcessRunning -ProcessId $proc.Id)) {
    Remove-Item $backendPidFile -Force -ErrorAction SilentlyContinue
    throw "Backend encerrou logo apos iniciar. Verifique $backendErr e $backendOut."
  }

  $trackedPid = Sync-PidFileWithPort -PidFile $backendPidFile -Port $BackendPort -FallbackProcessId $proc.Id
  if ($trackedPid) {
    Write-Host "Backend iniciado em background (PID rastreado $trackedPid; launcher $($proc.Id))."
  }
  else {
    Write-Host "Backend iniciado em background (launcher PID $($proc.Id))."
  }
  Write-Host "Checagem completa: .\\scripts\\dev-status.ps1"
}

function Start-Frontend {
  $frontendUrl = "http://${FrontendHost}:$FrontendPort/"
  $frontendOut = Join-Path $runtimeDir "frontend.out.log"
  $frontendErr = Join-Path $runtimeDir "frontend.err.log"
  $frontendDir = Join-Path $projectRoot "Frontend\app"
  $viteEntrypoint = Join-Path $frontendDir "node_modules\vite\bin\vite.js"

  if (-not (Test-Path $viteEntrypoint)) {
    throw "Dependencias do frontend nao encontradas. Rode: cd Frontend/app; npm install"
  }

  if (Test-Path $frontendPidFile) {
    $existingPid = [int](Get-Content $frontendPidFile -Raw).Trim()
    if ((Test-ProcessRunning -ProcessId $existingPid) -or (Get-ListeningProcessIds -Port $FrontendPort)) {
      $trackedPid = Sync-PidFileWithPort -PidFile $frontendPidFile -Port $FrontendPort -FallbackProcessId $existingPid
      if ($trackedPid) {
        Write-Host "Frontend ja em execucao (PID rastreado $trackedPid)."
      }
      else {
        Write-Host "Frontend ja em execucao."
      }
      return
    }
    Remove-Item $frontendPidFile -Force
  }

  if (Test-HttpOk -Url $frontendUrl) {
    $trackedPid = Sync-PidFileWithPort -PidFile $frontendPidFile -Port $FrontendPort
    if ($trackedPid) {
      Write-Host "Frontend ja responde em $frontendUrl (PID adotado $trackedPid)."
    }
    else {
      Write-Host "Frontend ja responde em $frontendUrl (processo externo ao script)."
    }
    return
  }

  $nodeExe = Resolve-NodeExe
  $frontendArgLine = "`"$viteEntrypoint`" --host $FrontendHost --port $FrontendPort --strictPort"

  Write-Host "Iniciando frontend com $nodeExe ..."
  $proc = Start-Process -FilePath $nodeExe `
    -ArgumentList $frontendArgLine `
    -WorkingDirectory $frontendDir `
    -RedirectStandardOutput $frontendOut `
    -RedirectStandardError $frontendErr `
    -PassThru

  Set-Content -Path $frontendPidFile -Value $proc.Id -Encoding ASCII

  if ($WaitForHealth) {
    if (-not (Wait-Http -Url $frontendUrl -Retries (Get-HealthRetries) -DelaySec 1 -ProcessId $proc.Id)) {
      Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
      Remove-Item $frontendPidFile -Force -ErrorAction SilentlyContinue
      throw "Frontend nao respondeu em $frontendUrl. Verifique $frontendErr e $frontendOut."
    }

    $trackedPid = Sync-PidFileWithPort -PidFile $frontendPidFile -Port $FrontendPort -FallbackProcessId $proc.Id
    if ($trackedPid) {
      Write-Host "Frontend OK em $frontendUrl (PID rastreado $trackedPid; launcher $($proc.Id))."
    }
    else {
      Write-Host "Frontend OK em $frontendUrl (launcher PID $($proc.Id))."
    }
    return
  }

  Start-Sleep -Seconds 2
  if (-not (Test-ProcessRunning -ProcessId $proc.Id)) {
    Remove-Item $frontendPidFile -Force -ErrorAction SilentlyContinue
    throw "Frontend encerrou logo apos iniciar. Verifique $frontendErr e $frontendOut."
  }

  $trackedPid = Sync-PidFileWithPort -PidFile $frontendPidFile -Port $FrontendPort -FallbackProcessId $proc.Id
  if ($trackedPid) {
    Write-Host "Frontend iniciado em background (PID rastreado $trackedPid; launcher $($proc.Id))."
  }
  else {
    Write-Host "Frontend iniciado em background (launcher PID $($proc.Id))."
  }
  Write-Host "Checagem completa: .\\scripts\\dev-status.ps1"
}

try {
  if (-not $SkipBackend) {
    Start-Backend
  }
  else {
    Write-Host "Backend ignorado por parametro."
  }

  if (-not $SkipFrontend) {
    Start-Frontend
  }
  else {
    Write-Host "Frontend ignorado por parametro."
  }

  Write-Host ""
  if ($WaitForHealth) {
    Write-Host "Servicos prontos (com healthcheck concluido)."
  }
  else {
    Write-Host "Servicos iniciados. Rode .\\scripts\\dev-status.ps1 em alguns segundos."
  }
  Write-Host "Logs em: $runtimeDir"
  Write-Host "Use scripts/dev-status.ps1 para checar e scripts/dev-stop.ps1 para encerrar."
}
catch {
  Write-Error $_.Exception.Message
  exit 1
}
