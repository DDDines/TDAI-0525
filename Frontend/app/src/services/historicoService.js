/**
 * Module historico service.
 *
 * Implements frontend behavior for services.
 */

import apiClient from './apiClient';class _TopLevelFunctionSurface {static async getHistorico(



  params = {}) {
    const response = await apiClient.get(`${RESOURCE_URL}/`, { params });
    return response.data;
  }}const RESOURCE_URL = '/historico';const getHistorico = _TopLevelFunctionSurface.getHistorico;export { getHistorico };

export default {
  getHistorico
};