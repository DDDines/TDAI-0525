# CatalogAI (TDAI-0525)

Plataforma para importar catalogos, enriquecer dados de produtos via web e gerar conteudo com IA para e-commerce.

## Estado Atual (2026-03-06)
- Backend e frontend estao operacionais no fluxo principal do MVP.
- Backend em arquitetura OOP-only (`APP_MODE=oop`).
- API publica versionada em `/api/v1`.
- Frontend React + Vite em `Frontend/app`.
- Backlog P0/P1/P2 documentado em `docs/BUGS_PRIORIZADOS_2026-02-18.md` foi concluido.

Validacao executada em 2026-03-06:
- `pytest -q`: `399 passed`
- `npm test`: `22 suites / 53 tests passed`
- `npm run lint`: `OK`
- `npm run build`: `OK`

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
- Backend: `pytest -q`
- Frontend (testes): `cd Frontend/app && npm test`
- Frontend (lint): `cd Frontend/app && npm run lint`
- Frontend (build): `cd Frontend/app && npm run build`

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
