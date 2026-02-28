# Migracao OOP - Progresso Real

## Visao geral

A migracao OOP do backend foi concluida.
O runtime opera em modo OOP-only (`APP_MODE=oop`) e a camada `Backend/services` foi removida do codigo produtivo.

## Checklist por dominio

### Fase 0 - Guardrails de arquitetura

- [x] Teste de arquitetura criado: `Backend/tests/test_architecture_boundaries.py`.
- [x] Regra: `Backend/application/**` nao pode importar `Backend/services/**`.
- [x] Regra: `Backend/application/**` nao pode importar `Backend/routers/**`.
- [x] Regra: `Backend/application/services/**` nao pode definir `__getattr__` em adapters/facades.
- [x] Regra: `Backend/application/services/**` nao pode chamar metodo privado de objeto externo (`obj._algo()`).
- [x] Regra: codigo backend nao pode importar `Backend.services`.

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
- [x] `FileProcessingFacade` migrado para adapter explicito sem fallback dinamico.
- [x] `CatalogExtractionService.processar_linha_padronizada` passou a usar metodo publico.
- [x] API publica adicionada no legado: `processar_linha_padronizada(...)`.
- [x] Delegacao de todas as funcoes publicas do modulo legado com warning de deprecacao centralizado.

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
- [x] `WebDataExtractorFacade` migrado para adapter explicito sem fallback dinamico.
- [x] Chamada privada removida em componente (`_normalizar...` -> metodo publico).
- [x] API publica adicionada no legado: `normalizar_dados_de_metadados(...)`.
- [x] Encapsulamento de estado global (cache/semaphore/flag Playwright) em runtime injetavel dedicado, com teste de isolamento.

### Fase 3 - Onda IA / Limit / Validator

- [x] Contratos internos adicionados em `Backend/application/services/ports.py`:
  - `IAGenerationPort`
  - `LimitPort`
  - `ValidationPort`
- [x] `IAGenerationFacade` sem `__getattr__`.
- [x] `LimitServiceFacade` sem `__getattr__`.
- [x] `ValidatorCrewFacade` sem import direto de `Backend.services`.
- [x] Defaults OOP migrados para adapters explicitos em `Backend/infrastructure/adapters/` (sem bridge legado no caminho padrao OOP).
- [x] Bridges legados removidos de `Backend/infrastructure/legacy/`.

### Fase 4 - Orquestracao e desacoplamento de borda

- [x] Import cruzado removido: `Backend/routers/fornecedores.py` nao depende mais de `Backend/routers/produtos.py`.
- [x] Runners unificados em implementacao OOP unica; execucao via `execute` (com alias `execute_oop` apenas para compatibilidade temporaria).
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
- [x] Runtime providers (`Backend/infrastructure/runtime/*`) desacoplados de `Backend.services`.
- [x] Atualizar documentacao final de arquitetura e matriz de conclusao.

## Criterios objetivos de fechamento

- [x] Zero import de `Backend/services` dentro de `Backend/application/services`.
- [x] Zero uso de `__getattr__` em adapters da camada de aplicacao.
- [x] Zero chamada a metodo privado de objeto externo em `Backend/application/services`.
- [x] Zero import de `Backend/routers` em `Backend/application`.
- [x] Sem bridges/proxies legados ativos em runtime de aplicacao.
- [x] Zero import de `Backend/services` em `Backend/infrastructure/runtime`.
- [x] Zero import de `Backend/services` em todo backend (incluindo runtime e testes de backend).

## Matriz de isolamento

| Fluxo | Modulo OOP principal | Dependencia direta de `Backend/services` na aplicacao |
|---|---|---|
| Importacao de catalogo (arquivo) | `Backend/application/services/file_processing/` | Nao |
| Enriquecimento web | `Backend/application/services/web_data_extractor/` | Nao |
| IA generation | `Backend/application/services/ia_generation_facade.py` + `Backend/application/services/ports.py` | Nao |
| Limites e creditos | `Backend/application/services/limit_service_facade.py` + `Backend/application/services/ports.py` | Nao |
| Validator crew | `Backend/application/services/validator_crew_facade.py` + `Backend/application/services/ports.py` | Nao |

## Arquitetura final

- Adapters OOP padrao concentrados em `Backend/infrastructure/adapters/`.
- Provedores de runtime concentrados em `Backend/infrastructure/runtime/` consumindo `Backend/infrastructure/runtime_modules/`.
- Implementacoes de dominio/runtime concentradas em `Backend/infrastructure/runtime_modules/`.
