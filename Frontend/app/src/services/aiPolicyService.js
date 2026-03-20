/**
 * AI policy service.
 */

import apiClient from './apiClient';

async function getOverview() {
  try {
    const response = await apiClient.get('/ai-policy/overview');
    return response.data;
  } catch (error) {
    throw error.response?.data || new Error('Falha ao carregar política de IA.');
  }
}

async function upsertPolicy(payload) {
  try {
    const response = await apiClient.put('/ai-policy', payload);
    return response.data;
  } catch (error) {
    throw error.response?.data || new Error('Falha ao salvar política de IA.');
  }
}

async function deletePolicy(scopeType, planId) {
  try {
    const params = planId != null ? { plan_id: planId } : {};
    const response = await apiClient.delete(`/ai-policy/${scopeType}`, { params });
    return response.data;
  } catch (error) {
    throw error.response?.data || new Error('Falha ao remover política de IA.');
  }
}

const aiPolicyService = { getOverview, upsertPolicy, deletePolicy };
export default aiPolicyService;
