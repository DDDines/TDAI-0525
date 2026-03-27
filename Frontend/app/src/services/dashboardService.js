/**
 * Dashboard service.
 */

import apiClient from './apiClient';

async function getMyDashboard(days = 30) {
  try {
    const response = await apiClient.get('/dashboard/me', { params: { days } });
    return response.data;
  } catch (error) {
    throw error.response?.data || new Error('Falha ao carregar dashboard do usuario.');
  }
}

export default {
  getMyDashboard,
};
