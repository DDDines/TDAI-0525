# Auditoria De Gap Procedural (Meta: 100% OOP Literal)

Data da auditoria: 2026-03-01

## Baseline objetivo
- Funcoes de modulo no backend (fora testes): `179` (baseline inicial)
- Endpoints FastAPI (`@router.*` + `@app.*`): `80`
- Funcoes de modulo nao-endpoint (procedural/glue):
- Baseline inicial: `107`
- Estado atual apos esta rodada: `10` (reduzido `-97`)
- Closures/funcoes aninhadas fora de classes: `0`

## O que foi resolvido nesta rodada
- Conversao de factories/wrappers de modulo para aliases OO em `core/*`, `routers/*`, `application/services/*`.
- Dependencias HTTP de autenticacao estabilizadas em `auth.py` e `routers/auth_utils.py` sem fallback dinamico.
- Extracao de closures para metodos privados em:
- `Backend/application/services/catalog_import_sanitization_service.py`
- `Backend/application/services/catalog_import_ingest_service.py`
- `Backend/application/services/web_enrichment_normalization_service.py`
- `Backend/application/services/web_enrichment_payload_service.py`
- `Backend/application/services/pipeline_dispatcher.py`
- `Backend/infrastructure/runtime_modules/web_data_extractor_module.py`
- `Backend/infrastructure/runtime_modules/file_processing_module.py`

## Estado atual por dominio (funcoes nao-endpoint)
- `alembic`: 4
- `infrastructure/runtime`: 5
- `testing`: 1

## Funcoes nao-endpoint remanescentes (lista completa)
1. `Backend/alembic/env.py::run_migrations_offline`
2. `Backend/alembic/env.py::run_migrations_online`
3. `Backend/alembic/versions/71136158c1ff_backup.py::upgrade`
4. `Backend/alembic/versions/71136158c1ff_backup.py::downgrade`
5. `Backend/infrastructure/runtime/file_processing_runtime.py::get_runtime_service`
6. `Backend/infrastructure/runtime/ia_generation_runtime.py::get_runtime_service`
7. `Backend/infrastructure/runtime/limit_runtime.py::get_runtime_service`
8. `Backend/infrastructure/runtime/validator_crew_runtime.py::get_runtime_service`
9. `Backend/infrastructure/runtime/web_data_extractor_runtime.py::get_runtime_service`
10. `Backend/testing/runtime_apis.py::processar_linha_padronizada`

## Closures restantes
- `0` (nenhum `def` aninhado detectado no backend fora testes)

## Suite de validacao
- `pytest -q`: `416 passed`
- `pytest -q Backend/tests/test_architecture_boundaries.py`: `38 passed`

## O que ainda falta para 100% OOP literal
1. Decisao arquitetural explicita para as 4 funcoes do Alembic (entrypoints de migracao).
2. Decisao arquitetural explicita para os 5 providers `get_runtime_service` (obrigatorios por teste de fronteira).
3. (Opcional) mover `Backend/testing/runtime_apis.py::processar_linha_padronizada` para adapter de teste baseado em classe.

## Criterio de concluido (literal extremo)
- `0` funcoes de modulo nao-endpoint fora allowlist tecnica (Alembic + providers runtime).
- `0` closures/funcoes aninhadas fora de classes.
- `0` wrappers funcionais de compatibilidade em `core`, `routers`, `application/services`.
- Suite verde:
- `pytest -q`
- `Backend/tests/test_architecture_boundaries.py`
