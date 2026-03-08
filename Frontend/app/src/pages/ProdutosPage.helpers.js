/**
 * Module produtos page helpers.
 *
 * Centralizes pure helpers shared by ProdutosPage and its tests.
 */
import productService from '../services/productService';

export async function noopGenerationHandler() {}

export function normalizeProductListPayload(data) {
  return {
    items: Array.isArray(data?.items) ? data.items : [],
    total_items: typeof data?.total_items === 'number' ? data.total_items : 0,
  };
}

export function resolveGenerationHandler(contentType, showAiFeatures, service = productService) {
  return (
    showAiFeatures
      ? {
          titulo: service.gerarTitulosProduto,
          descricao: service.gerarDescricaoProduto,
        }
      : {
          titulo: service.gerarTitulosProdutoModoBasico,
          descricao: service.gerarDescricaoProdutoModoBasico,
        }
  )[contentType] ?? noopGenerationHandler;
}
