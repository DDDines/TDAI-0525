# Migracao OOP - Progresso Real

## Visao geral

A base esta funcional e testada, mas ainda em transicao. O objetivo agora e concluir a migracao para OOP completo no backend com compatibilidade de API durante a janela de transicao.
No estado atual, a selecao de pipeline em runtime esta em modo OOP-only: `APP_MODE=legacy|shadow` e normalizado para `oop` com warning de compatibilidade.

## Checklist por dominio

### Fase 0 - Guardrails de arquitetura

- [x] Teste de arquitetura criado: `Backend/tests/test_architecture_boundaries.py`.
- [x] Regra: `Backend/application/**` nao pode importar `Backend/services/**`.
- [x] Regra: `Backend/application/**` nao pode importar `Backend/routers/**`.
- [x] Regra: `Backend/application/services/**` nao pode definir `__getattr__` em adapters/facades.
- [x] Regra: `Backend/application/services/**` nao pode chamar metodo privado de objeto externo (`obj._algo()`).

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
- [x] Bridges de legado mantidos somente para compatibilidade em `Backend/infrastructure/legacy/`.

### Fase 4 - Orquestracao e desacoplamento de borda

- [x] Import cruzado removido: `Backend/routers/fornecedores.py` nao depende mais de `Backend/routers/produtos.py`.
- [x] Runners unificados em implementacao OOP unica; aliases `execute_legacy`/`execute_oop` existem apenas para compatibilidade de assinatura.
- [x] Garantia de teste: `APP_MODE=oop` executa apenas executor OOP selecionado pelo orquestrador.
- [x] Fluxo real validado com `APP_MODE=oop` + `STRICT_OOP_NO_LEGACY=1` para endpoint de preview de catalogo sem bridge legado no caminho OOP.

### Fase 5 - Limpeza final

- [x] Marcar oficialmente `*_legacy_service` como deprecated em toda a base (proxy unificado em `Backend/core/deprecation.py`).
- [x] Remover pipelines legados de orquestracao (`Backend/legacy/pipelines/`) sem referencias restantes em runtime/testes.
- [x] Remover bridges de transicao em `Backend/infrastructure/legacy/`.
- [ ] Remover facades/proxies de transicao apos prazo de compatibilidade.
- [x] Atualizar documentacao final de arquitetura e matriz de conclusao.

## Criterios objetivos de fechamento

- [x] Zero import de `Backend/services` dentro de `Backend/application/services`.
- [x] Zero uso de `__getattr__` em adapters da camada de aplicacao.
- [x] Zero chamada a metodo privado de objeto externo em `Backend/application/services`.
- [x] Zero import de `Backend/routers` em `Backend/application`.
- [x] Fluxos legacy isolados por bridge/proxy temporario documentado.
- [x] Acoplamento de testes a internals de `Backend/services` reduzido para shim central em `Backend/testing/runtime_apis.py` (sem imports privados diretos espalhados).

## Matriz de isolamento (transicao)

| Fluxo | Modulo OOP principal | Dependencia direta de `Backend/services` na aplicacao |
|---|---|---|
| Importacao de catalogo (arquivo) | `Backend/application/services/file_processing/` | Nao |
| Enriquecimento web | `Backend/application/services/web_data_extractor/` | Nao |
| IA generation | `Backend/application/services/ia_generation_facade.py` + `Backend/application/services/ports.py` | Nao |
| Limites e creditos | `Backend/application/services/limit_service_facade.py` + `Backend/application/services/ports.py` | Nao |
| Validator crew | `Backend/application/services/validator_crew_facade.py` + `Backend/application/services/ports.py` | Nao |

## Pontos de transicao planejados

- Adapters OOP padrao concentrados em `Backend/infrastructure/adapters/`.
- Proxies de deprecacao de `*_legacy_service` centralizados em `Backend/core/deprecation.py`.
- Guard opcional de execucao estrita: `STRICT_OOP_NO_LEGACY=1` bloqueia acesso legado quando `APP_MODE=oop`.
- Remocao fisica restante de facades/proxies/shims: apos 2026-04-30.
