/**
 * Import validation rules service.
 */

import apiClient from './apiClient';

async function listarRegras() {
  const response = await apiClient.get('/import-rules/');
  return response.data;
}

async function deletarRegra(ruleId) {
  await apiClient.delete(`/import-rules/${ruleId}`);
}

export default { listarRegras, deletarRegra };
