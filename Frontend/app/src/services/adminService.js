// Frontend/app/src/services/adminService.js
import apiClient from './apiClient';

const adminService = {
  async getTotalCounts() {
    try {
      // O endpoint no backend é /admin/analytics/counts
      // apiClient já tem /api/v1 como baseURL
      const response = await apiClient.get('/admin/analytics/counts');
      return response.data;
    } catch (error) {
      console.error('Error fetching total counts (adminService):', error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao buscar contagens totais.');
    }
  },

  async getProductStatusCounts() {
    try {
      const response = await apiClient.get('/admin/analytics/product-status-counts');
      return response.data;
    } catch (error) {
      console.error('Error fetching product status counts:', error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao buscar contagem de status dos produtos.');
    }
  },

  async getRecentActivities() {
    try {
      const response = await apiClient.get('/admin/analytics/recent-activities');
      return response.data;
    } catch (error) {
      console.error('Error fetching recent activities:', error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao buscar atividades recentes.');
    }
  },

  async getRecentHistorico(limit = 5) {
    try {
      const response = await apiClient.get('/admin/analytics/recent-historico', { params: { limit } });
      return response.data;
    } catch (error) {
      console.error('Error fetching recent historico:', error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao buscar histórico recente.');
    }
  },

  // Você pode adicionar outras funções de admin aqui no futuro, como:
  // async getUsoIaPorPlano() { ... }
  // async getUserActivity() { ... }
};

export default adminService;
