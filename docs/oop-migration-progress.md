# Migracao OOP - Progresso Real

## Percentual consolidado (atualizado)

- Estrutura OOP (modos, selector, dispatcher, contracts, testes): `100%`
- Integracao das rotas criticas com estrutura OOP: `100%`
- Migracao da logica para use cases/services OO (sem corpo pesado no router): `93%`
- Migracao geral (estrutura + logica): `97%`

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
  - `CatalogImportOutcomeResolver` + `CatalogImportFileStateService` + `CatalogImportAuditWriter`
  - `WebEnrichmentConfigInspector` + `WebEnrichmentQueryPlanner` + `WebEnrichmentStatusResolver`
  - `WebEnrichmentFinalizationService`
  - Cobertura dedicada em testes: `test_catalog_import_components.py` e
    `test_web_enrichment_components.py`.

## O que ainda falta para 100%

1. Separar explicitamente o pipeline de escrita entre `legacy` e `oop`
   (hoje ambos ainda convergem no mesmo `TaskService` para processamento pesado).
2. Reduzir os trechos restantes de sanitizacao/normalizacao ainda acoplados em `routers`
   para componentes `application/services` dedicados.
3. Consolidar comparacao automatica de resultados em `APP_MODE=shadow`
   para detectar regressao funcional entre caminhos.
4. Manter `legacy` como fallback permanente para rollback e comparacao.

## Proximo bloco recomendado

1. Isolar sanitizacao/normalizacao de importacao atualmente em `routers/produtos.py`
   para componente OO reutilizavel.
2. Isolar normalizacao e regras de relevancia restantes de enriquecimento
   atualmente em `routers/web_enrichment.py` para componente OO reutilizavel.
3. Criar comparador de saida em `APP_MODE=shadow` com assert estrutural/log.
4. Congelar baseline legacy + checklist de rollback.
