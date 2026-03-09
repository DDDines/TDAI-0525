# Producao no Linux VPS

## Topologia alvo
- Frontend estatico servido por `nginx`
- API FastAPI em blue-green nas portas `8001` e `8002`
- Worker Celery no mesmo host
- Redis local no VPS
- Postgres gerenciado fora do VPS

## Bootstrap inicial do host
No servidor, como `root`:

```bash
cd /opt
git clone <repo> catalogai-bootstrap
cd catalogai-bootstrap/Project
APP_ROOT=/srv/catalogai DOMAIN=catalogai.example.com bash scripts/bootstrap-vps.sh
```

Isso instala `python3`, `nginx`, `redis-server`, `poppler-utils`, `tesseract-ocr` e `Node.js 20`, cria a estrutura de diretórios em `APP_ROOT` e publica a configuracao inicial do `nginx`.

## Estrutura esperada no VPS
- `APP_ROOT/releases/<sha>`: releases imutaveis
- `APP_ROOT/current`: symlink para a release ativa
- `APP_ROOT/shared/.env`: configuracao compartilhada
- `APP_ROOT/shared/active-slot`: slot ativo (`blue` ou `green`)
- `APP_ROOT/shared/last-slot`: ultimo slot ativo, usado no rollback
- `APP_ROOT/shared/logs`: logs do backend e do worker
- `APP_ROOT/shared/run`: pid files

## Arquivo de ambiente compartilhado
Crie `APP_ROOT/shared/.env` a partir de `Project/.env.example` e ajuste pelo menos:
- `DATABASE_URL`
- `SECRET_KEY`
- `REFRESH_SECRET_KEY`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `FRONTEND_URL`
- `BACKEND_CORS_ORIGINS`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `ASYNC_DISPATCH_PROVIDER=celery`
- credenciais do provider de IA usado em producao

## Secrets do GitHub Actions
Defina no repositório:
- `VPS_HOST`
- `VPS_USER`
- `VPS_APP_ROOT`
- `VPS_SSH_KEY`

## Deploy
Use o workflow `Deploy CatalogAI to VPS` em modo `deploy`.

Fluxo executado:
1. envia o release por `git archive`
2. cria ou reaproveita `.venv`
3. instala dependencias de runtime a partir de `requirements-backend-prod.txt`
4. executa upgrade/bootstrap do banco
   - em banco vazio, o deploy faz bootstrap do schema atual, cria os defaults e carimba `head`
5. builda o frontend
6. sobe backend + worker no slot inativo
7. executa `healthcheck` e `scripts/smoke_release.py`
8. troca o upstream do `nginx`
9. atualiza `active-slot` e `last-slot`

## Rollback
Use o mesmo workflow em modo `rollback`.

O rollback:
1. valida saude do slot alvo
2. reescreve o upstream do `nginx`
3. recarrega o `nginx`
4. atualiza `active-slot`

## Smoke script de release
O deploy chama `scripts/smoke_release.py` antes do switch.

Valida:
- `GET /health`
- `GET /`
- `POST /api/v1/auth/token` se `ADMIN_EMAIL` e `ADMIN_PASSWORD` estiverem disponiveis
- `GET /api/v1/produtos/?skip=0&limit=1`
- `GET /api/v1/product-types/?skip=0&limit=1`

## Observacoes operacionais
- O frontend estatico usa `APP_ROOT/current/Frontend/app/dist`, por isso o symlink `current` faz parte do rollout.
- O switch de trafego eh feito apenas no upstream do `nginx`; o slot anterior pode continuar rodando para rollback rapido.
- Se quiser economizar memoria, defina `KEEP_PREVIOUS_SLOT_RUNNING=0` no ambiente do deploy.
