/**
 * Dashboard service.
 */

import apiClient from './apiClient';

async function getMyDashboard() {
  try {
    const response = await apiClient.get('/dashboard/me');
    return response.data;
  } catch (error) {
    throw error.response?.data || new Error('Falha ao carregar dashboard do usuario.');
  }
}

export default {
  getMyDashboard,
};
