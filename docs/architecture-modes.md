# Architecture Mode (`APP_MODE`)

The backend runs in OOP-only mode.

## Supported value

- `oop`: executes the OOP pipeline.

Any other configured value is accepted only for transition compatibility and normalized to `oop` with a warning.

## Environment

Configure in `.env`:

```env
APP_MODE=oop
```

## Coverage

- Catalog import finalization pipeline (`/api/v1/produtos/importar-catalogo-finalizar/{file_id}/`)
- Web enrichment start pipeline (`/api/v1/enriquecimento-web/produto/{produto_id}`)

## Runtime architecture

- `Backend/application/contracts/pipeline_commands.py`: command objects used by orchestration.
- `Backend/application/orchestrators/*`: OOP orchestrators.
- `Backend/application/services/pipeline_dispatcher.py`: unified dispatch (inline/thread/background).
- `Backend/application/use_cases/*`: OOP processing use cases.
- `Backend/application/pipelines/*`: OOP builders/executors.
