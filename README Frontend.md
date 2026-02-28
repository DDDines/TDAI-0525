# CatalogAI - Frontend

Frontend React + Vite do CatalogAI.

## Local
- Pasta: `Frontend/app`
- Porta padrao: `5173`

## Setup rapido
1. `cd Frontend/app`
2. `npm install`
3. `npm run dev`

## Backend esperado
- Em desenvolvimento o frontend usa base `/api/v1` e proxy do Vite para `http://localhost:8000`.
- Se necessario, defina `VITE_API_BASE_URL` para sobrescrever o destino.

## Comandos uteis
- Testes: `npm test`
- Lint: `npm run lint`
- Build: `npm run build`
- Preview build: `npm run preview`

## Fluxo minimo de validacao
1. Suba backend (`python run_backend.py` na raiz)
2. Suba frontend (`npm run dev` em `Frontend/app`)
3. Acesse `http://localhost:5173`

