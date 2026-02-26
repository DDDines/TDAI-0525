# Migracao OOP - Progresso Real

## Percentual consolidado (atualizado)

- Estrutura OOP (modos, selector, dispatcher, contracts, testes): `100%`
- Integracao das rotas criticas com estrutura OOP: `100%`
- Migracao da logica para use cases/services OO (sem corpo pesado no router): `68%`
- Migracao geral (estrutura + logica): `82%`

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

## O que ainda falta para 100%

1. Fazer `APP_MODE=oop` executar fluxo OO dedicado (hoje legacy/oop apontam para o mesmo executor delegado).
2. Quebrar `catalog_import_task_service` em servicos menores (parser, quality gate, persistence summary).
3. Quebrar `web_enrichment_task_service` em servicos menores (source selection, extraction flow, merge/audit).
4. Manter `legacy` como fallback permanente para rollback e comparacao.

## Proximo bloco recomendado

1. Separar `catalog_import_task_service` em componentes OO menores e testaveis.
2. Separar `web_enrichment_task_service` em componentes OO menores e testaveis.
3. Ligar orchestrators para usar executor OOP dedicado no `APP_MODE=oop`.
4. Validar `shadow` comparando payload/resultado de legacy vs OOP.
