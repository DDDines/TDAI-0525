# Migracao OOP - Progresso Real

## Visao geral

A base esta funcional e testada, mas ainda em transicao. O objetivo agora e concluir a migracao para OOP completo no backend com compatibilidade de API durante a janela de transicao.

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
- [ ] Encapsulamento completo de estado global em runtime injetavel dedicado.

### Fase 3 - Onda IA / Limit / Validator

- [x] Contratos internos adicionados em `Backend/application/services/ports.py`:
  - `IAGenerationPort`
  - `LimitPort`
  - `ValidationPort`
- [x] `IAGenerationFacade` sem `__getattr__`.
- [x] `LimitServiceFacade` sem `__getattr__`.
- [x] `ValidatorCrewFacade` sem import direto de `Backend.services`.
- [x] Bridges de legado centralizados em `Backend/infrastructure/legacy/`.

### Fase 4 - Orquestracao e desacoplamento de borda

- [x] Import cruzado removido: `Backend/routers/fornecedores.py` nao depende mais de `Backend/routers/produtos.py`.
- [x] Runners com implementacoes legacy/oop distintas por dependencia injetada.
- [x] Garantia de teste: `APP_MODE=oop` executa apenas executor OOP selecionado pelo orquestrador.

### Fase 5 - Limpeza final

- [ ] Marcar oficialmente `*_legacy_service` como deprecated em toda a base.
- [ ] Remover bridges/facades de transicao apos prazo de compatibilidade.
- [ ] Atualizar documentacao final de arquitetura e matriz de conclusao.

## Criterios objetivos de fechamento

- [x] Zero import de `Backend/services` dentro de `Backend/application/services`.
- [x] Zero uso de `__getattr__` em adapters da camada de aplicacao.
- [x] Zero chamada a metodo privado de objeto externo em `Backend/application/services`.
- [x] Zero import de `Backend/routers` em `Backend/application`.
- [ ] Fluxos legacy removidos ou isolados apenas em bridge temporaria documentada.
