/**
 * External credentials service.
 */

import apiClient from './apiClient';

async function getOverview() {
  try {
    const response = await apiClient.get('/credenciais/overview');
    return response.data;
  } catch (error) {
    throw error.response?.data || new Error('Falha ao carregar credenciais.');
  }
}

async function upsertCredential(payload) {
  try {
    const response = await apiClient.put('/credenciais', payload);
    return response.data;
  } catch (error) {
    throw error.response?.data || new Error('Falha ao salvar credencial.');
  }
}

async function deleteCredential(scopeType, provider) {
  try {
    const response = await apiClient.delete(`/credenciais/${scopeType}/${provider}`);
    return response.data;
  } catch (error) {
    throw error.response?.data || new Error('Falha ao remover credencial.');
  }
}

async function validateCredential(payload) {
  try {
    const response = await apiClient.post('/credenciais/validar', payload);
    return response.data;
  } catch (error) {
    throw error.response?.data || new Error('Falha ao validar credencial.');
  }
}

export default {
  getOverview,
  upsertCredential,
  deleteCredential,
  validateCredential,
};
