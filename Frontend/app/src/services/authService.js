// Frontend/app/src/services/authService.js
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

export const getCurrentUser = async () => {
  try {
    const response = await apiClient.get('/users/me/');
    return response.data; 
  } catch (error) {
    console.error('Error fetching current user:', error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to fetch current user data');
  }
};

export const updateCurrentUser = async (userData) => {
  try {
    const response = await apiClient.put('/users/me/', userData);
    return response.data; 
  } catch (error) {
    console.error('Error updating current user:', error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to update user data');
  }
};

export const changePassword = async (passwordData) => {
  try {
    const response = await apiClient.post('/users/me/change-password', passwordData);
    return response.data; 
  } catch (error) {
    console.error('Error changing password:', error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to change password');
  }
};

export const getTotalCounts = async () => {
  try {
    const response = await apiClient.get('/admin/analytics/counts');
    return response.data; 
  } catch (error) {
    console.error('Error fetching total counts:', error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to fetch total counts');
  }
};

export const getMeuHistoricoUsoIA = async (params = {}) => {
  try {
    const response = await apiClient.get('/uso-ia/me/', { params });
    return response.data; 
  } catch (error) {
    console.error('Error fetching AI usage history:', error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to fetch AI usage history');
  }
};

// Função para buscar o histórico de uso da IA para um produto específico
export const getHistoricoUsoIAPorProduto = async (produtoId, params = {}) => {
  // params pode incluir skip e limit, ex: { limit: 1 } para pegar só o mais recente.
  try {
    // O endpoint no backend é /api/v1/uso-ia/produto/{produto_id}/
    const response = await apiClient.get(`/uso-ia/produto/${produtoId}/`, { params });
    return response.data; // Espera-se List[schemas.UsoIA] do backend
  } catch (error) {
    console.error(`Error fetching AI usage history for product ${produtoId}:`, error.response?.data || error.message);
    // Não lançar um novo erro aqui necessariamente, ou o toast pode mostrar "Failed to fetch..."
    // É melhor retornar null ou um objeto de erro para que a página possa lidar com isso.
    // Por agora, vamos deixar lançar, mas o `EnriquecimentoPage` tratará.
    throw error.response?.data || new Error(`Failed to fetch AI usage history for product ${produtoId}`);
  }
};


export default {
  getCurrentUser,
  updateCurrentUser,
  changePassword,
  getTotalCounts,
  getMeuHistoricoUsoIA,
  getHistoricoUsoIAPorProduto, // Garantir que está exportado
};