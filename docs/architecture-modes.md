# Architecture Modes (`APP_MODE`)

The backend now supports three runtime architecture modes to allow safe migration from legacy code to OOP pipelines without deleting old code.

## Modes

- `legacy` (default): executes legacy pipeline only.
- `oop`: executes OOP pipeline only.
- `shadow`: executes legacy pipeline and compares execution plans against OOP.

## Environment

Configure in `.env`:

```env
APP_MODE=legacy
```

## Current coverage

- Catalog import finalization pipeline (`/api/v1/produtos/importar-catalogo-finalizar/{file_id}/`)
- Web enrichment start pipeline (`/api/v1/enriquecimento-web/produto/{produto_id}`)

## Notes

- Legacy code remains in place and is not removed.
- In `shadow` mode, the API behavior remains legacy while diffs are logged for comparison.
- This is the first migration step; future OOP use cases can replace legacy executors incrementally.

## Current migration architecture

- `Backend/legacy/pipelines/*`: builders that keep the legacy path untouched.
- `Backend/application/contracts/pipeline_commands.py`: command objects used by OOP orchestration.
- `Backend/application/orchestrators/*`: mode-aware pipeline orchestration (`legacy/oop/shadow`).
- `Backend/application/services/pipeline_dispatcher.py`: despacho unificado (inline/thread/background).
- `Backend/application/use_cases/*`: camada OO de processamento (atualmente em delegação controlada).
- `Backend/application/pipelines/*`: OOP builders/executors that can be evolved independently.
