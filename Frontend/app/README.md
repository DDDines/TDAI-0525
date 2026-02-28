# CatalogAI Frontend (Vite)

Aplicacao React do CatalogAI.

## Requisitos
- Node.js 18+

## Desenvolvimento
```bash
cd Frontend/app
npm install
npm run dev
```

## Qualidade
```bash
npm test
npm run lint
npm run build
```

## Integracao com backend
- Base padrao: `/api/v1`
- Proxy local do Vite: `http://localhost:8000`
- Para sobrescrever, use `VITE_API_BASE_URL`
