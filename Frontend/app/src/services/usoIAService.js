// Frontend/app/src/services/usoIAService.js
import apiClient from './apiClient';

const USO_IA_RESOURCE_URL = '/uso-ia';

const usoIAService = {
  /**
   * Busca o histórico de uso de IA para um produto específico.
   * @param {number} produtoId O ID do produto.
   * @param {object} params Parâmetros de query (skip, limit).
   * @returns {Promise<Array>} Uma promessa que resolve para o histórico de uso de IA.
   */
  async getHistoricoUsoIAPorProduto(produtoId, params = {}) {
    try {
      // Endpoint correto do backend: /api/v1/uso-ia/por-produto/{produto_id}
      const response = await apiClient.get(`${USO_IA_RESOURCE_URL}/por-produto/${produtoId}`, { params });
      return response.data;
    } catch (error) {
      console.error(`Error fetching IA usage history for product ${produtoId}:`, error.response?.data || error.message);
      throw error.response?.data || new Error(`Failed to fetch IA usage history for product ${produtoId}`);
    }
  },

  // Você pode adicionar outras funções relacionadas a uso de IA aqui, como:
  // async getMeuHistoricoUsoIA(params = {}) { /* ... */ }
};

export default usoIAService;