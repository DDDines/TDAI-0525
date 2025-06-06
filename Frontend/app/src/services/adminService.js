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

  // Você pode adicionar outras funções de admin aqui no futuro, como:
  // async getUsoIaPorPlano() { ... }
  // async getUserActivity() { ... }
};

export default adminService;
