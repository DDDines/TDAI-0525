// Frontend/app/src/services/fornecedorService.js
import logger from '../utils/logger';
import apiClient from './apiClient';

export const getFornecedores = async (params = {}) => { // params pode incluir skip, limit, termo_busca
  try {
    // O backend agora deve retornar { items: [], total_items: X, limit: Y, skip: Z }
    const response = await apiClient.get('/fornecedores/', { params });
    logger.log('API Response in fornecedorService (getFornecedores):', response.data); // Para depuração
    return response.data; // Retorna o objeto completo
  } catch (error) {
    console.error('Error fetching fornecedores (SERVICE LEVEL):', JSON.stringify(error.response?.data || error.message || error));
    if (error.response && error.response.data) {
      throw error.response.data;
    } else if (error.request) {
      throw new Error('Nenhuma resposta do servidor ao buscar fornecedores.');
    } else {
      throw new Error(error.message || 'Erro ao configurar requisição para buscar fornecedores.');
    }
  }
};

export const getFornecedorById = async (fornecedorId) => {
  try {
    const response = await apiClient.get(`/fornecedores/${fornecedorId}/`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching fornecedor ${fornecedorId} (SERVICE LEVEL):`, JSON.stringify(error.response?.data || error.message || error));
    if (error.response && error.response.data) {
      throw error.response.data;
    } else if (error.request) {
      throw new Error(`Nenhuma resposta do servidor ao buscar fornecedor ${fornecedorId}.`);
    } else {
      throw new Error(error.message || `Erro ao configurar requisição para buscar fornecedor ${fornecedorId}.`);
    }
  }
};

export const createFornecedor = async (fornecedorData) => {
  try {
    const response = await apiClient.post('/fornecedores/', fornecedorData);
    return response.data;
  } catch (error) {
    console.error('Axios error object in createFornecedor (SERVICE LEVEL):', error);
    if (error.response) {
        console.error('Axios error.response.data:', error.response.data);
    }
    if (error.response && error.response.data) {
        throw error.response.data;
    } else {
        throw new Error(error.message || 'Erro ao tentar criar fornecedor. Verifique o console do serviço.');
    }
  }
};

export const updateFornecedor = async (fornecedorId, fornecedorUpdateData) => {
  try {
    const response = await apiClient.put(`/fornecedores/${fornecedorId}/`, fornecedorUpdateData);
    return response.data;
  } catch (error) {
    console.error(`Error updating fornecedor ${fornecedorId} (SERVICE LEVEL):`, JSON.stringify(error.response?.data || error.message || error));
    if (error.response && error.response.data) {
      throw error.response.data;
    } else if (error.request) {
      throw new Error(`Nenhuma resposta do servidor ao tentar atualizar fornecedor ${fornecedorId}.`);
    } else {
      throw new Error(error.message || `Erro ao configurar requisição para atualizar fornecedor ${fornecedorId}.`);
    }
  }
};

export const deleteFornecedor = async (fornecedorId) => {
  try {
    const response = await apiClient.delete(`/fornecedores/${fornecedorId}/`);
    return response.data;
  } catch (error) {
    console.error(`Error deleting fornecedor ${fornecedorId} (SERVICE LEVEL):`, JSON.stringify(error.response?.data || error.message || error));
    if (error.response && error.response.data) {
      throw error.response.data;
    } else if (error.request) {
      throw new Error(`Nenhuma resposta do servidor ao tentar deletar fornecedor ${fornecedorId}.`);
    } else {
      throw new Error(error.message || `Erro ao configurar requisição para deletar fornecedor ${fornecedorId}.`);
    }
  }
};

export default {
  getFornecedores,
  getFornecedorById,
  createFornecedor,
  updateFornecedor,
  deleteFornecedor,
};
