# CatalogAI (TDAI-0525)

Plataforma para importar catalogos, enriquecer dados de produtos via web e gerar conteudo com IA para e-commerce.

## Estado Atual (2026-03-08)
- Backend e frontend estao fechados com cobertura literal `100%`.
- Backend em arquitetura OOP-only (`APP_MODE=oop`).
- API publica versionada em `/api/v1`.
- Frontend React + Vite em `Frontend/app`.
- LM Studio local suportado lado a lado com OpenAI/Gemini.
- Prompt templates versionados no banco.
- Dispatch assincrono preparado com Celery + Redis.
- CI/CD inclui gate de testes, migration safety e deploy blue-green para VPS Linux.

Validacao executada em 2026-03-08:
- `python -m pytest -q`: `1054 passed`
- backend coverage: `100.00%`
- `cd Frontend/app && npm run test:coverage`: `67 suites / 625 tests passed`
- frontend coverage: `100%`
- `cd Frontend/app && npm run lint`: `OK`
- `cd Frontend/app && npm run build`: `OK`
- `cd Frontend/app && npm run test:e2e`: `2 passed`

## Estrutura Do Projeto
- `Backend/`: API FastAPI, aplicacao OOP, repositorios e runtime modules.
- `Frontend/app/`: SPA React (Vite), paginas e componentes.
- `docs/`: arquitetura, migracao OOP, execucao local e backlog.
- `scripts/`: automacao para subir/parar ambiente local.
- `Prototipos/`: artefatos historicos e PDFs de planejamento.

## Requisitos
- Python 3.10+
- Node.js 18+
- PostgreSQL (opcional; sem `DATABASE_URL` usa SQLite local)
- Playwright browsers (`playwright install`)
- Para preview/OCR de PDF: Poppler e Tesseract instalados no sistema

## Setup Rapido (Manual)
1. Configure ambiente:
   - Windows: `copy .env.example .env`
   - Linux/macOS: `cp .env.example .env`
   - Defina no minimo: `SECRET_KEY`, `REFRESH_SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`
   - Garanta `APP_MODE=oop`
2. Backend:
   - `python -m venv .venv`
   - Windows: `.\.venv\Scripts\Activate.ps1`
   - Linux/macOS: `source .venv/bin/activate`
   - `python -m pip install -r requirements-backend.txt`
   - `alembic -c Backend/alembic.ini upgrade head`
   - `playwright install`
   - `python run_backend.py`
3. Frontend:
   - `cd Frontend/app`
   - `npm install`
   - `npm run dev`

## Execucao Local Com Scripts (Windows/PowerShell)
No diretorio `Project`:
- Subir backend + frontend: `.\scripts\dev-start.ps1`
- Ver status: `.\scripts\dev-status.ps1`
- Encerrar: `.\scripts\dev-stop.ps1`

Detalhes extras: `docs/EXECUCAO_LOCAL.md`.

## URLs Locais
- Frontend: `http://localhost:5173`
- API base: `http://localhost:8000/api/v1`
- Swagger: `http://localhost:8000/docs`

## Testes E Qualidade
- Backend: `python -m pytest -q`
- Frontend (coverage): `cd Frontend/app && npm run test:coverage`
- Frontend (lint): `cd Frontend/app && npm run lint`
- Frontend (build): `cd Frontend/app && npm run build`
- End-to-end: `cd Frontend/app && npm run test:e2e`

## Validacao Local De IA Sem Custo Externo
- Sincronizar os prompts versionados no banco: `python scripts/sync_prompt_templates.py`
- Rodar evals locais contra o LM Studio: `python scripts/run_evals.py --model google/gemma-3-12b`
- Validar o fluxo real via API com produto descartavel: `python scripts/validate_local_llm_workflow.py --base-url http://127.0.0.1:8000`
- O ultimo comando autentica no backend local, cria um produto temporario, dispara geracao de titulos e descricao no endpoint `openai`, valida a qualidade com regras deterministicas e apaga o produto ao final.

## Deploy E Operacao
- CI principal: `.github/workflows/python-tests.yml`
- Deploy VPS blue-green: `.github/workflows/deploy-vps.yml`
- Bootstrap do host Linux: `bash scripts/bootstrap-vps.sh`
- Safety check de migrations: `python scripts/check_migration_safety.py`
- Validacao de upgrade Alembic: `python scripts/validate_alembic_upgrade.py`
- Smoke de release: `python scripts/smoke_release.py --base-url http://127.0.0.1:8000`
- Rollout blue-green: `bash scripts/deploy-blue-green.sh`
- Rollback blue-green: `bash scripts/rollback-blue-green.sh`
- Guia operacional: `docs/PRODUCAO_VPS.md`

## Manutencao Retroativa (Conteudo)
- Dry-run de limpeza retroativa (sem gravar): `python scripts/backfill_product_content_sanitization.py --limit 200`
- Aplicar limpeza retroativa no banco: `python scripts/backfill_product_content_sanitization.py --apply`
- Escopos opcionais: `--user-id <id>`, `--produto-id <id>`, `--commit-every <n>`, `--verbose`

## Documentacao Importante
- Arquitetura e modos: `docs/architecture-modes.md`
- Progresso migracao OOP: `docs/oop-migration-progress.md`
- Auditoria gap procedural: `docs/procedural-gap-audit.md`
- Bugs priorizados: `docs/BUGS_PRIORIZADOS_2026-02-18.md`
- Frontend (detalhes): `Frontend/app/README.md`
