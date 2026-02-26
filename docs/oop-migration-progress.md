# Migracao OOP - Progresso Real

## Percentual consolidado (atualizado)

- Estrutura OOP (modos, selector, dispatcher, contracts, testes): `100%`
- Integracao das rotas criticas com estrutura OOP: `100%`
- Migracao da logica para use cases (sem pass-through puro): `35%`
- Migracao geral (estrutura + logica): `62%`

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

## O que ainda falta para 100%

1. Remover o corpo principal de processamento dos routers:
   - `Backend/routers/produtos.py::_tarefa_processar_catalogo`
   - `Backend/routers/web_enrichment.py::_tarefa_enriquecer_produto_web`
2. Extrair para services/use cases OO:
   - parsing por formato
   - validacao de qualidade e descarte
   - persistencia de resumo e auditoria
3. Fazer `APP_MODE=oop` executar fluxo totalmente OO (sem executor legado injetado).
4. Manter `legacy` como fallback permanente para rollback e comparacao.

## Proximo bloco recomendado

1. Extrair `_tarefa_processar_catalogo` para `application/services` (primeiro alvo).
2. Deixar router apenas com chamada de caso de uso.
3. Validar `shadow` comparando saida legacy vs OOP.
4. Repetir o mesmo padrao para enriquecimento web.
