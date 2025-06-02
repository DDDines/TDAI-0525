// Frontend/app/src/services/productTypeService.js
import apiClient from './apiClient'; // Importa a instância centralizada do Axios

// A baseURL (ex: /api/v1) já está configurada no apiClient
// Os paths dos endpoints aqui são relativos a essa baseURL.
const RESOURCE_URL = '/product-types';

const productTypeService = {
  async getProductTypes(params = {}) {
    // A URL completa será: baseURL + /product-types (ou /product-types/ se o endpoint no backend tiver)
    // O endpoint GET /product-types/ no backend está sem barra final na definição do router,
    // mas o FastAPI geralmente trata ambos. Vamos manter sem a barra para consistência com getProductTypeDetails.
    const response = await apiClient.get(`${RESOURCE_URL}`, { params }); // Removida barra final aqui também por consistência
    return response.data;
  },

  async getProductTypeDetails(typeIdOrKey) {
    // CORREÇÃO: Remover a barra final para corresponder à definição do endpoint FastAPI
    // O endpoint no backend é /product-types/{type_id_or_key}
    const response = await apiClient.get(`${RESOURCE_URL}/${typeIdOrKey}`); // ANTES: `${RESOURCE_URL}/${typeIdOrKey}/`
    return response.data;
  },

  async createProductType(productTypeData) {
    // O endpoint POST /product-types/ no backend está com barra final na definição do router
    // mas FastAPI pode ser flexível. Para ser exato com a definição do router:
    const response = await apiClient.post(`${RESOURCE_URL}/`, productTypeData);
    return response.data;
  },

  async updateProductType(typeId, productTypeData) {
    // O endpoint PUT /product-types/{type_id} no backend está sem barra final
    const response = await apiClient.put(`${RESOURCE_URL}/${typeId}`, productTypeData);
    return response.data;
  },

  async deleteProductType(typeId) {
    // O endpoint DELETE /product-types/{type_id} no backend está sem barra final
    const response = await apiClient.delete(`${RESOURCE_URL}/${typeId}`);
    return response.data;
  },

  async addAttributeToType(typeId, attributeData) {
    // O endpoint POST /{type_id}/attributes/ no backend está com barra final
    const response = await apiClient.post(`${RESOURCE_URL}/${typeId}/attributes/`, attributeData);
    return response.data;
  },

  async updateAttributeInType(typeId, attributeId, attributeData) {
    // O endpoint PUT /{type_id}/attributes/{attribute_id} no backend está sem barra final
    const response = await apiClient.put(`${RESOURCE_URL}/${typeId}/attributes/${attributeId}`, attributeData);
    return response.data;
  },

  async removeAttributeFromType(typeId, attributeId) {
    // O endpoint DELETE /{type_id}/attributes/{attribute_id} no backend está sem barra final
    const response = await apiClient.delete(`${RESOURCE_URL}/${typeId}/attributes/${attributeId}`);
    return response.data;
  }
};

export default productTypeService;