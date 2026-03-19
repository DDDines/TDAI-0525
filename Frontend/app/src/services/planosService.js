/**
 * Planos e faturamento service.
 */

import apiClient from './apiClient';

async function listarPlanos() {
  const response = await apiClient.get('/planos/');
  return response.data;
}

async function meuPlano() {
  const response = await apiClient.get('/planos/meu-plano/');
  return response.data;
}

async function mudarPlano(planoId) {
  const response = await apiClient.post('/planos/mudar/', { plano_id: planoId });
  return response.data;
}

export default { listarPlanos, meuPlano, mudarPlano };
