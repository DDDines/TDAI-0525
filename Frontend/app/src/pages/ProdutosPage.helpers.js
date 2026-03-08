/**
 * Module produtos page helpers.
 *
 * Centralizes pure helpers shared by ProdutosPage and its tests.
 */
import productService from '../services/productService';

export async function noopGenerationHandler() {}

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
