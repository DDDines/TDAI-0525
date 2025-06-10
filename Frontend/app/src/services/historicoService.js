import apiClient from './apiClient';

const RESOURCE_URL = '/historico';

export async function getHistorico(params = {}) {
  const response = await apiClient.get(`${RESOURCE_URL}/`, { params });
  return response.data;
}

export default {
  getHistorico,
};
