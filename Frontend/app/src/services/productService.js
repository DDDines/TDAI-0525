// Frontend/app/src/services/productService.js
import axios from 'axios';

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
    console.log('API Response in productService (getProdutos):', response.data);
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
    console.log('API Response in productService (getProdutoById):', response.data);
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

export default {
  getProdutos,
  getProdutoById,
  createProduto,
  updateProduto,
  deleteProduto,
  gerarTitulosProduto,
  gerarDescricaoProduto,
};