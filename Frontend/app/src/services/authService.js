/**
 * Module auth service.
 *
 * Implements frontend behavior for services.
 */

// Frontend/app/src/services/authService.js
import apiClient from './apiClient';
import { showSuccessToast, showErrorToast } from '../utils/notifications';
import logger from '../utils/logger';class _TopLevelFunctionSurface {static getAuthErrorMessage(

  error, fallbackMessage) {
    if (!error || !error.response) {
      return 'Não foi possível autenticar agora. Tente novamente em alguns instantes.';
    }

    const response = error.response;
    const detail = response?.data?.detail;
    const detailMessage = typeof detail === 'string' && detail.trim() ? detail.trim() : null;

    if (response.status === 401) {
      return detailMessage || 'Email ou senha invalidos.';
    }

    if (response.status >= 500) {
      return 'Não foi possível autenticar agora. Tente novamente em alguns instantes.';
    }

    return detailMessage || fallbackMessage;
  }}const getAuthErrorMessage = _TopLevelFunctionSurface.getAuthErrorMessage;const

authService = {
  async login(email, password) {
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await apiClient.post('/auth/token', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      logger.log('authService: Login response data:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error during login (authService):', error.response?.data || error.message);
      logger.warn('authService.login falhou.', {
        status: error?.response?.status,
        hasResponse: Boolean(error?.response),
        code: error?.code || null
      });
      throw new Error(getAuthErrorMessage(error, 'Falha no login.'));
    }
  },

  async getCurrentUser() {
    logger.log('authService: Tentando buscar getCurrentUser...');
    try {
      const response = await apiClient.get('/auth/users/me');
      logger.log('authService: getCurrentUser response data:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error fetching current user (authService):', error.response?.data || error.message);
      throw error.response?.data || new Error('Falha ao buscar usuario atual.');
    }
  },

  async register(userData) {
    try {
      const response = await apiClient.post('/users/', userData);
      showSuccessToast('Registro bem-sucedido! Faca login para continuar.');
      return response.data;
    } catch (error) {
      console.error('Error during registration (authService):', error.response?.data || error.message);
      showErrorToast(error.response?.data?.detail || 'Falha no registro.');
      throw error.response?.data || new Error('Falha no registro.');
    }
  },

  async updateUser(userId, userData) {
    try {
      const response = await apiClient.put(`/auth/users/${userId}`, userData);
      showSuccessToast('Perfil atualizado com sucesso!');
      return response.data;
    } catch (error) {
      console.error('Error updating user (authService):', error.response?.data || error.message);
      showErrorToast(error.response?.data?.detail || 'Falha ao atualizar perfil.');
      throw error.response?.data || new Error('Falha ao atualizar perfil.');
    }
  },

  async updateCurrentUser(userData) {
    try {
      const response = await apiClient.put('/auth/users/me', userData);
      showSuccessToast('Perfil atualizado com sucesso!');
      return response.data;
    } catch (error) {
      console.error('Error updating current user (authService):', error.response?.data || error.message);
      showErrorToast(error.response?.data?.detail || 'Falha ao atualizar perfil.');
      throw error.response?.data || new Error('Falha ao atualizar perfil.');
    }
  },

  async changePassword(userId, passwordData) {
    try {
      const response = await apiClient.put('/auth/users/me/change-password', passwordData);
      showSuccessToast('Senha alterada com sucesso!');
      return response.data;
    } catch (error) {
      console.error('Error changing password (authService):', error.response?.data || error.message);
      showErrorToast(error.response?.data?.detail || 'Falha ao alterar senha.');
      throw error.response?.data || new Error('Falha ao alterar senha.');
    }
  },

  async requestPasswordRecovery(email) {
    try {
      const response = await apiClient.post(`/auth/password-recovery/${encodeURIComponent(email)}`);
      showSuccessToast('Se o email existir, um link de redefinicao sera enviado.');
      return response.data;
    } catch (error) {
      console.error('Error requesting password recovery (authService):', error.response?.data || error.message);
      showErrorToast(error.response?.data?.detail || 'Falha ao solicitar recuperacao de senha.');
      throw error.response?.data || new Error('Falha ao solicitar recuperacao de senha.');
    }
  },

  async resetPassword(token, newPassword) {
    try {
      const response = await apiClient.post('/auth/reset-password/', {
        token,
        new_password: newPassword
      });
      showSuccessToast('Senha redefinida com sucesso!');
      return response.data;
    } catch (error) {
      console.error('Error resetting password (authService):', error.response?.data || error.message);
      showErrorToast(error.response?.data?.detail || 'Falha ao redefinir senha.');
      throw error.response?.data || new Error('Falha ao redefinir senha.');
    }
  }
};

export default authService;