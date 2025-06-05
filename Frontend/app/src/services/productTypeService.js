// Frontend/app/src/services/productTypeService.js
import apiClient from './apiClient'; // Importa a instância centralizada do Axios

const RESOURCE_URL = '/product-types';

const productTypeService = {
  async getProductTypes(params = {}) {
    const response = await apiClient.get(`${RESOURCE_URL}/`, { params });
    return response.data;
  },

  async getProductTypeDetails(typeIdOrKey) {
    const response = await apiClient.get(`${RESOURCE_URL}/${typeIdOrKey}`);
    return response.data;
  },

  async createProductType(productTypeData) {
    const response = await apiClient.post(`${RESOURCE_URL}/`, productTypeData);
    return response.data;
  },

  async updateProductType(typeId, productTypeData) {
    const response = await apiClient.put(`${RESOURCE_URL}/${typeId}`, productTypeData);
    return response.data;
  },

  async deleteProductType(typeId) {
    const response = await apiClient.delete(`${RESOURCE_URL}/${typeId}`);
    return response.data;
  },

  async addAttributeToType(typeId, attributeData) {
    const response = await apiClient.post(`${RESOURCE_URL}/${typeId}/attributes/`, attributeData);
    return response.data;
  },

  async updateAttributeInType(typeId, attributeId, attributeData) {
    const response = await apiClient.put(`${RESOURCE_URL}/${typeId}/attributes/${attributeId}`, attributeData);
    return response.data;
  },

  async removeAttributeFromType(typeId, attributeId) {
    const response = await apiClient.delete(`${RESOURCE_URL}/${typeId}/attributes/${attributeId}`);
    return response.data;
  },

  // --- NOVA FUNÇÃO ADICIONADA ABAIXO ---
  
  async reorderAttributeInType(typeId, attributeId, direction) {
    // direction deve ser "up" ou "down"
    const response = await apiClient.post(`${RESOURCE_URL}/${typeId}/attributes/${attributeId}/reorder`, { direction });
    return response.data;
  }
};

export default productTypeService;