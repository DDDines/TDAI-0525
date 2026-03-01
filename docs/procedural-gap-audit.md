# Auditoria De Gap Procedural (Meta: 100% OOP Literal)

Data da auditoria: 2026-03-01

## Baseline objetivo
- Funcoes de modulo no backend (fora testes): `179` (baseline inicial)
- Endpoints FastAPI (`@router.*` + `@app.*`): `80`
- Funcoes de modulo nao-endpoint (procedural/glue):
- Baseline inicial: `107`
- Estado atual apos esta rodada: `9` (reduzido `-98`)
- Closures/funcoes aninhadas fora de classes: `0`

## Guardrail adicionado
- Teste de arquitetura novo: `test_backend_top_level_non_endpoint_functions_are_allowlisted`.
- Regra: qualquer funcao top-level fora de endpoint HTTP falha, exceto allowlist tecnica.

## Funcoes nao-endpoint remanescentes (allowlist tecnica)
1. `Backend/alembic/env.py::run_migrations_offline`
2. `Backend/alembic/env.py::run_migrations_online`
3. `Backend/alembic/versions/71136158c1ff_backup.py::upgrade`
4. `Backend/alembic/versions/71136158c1ff_backup.py::downgrade`
5. `Backend/infrastructure/runtime/file_processing_runtime.py::get_runtime_service`
6. `Backend/infrastructure/runtime/ia_generation_runtime.py::get_runtime_service`
7. `Backend/infrastructure/runtime/limit_runtime.py::get_runtime_service`
8. `Backend/infrastructure/runtime/validator_crew_runtime.py::get_runtime_service`
9. `Backend/infrastructure/runtime/web_data_extractor_runtime.py::get_runtime_service`

## O que foi removido nesta rodada
- Wrapper top-level de `Backend/testing/runtime_apis.py` convertido para classe (`RuntimeApis`).
- Wrappers top-level remanescentes convertidos para aliases OO em:
- `Backend/routers/auth_utils.py`
- `Backend/routers/password_recovery.py`
- `Backend/routers/social_auth.py`
- `Backend/initial_data.py`
- `Backend/main.py`

## Suite de validacao
- `pytest -q`: `417 passed`
- `pytest -q Backend/tests/test_architecture_boundaries.py`: `39 passed`

## Criterio de concluido (literal extremo)
- `0` funcoes de modulo nao-endpoint fora allowlist tecnica (Alembic + providers runtime).
- `0` closures/funcoes aninhadas fora de classes.
- `0` wrappers funcionais de compatibilidade em `core`, `routers`, `application/services`.
- Suite verde:
- `pytest -q`
- `Backend/tests/test_architecture_boundaries.py`
