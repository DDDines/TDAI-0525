// Frontend/app/src/services/productService.js
// Importa a instância centralizada do Axios do apiClient.js
import apiClient from './apiClient';

export const getProdutos = async (params = {}) => {
  try {
    const response = await apiClient.get('/produtos', { params }); // Endpoint sem barra final
    console.log('API Response in productService (getProdutos):', response.data);
    return response.data;
  } catch (error) {
    console.error('Error fetching produtos:', error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to fetch produtos');
  }
};

export const getProdutoById = async (produtoId) => {
  try {
    const response = await apiClient.get(`/produtos/${produtoId}`); // Endpoint sem barra final
    console.log('API Response in productService (getProdutoById):', response.data);
    return response.data;
  } catch (error) {
    console.error(`Error fetching produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error(`Failed to fetch produto ${produtoId}`);
  }
};

export const createProduto = async (produtoData) => {
  try {
    const response = await apiClient.post('/produtos', produtoData); // Endpoint sem barra final
    return response.data;
  } catch (error) {
    console.error('Error creating produto:', error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to create produto');
  }
};

export const updateProduto = async (produtoId, produtoUpdateData) => {
  try {
    const response = await apiClient.put(`/produtos/${produtoId}`, produtoUpdateData); // Endpoint sem barra final
    return response.data;
  } catch (error) {
    console.error(`Error updating produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error(`Failed to update produto ${produtoId}`);
  }
};

export const deleteProduto = async (produtoId) => {
  try {
    const response = await apiClient.delete(`/produtos/${produtoId}`); // Endpoint sem barra final
    return response.data;
  } catch (error) {
    console.error(`Error deleting produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error(`Failed to delete produto ${produtoId}`);
  }
};

// Nova função para iniciar o enriquecimento web (anteriormente enrichProductWeb)
export const iniciarEnriquecimentoWebProduto = async (produtoId, termosBuscaOverride = null) => {
  try {
    // Endpoint corrigido: /enriquecimento-web/produto/{produto_id}
    let endpoint = `/enriquecimento-web/produto/${produtoId}`; 
    const params = termosBuscaOverride ? { termos_busca_override: termosBuscaOverride } : {};
    // POST request com payload null e parâmetros na query string
    const response = await apiClient.post(endpoint, null, { params });
    return response.data; // Geralmente { "message": "Processo ... iniciado..." }
  } catch (error) {
    console.error(`Error starting web enrichment for produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to start web enrichment process');
  }
};

// Função para gerar títulos (anteriormente generateProductTitles)
export const gerarTitulosProduto = async (produtoId, config = {}) => {
  try {
    // Endpoint corrigido: /geracao-ia/titulo/{produto_id}
    const response = await apiClient.post(`/geracao-ia/titulo/${produtoId}`, config); 
    return response.data;
  } catch (error) {
    console.error(`Error generating titles for produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to generate titles');
  }
};

// Função para gerar descrição (anteriormente generateProductDescription)
export const gerarDescricaoProduto = async (produtoId, config = {}) => {
  try {
    // Endpoint corrigido: /geracao-ia/descricao/{produto_id}
    const response = await apiClient.post(`/geracao-ia/descricao/${produtoId}`, config);
    return response.data;
  } catch (error) {
    console.error(`Error generating description for produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to generate description');
  }
};

// Novo: Função para deleção em lote (exemplo, se o backend tiver este endpoint)
export const batchDeleteProdutos = async (produtoIds) => {
  try {
    // Supondo que o backend espera um corpo JSON com uma lista de IDs
    const response = await apiClient.post('/produtos/batch-delete', { produto_ids: produtoIds });
    return response.data;
  } catch (error) {
    console.error('Error batch deleting produtos:', error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to batch delete products');
  }
};

// REMOVIDO: Não há default export. Todas as funções são exportadas como named exports acima.