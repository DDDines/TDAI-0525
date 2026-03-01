# Auditoria De Gap Procedural (Meta: 100% OOP Literal)

Data da auditoria: 2026-03-01

## Baseline objetivo
- Funcoes de modulo no backend (fora testes): `179` (baseline inicial)
- Endpoints FastAPI (`@router.*` + `@app.*`): `77`
- Funcoes de modulo nao-endpoint (procedural/glue):
- Baseline inicial: `107`
- Estado atual apos esta rodada: `68` (reduzido `-39`)
- Closures/funcoes aninhadas fora de classes: `13`

## O que foi resolvido nesta rodada
- `Backend/main.py`
- removidos monolitos `_build_allowed_origins_core`, `_startup_event_create_defaults_core`, `_create_new_user_core`
- bootstrap consolidado em metodos de `_MainBootstrapRuntime`
- `Backend/initial_data.py`
- removido `_create_initial_data_core`
- seed consolidado em metodos de `_InitialDataRuntime`
- `Backend/routers/web_enrichment.py`
- removidos wrappers internos duplicados
- mapeamento consolidado em `_WebEnrichmentMappingRuntime`
- `Backend/routers/generation.py`
- removida funcao solta `_tarefa_processar_geracao_e_registrar_uso`
- `Backend/auth.py`
- removidos wrappers publicos redundantes de compatibilidade
- mantidas dependencias HTTP + endpoints
- `Backend/routers/social_auth.py` e `Backend/routers/password_recovery.py`
- migrados para consumo de `get_auth_workflow()` por objeto
- `Backend/core/security.py`
- removida API funcional global (`verify_password`, `get_password_hash`, etc.)
- mantido acesso OO via `SecurityWorkflow`
- consumidores atualizados (`user_repository`, `auth_utils`, `tests/test_security.py`)
- `Backend/core/email_utils.py`
- removidos wrappers funcionais globais (`send_email`, `send_password_reset_email`, `conf`)
- consumo movido para instancia de `EmailWorkflow` em `password_recovery`
- `Backend/routers/produtos.py`
- removidos wrappers privados duplicados de saneamento/qualidade

## Estado atual por dominio (funcoes nao-endpoint)
- `routers`: 25
- `core`: 8
- `application`: 8
- `main.py`: 6
- `infrastructure`: 5
- `alembic`: 4
- `auth.py`: 3
- `initial_data.py`: 2
- `database.py`: 2
- `tasks.py`: 2
- `create_tables.py`: 2

## Hotspots restantes (>= 8 linhas)
1. `Backend/application/services/repository_runtime_support.py::call_repository_method` (32)
2. `Backend/routers/web_enrichment.py::is_source_relevant_for_product` (14)
3. `Backend/routers/auth_utils.py::get_current_user` (12)
4. `Backend/application/services/repository_runtime_support.py::bind_repository` (11)
5. `Backend/routers/web_enrichment.py::build_payload_enriquecimento_visivel` (9)
6. `Backend/application/services/service_container.py::build_request_scoped_dependency` (9)

## Closures restantes (13)
- `application/services/catalog_import_ingest_service.py`
- `application/services/catalog_import_sanitization_service.py`
- `application/services/pipeline_dispatcher.py`
- `application/services/service_container.py`
- `application/services/web_enrichment_normalization_service.py`
- `application/services/web_enrichment_payload_service.py`
- `infrastructure/runtime_modules/file_processing_module.py`
- `infrastructure/runtime_modules/web_data_extractor_module.py`

## Suíte de validacao
- `pytest -q`: `416 passed`
- `pytest -q Backend/tests/test_architecture_boundaries.py`: `38 passed`

## O que ainda falta para 100% OOP literal
1. Eliminar wrappers utilitarios em routers (`web_enrichment`, `auth_utils`, remanescentes em `produtos`) migrando testes para servicos de aplicacao.
2. Substituir helpers funcionais da aplicacao (`repository_runtime_support.py`, `product_repositories.py`) por factories/classes de suporte OO.
3. Migrar providers utilitarios (`database.py`, `tasks.py`, `create_tables.py`, `core/app_mode.py`, `core/config.py`) para contratos OO, mantendo entrypoints minimos.
4. Resolver as 13 closures restantes (extrair para metodos privados de classe ou objetos dedicados).

## Critério de concluido (literal extremo)
- `0` funcoes de modulo nao-endpoint (fora allowlist de entrypoints CLI/ASGI).
- `0` closures/funcoes aninhadas fora de classes.
- `0` wrappers funcionais de compatibilidade em `core`, `routers`, `application/services`.
- Suite verde:
- `pytest -q`
- `Backend/tests/test_architecture_boundaries.py`
