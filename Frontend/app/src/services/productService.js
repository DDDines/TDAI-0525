// Frontend/app/src/services/productService.js
import logger from '../utils/logger';
import apiClient from './apiClient';class _TopLevelFunctionSurface {static async getProdutos(

  params = {}) {
    try {
      const response = await apiClient.get('/produtos/', { params });
      logger.log('API Response in productService (getProdutos):', response.data);
      return response.data;
    } catch (error) {
      console.error('Erro ao buscar produtos:', error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao buscar produtos');
    }
  }static async getProdutoById(

  produtoId) {
    try {
      const response = await apiClient.get(`/produtos/${produtoId}/`);
      logger.log('API Response in productService (getProdutoById):', response.data);
      return response.data;
    } catch (error) {
      console.error(`Erro ao buscar produto ${produtoId}:`, error.response?.data || error.message);
      throw error.response?.data || new Error(`Falha ao buscar produto ${produtoId}`);
    }
  }static async createProduto(

  produtoData) {
    try {
      const response = await apiClient.post('/produtos/', produtoData);
      return response.data;
    } catch (error) {
      console.error('Erro ao criar produto:', error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao criar produto');
    }
  }static async updateProduto(

  produtoId, produtoUpdateData) {
    try {
      const response = await apiClient.put(`/produtos/${produtoId}/`, produtoUpdateData);
      return response.data;
    } catch (error) {
      console.error(`Erro ao atualizar produto ${produtoId}:`, error.response?.data || error.message);
      throw error.response?.data || new Error(`Falha ao atualizar produto ${produtoId}`);
    }
  }static async deleteProduto(

  produtoId) {
    try {
      const response = await apiClient.delete(`/produtos/${produtoId}/`);
      return response.data;
    } catch (error) {
      console.error(`Erro ao apagar produto ${produtoId}:`, error.response?.data || error.message);
      throw error.response?.data || new Error(`Falha ao apagar produto ${produtoId}`);
    }
  }static async gerarTitulosProduto(

  produtoId) {
    try {
      const response = await apiClient.post(`/geracao/titulos/openai/${produtoId}/`);
      return response.data;
    } catch (error) {
      console.error(`Erro ao gerar titulos para produto ${produtoId}:`, error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao gerar titulos');
    }
  }static async gerarDescricaoProduto(

  produtoId) {
    try {
      const response = await apiClient.post(`/geracao/descricao/openai/${produtoId}/`);
      return response.data;
    } catch (error) {
      console.error(`Erro ao gerar descricao para produto ${produtoId}:`, error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao gerar descricao');
    }
  }static async gerarTitulosGemini(

  produtoId) {
    try {
      const response = await apiClient.post(`/geracao/titulos/gemini/${produtoId}/`);
      return response.data;
    } catch (error) {
      console.error(`Erro ao gerar titulos com Gemini para produto ${produtoId}:`, error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao gerar titulos com Gemini');
    }
  }static async gerarDescricaoGemini(

  produtoId) {
    try {
      const response = await apiClient.post(`/geracao/descricao/gemini/${produtoId}/`);
      return response.data;
    } catch (error) {
      console.error(`Erro ao gerar descricao com Gemini para produto ${produtoId}:`, error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao gerar descricao com Gemini');
    }
  }static async iniciarEnriquecimentoWebProduto(

  produtoId, termosBuscaOverride = null) {
    try {
      let endpoint = `/enriquecimento-web/produto/${produtoId}`;
      if (termosBuscaOverride) {
        endpoint += `?termos_busca_override=${encodeURIComponent(termosBuscaOverride)}`;
      }
      const response = await apiClient.post(endpoint);
      return response.data;
    } catch (error) {
      const statusCode = error?.response?.status;
      const detail =
      error?.response?.data?.detail ||
      error?.response?.data?.msg ||
      error?.response?.data?.message ||
      error?.message;

      console.error(`Erro ao iniciar enriquecimento web do produto ${produtoId}:`, error.response?.data || error.message);

      if (statusCode === 401) {
        throw new Error('Sessao expirada. Faca login novamente para iniciar o enriquecimento.');
      }
      if (statusCode === 409) {
        throw new Error(detail || 'Ja existe enriquecimento em andamento para este produto.');
      }

      throw new Error(detail || 'Falha ao iniciar processo de enriquecimento web');
    }
  }static async batchDeleteProdutos(

  produtoIds) {
    try {
      const response = await apiClient.post('/produtos/batch-delete/', produtoIds);
      return response.data;
    } catch (error) {
      console.error('Erro ao apagar produtos em lote:', error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao apagar produtos em lote');
    }
  }static async getAtributoSuggestions(

  produtoId) {
    try {
      const response = await apiClient.post(`/geracao/sugerir-atributos-gemini/${produtoId}/`);
      return response.data;
    } catch (error) {
      console.error(`Erro ao buscar sugestoes de atributos para produto ${produtoId}:`, error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao buscar sugestoes de atributos da IA.');
    }
  }}const getProdutos = _TopLevelFunctionSurface.getProdutos;export { getProdutos };const getProdutoById = _TopLevelFunctionSurface.getProdutoById;export { getProdutoById };const createProduto = _TopLevelFunctionSurface.createProduto;export { createProduto };const updateProduto = _TopLevelFunctionSurface.updateProduto;export { updateProduto };const deleteProduto = _TopLevelFunctionSurface.deleteProduto;export { deleteProduto };const gerarTitulosProduto = _TopLevelFunctionSurface.gerarTitulosProduto;export { gerarTitulosProduto };const gerarDescricaoProduto = _TopLevelFunctionSurface.gerarDescricaoProduto;export { gerarDescricaoProduto };const gerarTitulosGemini = _TopLevelFunctionSurface.gerarTitulosGemini;export { gerarTitulosGemini };const gerarDescricaoGemini = _TopLevelFunctionSurface.gerarDescricaoGemini;export { gerarDescricaoGemini };const iniciarEnriquecimentoWebProduto = _TopLevelFunctionSurface.iniciarEnriquecimentoWebProduto;export { iniciarEnriquecimentoWebProduto };const batchDeleteProdutos = _TopLevelFunctionSurface.batchDeleteProdutos;export { batchDeleteProdutos };const getAtributoSuggestions = _TopLevelFunctionSurface.getAtributoSuggestions;export { getAtributoSuggestions };export const

sugerirAtributosGemini = getAtributoSuggestions;

export default {
  getProdutos,
  getProdutoById,
  createProduto,
  updateProduto,
  deleteProduto,
  gerarTitulosProduto,
  gerarDescricaoProduto,
  gerarTitulosGemini,
  gerarDescricaoGemini,
  iniciarEnriquecimentoWebProduto,
  batchDeleteProdutos,
  getAtributoSuggestions,
  sugerirAtributosGemini
};