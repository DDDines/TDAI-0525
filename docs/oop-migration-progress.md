# Migracao OOP - Progresso Real

## Visao geral

A migracao OOP do backend foi concluida.
O runtime opera em modo OOP-only (`APP_MODE=oop`) e a camada `Backend/services` foi removida do codigo produtivo.

## Checklist por dominio

### Fase 0 - Guardrails de arquitetura

- [x] Teste de arquitetura criado: `Backend/tests/test_architecture_boundaries.py`.
- [x] Regra: `Backend/application/**` nao pode importar `Backend/services/**`.
- [x] Regra: `Backend/application/**` nao pode importar `Backend/routers/**`.
- [x] Regra: `Backend/application/services/**` nao pode definir `__getattr__` em adapters.
- [x] Regra: `Backend/application/services/**` nao pode chamar metodo privado de objeto externo (`obj._algo()`).
- [x] Regra: codigo backend nao pode importar `Backend.services`.
- [x] Regra: routers nao importam mais `Backend.application.services` (pacote raiz); apenas modulos explicitos.
- [x] Regra: `data_access_service` nao pode chamar funcoes de modulo `crud_*` diretamente (delegacao obrigatoria por workflow OO).
- [x] Regra: `Backend/application/services/__init__.py` sem imports eager/re-export (evita side effects e ciclos).

### Fase 1 - Onda File Processing

- [x] Novo pacote criado: `Backend/application/services/file_processing/`.
- [x] Contrato criado: `FileProcessingPort`.
- [x] Servicos por responsabilidade:
  - `storage_service.py`
  - `tabular_ingestion_service.py`
  - `pdf_ingestion_service.py`
  - `preview_service.py`
  - `pdf_assets_service.py`
  - `orchestrator_service.py`
- [x] Facade de transicao removida; fluxo usa `FileProcessingOrchestratorService` + adapter OO explicito.
- [x] `CatalogExtractionService.processar_linha_padronizada` passou a usar metodo publico.
- [x] API publica consolidada em runtime OOP: `processar_linha_padronizada(...)`.

### Fase 2 - Onda Web Data Extractor

- [x] Novo pacote criado: `Backend/application/services/web_data_extractor/`.
- [x] Contrato criado: `WebDataExtractorPort`.
- [x] Servicos por responsabilidade:
  - `search_service.py`
  - `content_service.py`
  - `metadata_service.py`
  - `llm_service.py`
  - `ocr_service.py`
  - `orchestrator_service.py`
- [x] Facade de transicao removida; fluxo usa `WebDataExtractorOrchestratorService` + adapter OO explicito.
- [x] Chamada privada removida em componente (`_normalizar...` -> metodo publico).
- [x] API publica consolidada em runtime OOP: `normalizar_dados_de_metadados(...)`.
- [x] Encapsulamento de estado global (cache/semaphore/flag Playwright) em runtime injetavel dedicado, com teste de isolamento.

### Fase 3 - Onda IA / Limit / Validator

- [x] Contratos internos adicionados em `Backend/application/services/ports.py`:
  - `IAGenerationPort`
  - `LimitPort`
  - `ValidationPort`
- [x] Camadas de transicao removidas; consumo direto de `IAGenerationService`, `LimitService` e `ValidatorCrewAdapter`.
- [x] Defaults OOP migrados para adapters explicitos em `Backend/infrastructure/adapters/` (sem bridge legado no caminho padrao OOP).
- [x] Bridges legados removidos de `Backend/infrastructure/legacy/`.

### Fase 4 - Orquestracao e desacoplamento de borda

- [x] Import cruzado removido: `Backend/routers/fornecedores.py` nao depende mais de `Backend/routers/produtos.py`.
- [x] Runners unificados em implementacao OOP unica; execucao via `execute`.
- [x] Garantia de teste: `APP_MODE=oop` executa apenas executor OOP selecionado pelo orquestrador.
- [x] Fluxo real validado em `APP_MODE=oop` sem bridge legado no caminho OOP.

### Fase 5 - Limpeza final

- [x] Remover proxies `*_legacy_service` de modulos backend e camada de roteadores.
- [x] Remover pipelines legados de orquestracao (`Backend/legacy/pipelines/`) sem referencias restantes em runtime/testes.
- [x] Remover bridges de transicao em `Backend/infrastructure/legacy/`.
- [x] Remover camada central de proxy legado (`Backend/core/deprecation.py`) e testes associados.
- [x] Remover componentes de aplicacao que apenas encapsulavam modulo legado (`file_processing_components` e `web_data_extractor_components`).
- [x] Remover guard de runtime legado (`Backend/core/legacy_guard.py`) e testes associados.
- [x] Remover comparador `shadow_result_comparator` e hooks de gravacao `shadow_compare` dos task services OOP.
- [x] Migrar implementacoes de runtime de `Backend/services/*` para `Backend/infrastructure/runtime_modules/*`.
- [x] Pacotes legados `Backend/infrastructure/runtime/*` e `Backend/infrastructure/runtime_services/*` removidos do codigo produtivo.
- [x] `Backend/application/services/__init__.py` simplificado para pacote sem eager imports (imports explicitos por modulo).
- [x] `DataAccessService` migrado para delegacao OO via workflows `crud_*` (sem uso de funcoes top-level de CRUD na camada).
- [x] Bridge dinamica de repositorio removida (`repository_runtime_support.py` e `call_repository_method(...)`).
- [x] Assinaturas de pipeline/orquestracao ajustadas sem parametro procedural por chamada (`db_session_factory`).
- [x] Repositorio `FornecedorImportJobRepository` unificado no padrao OO (`Session` no construtor).
- [x] Estado mutavel global removido de runtime de file processing (`global` -> estado de instancia).
- [x] Atualizar documentacao final de arquitetura e matriz de conclusao.

## Criterios objetivos de fechamento

- [x] Zero import de `Backend/services` dentro de `Backend/application/services`.
- [x] Zero uso de `__getattr__` em adapters da camada de aplicacao.
- [x] Zero chamada a metodo privado de objeto externo em `Backend/application/services`.
- [x] Zero import de `Backend/routers` em `Backend/application`.
- [x] Sem bridges/proxies legados ativos em runtime de aplicacao.
- [x] Zero `repository_runtime_support.py` e zero `call_repository_method(...)` no codigo produtivo.
- [x] Zero parametro `db_session_factory` em metodos publicos de servico (somente injecao no construtor).
- [x] Zero import de `Backend/services` em todo backend produtivo (`application`, `routers`, `infrastructure`).
- [x] Zero import de `Backend/services` em todo backend (incluindo runtime e testes de backend).

## Matriz de isolamento

| Fluxo | Modulo OOP principal | Dependencia direta de `Backend/services` na aplicacao |
|---|---|---|
| Importacao de catalogo (arquivo) | `Backend/application/services/file_processing/` | Nao |
| Enriquecimento web | `Backend/application/services/web_data_extractor/` | Nao |
| IA generation | `Backend/application/services/ia_generation_service.py` + `Backend/application/services/ports.py` | Nao |
| Limites e creditos | `Backend/application/services/limit_service.py` + `Backend/application/services/ports.py` | Nao |
| Validator crew | `Backend/infrastructure/adapters/validator_crew_adapter.py` + `Backend/application/services/ports.py` | Nao |

## Arquitetura final

- Adapters OOP padrao concentrados em `Backend/infrastructure/adapters/`.
- Implementacoes de dominio/runtime concentradas em `Backend/infrastructure/runtime_modules/`.
- Pacotes legados de transicao removidos:
  - `Backend/infrastructure/runtime/`
  - `Backend/infrastructure/runtime_services/`
- Fluxo final de composicao: `routers` -> `application/services` -> `infrastructure/adapters` -> `runtime_modules` + `repositories`.

## Limpeza de artefatos

- [x] Logs temporarios e dumps de execucao removidos do versionamento (`Backend/logs/import_jobs`, `tmp/`, `Frontend/app/tmp/`, `Frontend/app/test-results/`).
- [x] `.gitignore` atualizado para bloquear reentrada de artefatos gerados localmente.

## Hardening final (2026-03-02)

- [x] `Backend/infrastructure/runtime_modules` sem `crud_module`/`crud_users_module`.
- [x] `Backend/infrastructure/runtime_modules/limit_module.py` sem fallback `except TypeError`.
- [x] `IAGenerationService` e `LimitService` com porta obrigatoria no construtor (sem fallback interno de adapter).
- [x] `Backend/routers/auth_utils.py` com dependencias explicitas (`security_workflow` e `user_repository_factory`).
- [x] `Backend/tasks.py` sem `create_engine`, `sessionmaker` e `db.query`.
- [x] `Backend/infrastructure/runtime_modules/file_processing_module.py` sem query direta de `CatalogImportFile`.
