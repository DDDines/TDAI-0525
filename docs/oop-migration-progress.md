# Migracao OOP - Progresso Real

## Percentual consolidado (atualizado)

- Estrutura OOP (modos, selector, dispatcher, contracts, testes): `100%`
- Integracao das rotas criticas com estrutura OOP: `100%`
- Migracao da logica para use cases/services OO (sem corpo pesado no router): `100%`
- Migracao geral (estrutura + logica): `100%`

## O que ja esta pronto

- `APP_MODE` (`legacy`, `oop`, `shadow`) funcional.
- `PipelineSelector` com comparacao em shadow mode.
- `PipelineDispatcher` unificado (inline/thread/background).
- Orquestradores de:
  - importacao de catalogo
  - enriquecimento web
- Use cases com validacao/normalizacao de comando:
  - `CatalogImportProcessingUseCase` agora valida IDs e normaliza mapping/pages/region
  - `WebEnrichmentProcessingUseCase` agora valida IDs e normaliza termo de busca
- Tarefas pesadas extraidas dos routers para camada `application/services`:
  - `Backend/application/services/catalog_import_task_service.py`
  - `Backend/application/services/web_enrichment_task_service.py`
  - Routers agora atuam como delegadores dessas tarefas.
- Rotas criticas agora informam `legacy_executor` e `oop_executor` separados
  nos orquestradores, permitindo diferenciar caminho OOP em `APP_MODE=oop`.
- Tarefas de importacao/enriquecimento agora tambem possuem `TaskService` OO
  (`CatalogImportTaskService` e `WebEnrichmentTaskService`) usados pelos executores.
- Executor OOP agora chama `TaskService` diretamente (sem encadear no executor legacy).
- Use cases e executores OOP agora operam com comandos tipados
  (`CatalogImportFinalizeCommand` e `WebEnrichmentStartCommand`).
- Task services foram quebrados em componentes OO menores para reduzir acoplamento:
  - `CatalogImportIssueTracker` + `CatalogImportQualityAccumulator`
  - `CatalogImportOutcomeResolver` + `CatalogImportFileStateService` + `CatalogImportAuditWriter` + `CatalogImportResultBuilder`
  - `WebEnrichmentConfigInspector` + `WebEnrichmentQueryPlanner` + `WebEnrichmentStatusResolver`
  - `WebEnrichmentFinalizationService`
  - Cobertura dedicada em testes: `test_catalog_import_components.py` e
    `test_web_enrichment_components.py`.
- Sanitizacao/normalizacao remanescente de importacao foi extraida para
  `CatalogImportSanitizationService`.
- Normalizacao textual/campos do enriquecimento web foi extraida para
  `WebEnrichmentNormalizationService`.
- Comparacao automatica de resultados legacy/oop foi adicionada via
  `ShadowResultComparator` com persistencia em `Backend/logs/shadow_compare`.
- Pipelines de execucao agora usam instancias separadas por variante (`legacy`/`oop`)
  nos task services, preservando rollback.

## O que ainda falta para 100%

Concluido para a trilha OOP.
