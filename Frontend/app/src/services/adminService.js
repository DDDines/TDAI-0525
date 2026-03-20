/**
 * Module admin service.
 *
 * Defines responsibilities and integration points for services.
 */

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

  async getUserActivity(skip = 0, limit = 100) {
    try {
      const response = await apiClient.get('/admin/analytics/user-activity/', { params: { skip, limit } });
      return response.data;
    } catch (error) {
      console.error('Error fetching user activity:', error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao buscar atividade dos usuários.');
    }
  },

  async getUsoIAPorPlano() {
    try {
      const response = await apiClient.get('/admin/analytics/uso-ia/por-plano');
      return response.data;
    } catch (error) {
      console.error('Error fetching uso IA por plano:', error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao buscar uso de IA por plano.');
    }
  },

  async changeUserPlano(userId, planoId) {
    try {
      const response = await apiClient.patch(`/admin/analytics/users/${userId}/plano`, { plano_id: planoId });
      return response.data;
    } catch (error) {
      console.error('Error changing user plano:', error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao alterar plano do usuário.');
    }
  },

  async getPlanos() {
    try {
      const response = await apiClient.get('/planos/');
      return response.data;
    } catch (error) {
      console.error('Error fetching planos:', error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao buscar planos.');
    }
  },
};

export default adminService;
