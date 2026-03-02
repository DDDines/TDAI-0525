/**
 * Module historico service.
 *
 * Defines responsibilities and integration points for services.
 */

import apiClient from './apiClient';

async function getHistorico(


  params = {}) {
    const response = await apiClient.get(`${RESOURCE_URL}/`, { params });
    return response.data;
  }
const RESOURCE_URL = '/historico';export { getHistorico };

export default {
  getHistorico
};