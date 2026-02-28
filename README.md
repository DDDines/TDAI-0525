# CatalogAI (TDAI-0525)

Plataforma para importar catalogos, enriquecer dados de produtos pela web e gerar conteudo com IA.

## Estado atual
- Backend em modo OOP-only.
- Runtime principal usa `APP_MODE=oop`.
- API publica em `/api/v1`.
- Frontend React + Vite em `Frontend/app`.

## Requisitos
- Python 3.10+
- Node.js 18+
- (Opcional) PostgreSQL
- Playwright browsers (`playwright install`)
- Para preview de PDF: Poppler e Tesseract instalados no sistema

## Setup rapido
1. Configure ambiente:
   - `copy .env.example .env` (Windows) ou `cp .env.example .env` (Linux/macOS)
   - Ajuste no minimo: `SECRET_KEY`, `REFRESH_SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`
   - Defina `APP_MODE=oop`
   - Se nao for usar PostgreSQL, remova/comente `DATABASE_URL` para usar SQLite local
2. Backend:
   - `python -m venv .venv`
   - `.venv\\Scripts\\activate` (Windows) ou `source .venv/bin/activate` (Linux/macOS)
   - `pip install -r requirements-backend.txt`
   - `alembic -c Backend/alembic.ini upgrade head`
   - `playwright install`
   - `python run_backend.py`
3. Frontend:
   - `cd Frontend/app`
   - `npm install`
   - `npm run dev`

## URLs locais
- Frontend: `http://localhost:5173`
- API: `http://localhost:8000/api/v1`
- Swagger: `http://localhost:8000/docs`

## Testes e qualidade
- Backend: `pytest -q`
- Frontend testes: `cd Frontend/app && npm test`
- Frontend lint: `cd Frontend/app && npm run lint`
- Frontend build: `cd Frontend/app && npm run build`

## Documentacao por camada
- Backend: `README Backend.md`
- Frontend: `README Frontend.md`
- Frontend/app: `Frontend/app/README.md`
