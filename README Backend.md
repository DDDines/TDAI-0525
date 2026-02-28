# CatalogAI - Backend

Backend FastAPI do CatalogAI.

## Estado atual
- Arquitetura OOP-only no caminho de execucao.
- `APP_MODE` ativo deve ser `oop`.
- Servicos de aplicacao em `Backend/application/services`.
- Runtimes/adapters em `Backend/infrastructure`.

## Requisitos
- Python 3.10+
- Dependencias de `requirements-backend.txt`
- Playwright browsers (`playwright install`)
- Para PDF/OCR: Poppler (`pdftoppm`) e Tesseract instalados

## Setup rapido
1. `copy .env.example .env` (Windows) ou `cp .env.example .env`
2. Ajuste no minimo:
   - `SECRET_KEY`
   - `REFRESH_SECRET_KEY`
   - `ADMIN_EMAIL`
   - `ADMIN_PASSWORD`
   - `APP_MODE=oop`
3. Se nao usar PostgreSQL, remova `DATABASE_URL` para cair em SQLite local
4. Crie ambiente e instale dependencias:
   - `python -m venv .venv`
   - `.venv\\Scripts\\activate` (Windows) ou `source .venv/bin/activate`
   - `pip install -r requirements-backend.txt`
5. Migre banco:
   - `alembic -c Backend/alembic.ini upgrade head`
6. Instale browsers Playwright:
   - `playwright install`
7. Suba a API:
   - `python run_backend.py`

## Comandos uteis
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Testes backend: `pytest -q`

## Observacoes
- Execute os comandos a partir da raiz do repositorio (`Project`).
- `AUTO_CREATE_TABLES=true` e util apenas para desenvolvimento local.
