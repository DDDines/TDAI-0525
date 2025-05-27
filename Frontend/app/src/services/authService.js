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

// NOVO: Função para buscar o histórico de uso da IA do usuário logado
export const getMeuHistoricoUsoIA = async (params = {}) => {
  // params pode incluir skip e limit para paginação
  // O backend em routers/uso_ia.py para /me/ retorna List[schemas.UsoIA]
  // Não retorna total_items por padrão, então a paginação será simples (apenas próxima/anterior baseada no número de itens retornados)
  // ou precisaremos ajustar o backend para retornar total_items para /uso-ia/me/ também.
  try {
    const response = await apiClient.get('/uso-ia/me/', { params });
    // Se o backend for ajustado para retornar um objeto com items e total_items:
    // return response.data; 
    // Por agora, assumindo que retorna uma lista diretamente:
    return response.data; // Espera-se List[schemas.UsoIA]
  } catch (error) {
    console.error('Error fetching AI usage history:', error.response?.data || error.message);
    throw error.response?.data || new Error('Failed to fetch AI usage history');
  }
};


export default {
  getCurrentUser,
  updateCurrentUser,
  changePassword,
  getTotalCounts,
  getMeuHistoricoUsoIA, // Adicionar a nova função aos exports
};