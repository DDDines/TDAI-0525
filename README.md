# CommerceFolio

Plataforma para importar catalogos, enriquecer dados de produtos via web e gerar conteudo com IA para e-commerce.

## Estado Atual (2026-03-11)
- Produto full-stack funcional para importar catalogos, enriquecer dados web e gerar conteudo com IA.
- Backend em arquitetura OOP-only (`APP_MODE=oop`) com API versionada em `/api/v1`.
- Frontend React + Vite em `Frontend/app`.
- LM Studio local suportado para geracao e para extracao multimodal de PDF.
- OpenAI, Gemini e Google CSE seguem opcionais por configuracao; sem chaves, o sistema usa os caminhos locais/fallback disponiveis.
- Prompt templates versionados no banco.
- Dispatch assincrono preparado com Celery + Redis.
- CI/CD inclui gate de testes, migration safety e deploy blue-green para VPS Linux.

Observacao importante:
- Este repositorio esta em refinamento ativo. Nao trate numeros fixos de cobertura ou quantidade de testes neste README como fonte da verdade da branch atual.
- Para validar o estado real do codigo, use os comandos da secao `Testes E Qualidade` e os scripts da secao `Validacao Local De IA Sem Custo Externo`.

## Novidades Da Rodada
- Conteudo gerado e edicao do produto agora compartilham o mesmo workspace visual para titulos e descricao.
- A tela `Conteudo Gerado do Produto` permite gerar titulos e descricao diretamente, com checkbox `Usar IA` quando o usuario esta no modo completo.
- A lista de produtos persiste pagina, busca, ordenacao e filtros na URL; ao voltar de conteudo/edicao, o contexto da lista e restaurado.
- Usuarios nao-admin agora possuem dashboard operacional proprio via `GET /dashboard/me`.
- O modo da experiencia do produto passa a ser derivado do plano e do perfil (`product_experience_mode`): `Pro/Enterprise/admin => complete`, `Gratuito => basic`.
- A tela de enriquecimento abre por padrao em `Enriquecidos` e aceita os escopos `Todos`, `Pendentes` e `Falharam`.
- Produtos e fornecedores agora suportam selecao em massa por `pagina atual` ou `todos os resultados filtrados`.
- O sistema possui uma nova area de `Credenciais e Integracoes` em Configuracoes, com precedencia `Pessoal > Empresa > Sistema` para OpenAI, Google Gemini e Google CSE.
- Tipos de produto podem marcar atributos com `collect_in_ai=true` para orientar coleta e sugestoes no modo IA.
- A limpeza final de conteudo remove ruido como `%20`, entidades HTML, redirects e fragmentos de query antes de promover o texto para campos visiveis.

## Estrutura Do Projeto
- `Backend/`: API FastAPI, aplicacao OOP, repositorios e runtime modules.
- `Frontend/app/`: SPA React (Vite), paginas e componentes.
- `docs/`: arquitetura, migracao OOP, execucao local, backlog e operacao.
- `scripts/`: automacao de ambiente local, validacao, evals e operacao/deploy.
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
- Gate de qualidade de output local: `python scripts/validate_output_quality_suite.py`

## Validacao Local De IA Sem Custo Externo
- Para LM Studio local, mantenha `AI_PROVIDER=lm_studio` e use `LM_STUDIO_MAX_CONCURRENCY=1` para evitar sobrecarga durante testes/smokes.
- A ingestao de PDF em `extraction_mode=ia` agora envia texto da pagina e, quando disponivel, um pequeno contexto visual multimodal para o LM Studio; ajuste `PDF_LLM_IMAGE_DPI` se precisar equilibrar legibilidade e peso da requisicao.
- Tanto na ingestao quanto no enrichment por PDF, o sistema prioriza as paginas com mais sinal de produto para o contexto visual; ajuste `PDF_LLM_PAGE_SCAN_LIMIT` se quiser ampliar ou reduzir a janela de paginas analisadas antes da selecao.
- Sincronizar os prompts versionados no banco: `python scripts/sync_prompt_templates.py`
- Rodar evals locais contra o LM Studio: `python scripts/run_evals.py --model google/gemma-3-12b`
- Validar o fluxo real via API com produto descartavel: `python scripts/validate_local_llm_workflow.py --base-url http://127.0.0.1:8000`
- Validar importacao + geracao com um catalogo publico real: `python scripts/validate_real_catalog_pipeline.py --base-url http://127.0.0.1:8000`
- Validar um conjunto curado de saidas com score deterministico: `python scripts/validate_output_quality_suite.py`
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
