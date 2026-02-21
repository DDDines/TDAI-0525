# Execucao Local Rapida (Windows/PowerShell)

## 1) Subir backend + frontend

No diretorio `Project`:

```powershell
.\scripts\dev-start.ps1
```

O script:
- sobe backend em `http://127.0.0.1:8000`
- sobe frontend em `http://127.0.0.1:5173`
- grava logs em `Project\.runtime\`
- retorna rapido (nao bloqueia o terminal)

Se quiser aguardar healthcheck completo no proprio comando:

```powershell
.\scripts\dev-start.ps1 -WaitForHealth
```

`-WaitForHealth` usa timeout de 60s por padrao (ajustavel com `-HealthTimeoutSec`).

## 2) Ver status

```powershell
.\scripts\dev-status.ps1
```

## 3) Encerrar servicos iniciados pelo script

```powershell
.\scripts\dev-stop.ps1
```

## Opcoes uteis

Subir so backend:

```powershell
.\scripts\dev-start.ps1 -SkipFrontend
```

Subir so frontend:

```powershell
.\scripts\dev-start.ps1 -SkipBackend
```

Mudar porta/host:

```powershell
.\scripts\dev-start.ps1 -BackendPort 8001 -FrontendPort 5174
```

## Observacao

Se o backend/frontend ja estiver rodando fora do script, ele detecta URL ativa e nao tenta abrir outra instancia.
