# Bugs Priorizados (2026-02-18)

## P0 - Fluxo de Importacao PDF (Fornecedor)
- [x] Finalizacao usava caminho diferente do preview de regiao (sem OCR de regiao).
- [x] BBox normalizada com valores levemente > 1 quebrava recorte.
- [x] Mapping salvo em formato invertido (`campo -> coluna`) nao era normalizado.
- [x] `FAILED` sem diagnostico visivel no frontend.
- [x] Status/result sem campos consistentes (`stats`, `pages_total/total_pages`).
- [x] LLM desligado no processamento em lote para reduzir tempo e variabilidade.

## P1 - Estabilidade e Manutenibilidade
- [x] `Backend/routers/produtos.py` esta com bloco de imports/definicoes duplicado no topo e precisa limpeza estrutural.
- [x] Suite de testes legado esta parcialmente desalinhado com contratos atuais de importacao.
- [x] Endpoint de selecao de regiao para PDFs sinteticos simples ainda diverge da expectativa de alguns testes antigos.

## P1 - Ambiente
- [x] Ambiente local com conflito `numpy`/`pyarrow` (ABI) gera warnings/excecoes de import em alguns contextos.

## P2 - UX e Performance
- [x] Exibir ETA/progresso real de processamento por pagina no wizard.
- [x] Melhorar heuristicas de OCR para reduzir ruido em linhas com poucos caracteres.
- [x] Adicionar opcao explicita no frontend para modo de extracao (Tabela/OCR/IA) por arquivo.
