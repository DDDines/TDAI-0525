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

async function criarCheckout(planoId) {
  const response = await apiClient.post('/billing/checkout', { plano_id: planoId });
  return response.data; // { checkout_url }
}

async function abrirPortal() {
  const response = await apiClient.get('/billing/portal');
  return response.data; // { portal_url }
}

export default { listarPlanos, meuPlano, mudarPlano, criarCheckout, abrirPortal };
