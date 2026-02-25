# Migração OOP - Progresso Real

## Percentual consolidado

- Estrutura OOP (modos, selector, dispatcher, contracts, testes): `100%`
- Integração de rotas críticas com a estrutura OOP: `100%`
- Migração de lógica de negócio para use cases (sem delegar para legado): `20%`
- Migração geral (estrutura + lógica): `55%`

## O que já está pronto

- `APP_MODE` (`legacy`, `oop`, `shadow`) funcionando.
- `PipelineSelector` com comparação em shadow mode.
- `PipelineDispatcher` unificado (inline/thread/background).
- Orquestradores de:
  - importação de catálogo
  - enriquecimento web
- Testes de infraestrutura da migração:
  - selector/app mode
  - dispatcher
  - orchestrators
  - use cases base

## O que ainda falta (para 100%)

1. Tirar dependência de delegação nos use cases:
   - `CatalogImportProcessingUseCase` ainda delega para executor legado.
   - `WebEnrichmentProcessingUseCase` ainda delega para executor legado.
2. Mover regras centrais do `routers/produtos.py` para camadas OO:
   - parsing/normalização por tipo de arquivo
   - pós-validação e scoring de qualidade
   - persistência e resumo final de importação
3. Mover regras centrais do `routers/web_enrichment.py` para camadas OO:
   - seleção/filtro de fontes
   - merge de campos e auditoria de alterações
   - tratamento de fallback/API em serviços dedicados
4. Deixar `legacy` como fallback permanente para comparação e rollback seguro.

## Próximo bloco recomendado

1. Implementar `CatalogImportProcessingUseCase` real (sem delegação).
2. Extrair etapa de persistência/resumo para `application/services`.
3. Ligar esse fluxo no modo `oop` e validar em `shadow`.
4. Repetir o mesmo padrão para enriquecimento web.

