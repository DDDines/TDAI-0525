// Frontend/app/src/services/productService.js
import axios from 'axios';
import logger from '../utils/logger';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  }
});

apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, error => {
  return Promise.reject(error);
});

export const getProdutos = async (params = {}) => {
  try {
    // ADICIONADA BARRA FINAL AQUI
    const response = await apiClient.get('/produtos/', { params });
    logger.log('API Response in productService (getProdutos):', response.data);
    return response.data;
  } catch (error) {
    console.error('Error fetching produtos:', error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to fetch produtos');
  }
};

export const getProdutoById = async (produtoId) => {
  try {
    // ADICIONADA BARRA FINAL AQUI
    const response = await apiClient.get(`/produtos/${produtoId}/`);
    logger.log('API Response in productService (getProdutoById):', response.data);
    return response.data;
  } catch (error) {
    console.error(`Error fetching produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error(`Failed to fetch produto ${produtoId}`);
  }
};

export const createProduto = async (produtoData) => {
  try {
    // ADICIONADA BARRA FINAL AQUI
    const response = await apiClient.post('/produtos/', produtoData);
    return response.data;
  } catch (error) {
    console.error('Error creating produto:', error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to create produto');
  }
};

export const updateProduto = async (produtoId, produtoUpdateData) => {
  try {
    // ADICIONADA BARRA FINAL AQUI
    const response = await apiClient.put(`/produtos/${produtoId}/`, produtoUpdateData);
    return response.data;
  } catch (error) {
    console.error(`Error updating produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error(`Failed to update produto ${produtoId}`);
  }
};

export const deleteProduto = async (produtoId) => {
  try {
    // ADICIONADA BARRA FINAL AQUI
    const response = await apiClient.delete(`/produtos/${produtoId}/`);
    return response.data;
  } catch (error) {
    console.error(`Error deleting produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error(`Failed to delete produto ${produtoId}`);
  }
};

export const gerarTitulosProduto = async (produtoId) => {
  try {
    // Mantendo consistência com a barra final se o router de geração também a usar
    // Verifique o prefixo do router 'generation.py'. Se for /geracao, então:
    const response = await apiClient.post(`/geracao/titulos/openai/${produtoId}/`); // Assumindo barra final
    return response.data;
  } catch (error) {
    console.error(`Error generating titles for produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to generate titles');
  }
};

export const gerarDescricaoProduto = async (produtoId) => {
  try {
    const response = await apiClient.post(`/geracao/descricao/openai/${produtoId}/`); // Assumindo barra final
    return response.data;
  } catch (error) {
    console.error(`Error generating description for produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to generate description');
  }
};

// --- NOVAS FUNÇÕES PARA GEMINI ---
export const gerarTitulosGemini = async (produtoId) => {
  try {
    const response = await apiClient.post(`/geracao/titulos/gemini/${produtoId}/`);
    return response.data;
  } catch (error) {
    console.error(`Erro ao gerar titulos com Gemini para produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao gerar titulos com Gemini');
  }
};

export const gerarDescricaoGemini = async (produtoId) => {
  try {
    const response = await apiClient.post(`/geracao/descricao/gemini/${produtoId}/`);
    return response.data;
  } catch (error) {
    console.error(`Erro ao gerar descricao com Gemini para produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao gerar descricao com Gemini');
  }
};

export const iniciarEnriquecimentoWebProduto = async (produtoId, termosBuscaOverride = null) => {
  try {
    let endpoint = `/enriquecimento-web/produto/${produtoId}/`;
    if (termosBuscaOverride) {
      endpoint += `?termos_busca_override=${encodeURIComponent(termosBuscaOverride)}`;
    }
    // O endpoint é POST e espera uma resposta 202 Accepted com uma mensagem.
    const response = await apiClient.post(endpoint);
    return response.data; // Geralmente { "message": "Processo ... iniciado..." }
  } catch (error) {
    console.error(`Error starting web enrichment for produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to start web enrichment process');
  }
};

export const batchDeleteProdutos = async (produtoIds) => {
  try {
    // O endpoint do backend é POST e espera a lista de IDs no corpo da requisição
    const response = await apiClient.post('/produtos/batch-delete/', produtoIds);
    return response.data;
  } catch (error) {
    console.error('Erro ao apagar produtos em lote:', error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao apagar produtos em lote');
  }
};

// --- FUNÇÃO ADICIONADA ---
export const getAtributoSugestions = async (produtoId) => {
  try {
    // O endpoint no backend é: POST /api/v1/geracao/sugerir-atributos-gemini/{produto_id}
    const response = await apiClient.post(`/geracao/sugerir-atributos-gemini/${produtoId}`);
    return response.data; // Deve retornar um objeto schemas.SugestoesAtributosResponse
  } catch (error) {
    console.error(`Erro ao buscar sugestões de atributos para produto ${produtoId}:`, error.response?.data || error.message);
    // Lança o erro para que o componente que o chamou possa tratá-lo
    throw error.response?.data || new Error('Falha ao buscar sugestões de atributos da IA.');
  }
};
// --- FIM DA FUNÇÃO ADICIONADA ---

// Alias para o modal que usa este nome
export const sugerirAtributosGemini = getAtributoSugestions;


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
  getAtributoSugestions,
  sugerirAtributosGemini,
};
