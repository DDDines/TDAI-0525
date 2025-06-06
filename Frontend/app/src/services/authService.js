// Frontend/app/src/services/authService.js
import apiClient from './apiClient';
import { showSuccessToast, showErrorToast } from '../utils/notifications'; // Assumindo que você quer usar toasts aqui também

const authService = {
  async login(email, password) {
    try {
      const formData = new URLSearchParams();
      formData.append('username', email); // O backend espera 'username' no form data
      formData.append('password', password);

      const response = await apiClient.post('/auth/token', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });
      console.log("authService: Login response data:", response.data);
      // O token é salvo no AuthContext após esta chamada ser bem-sucedida
      return response.data;
    } catch (error) {
      console.error('Error during login (authService):', error.response?.data || error.message);
      // Erros de login são geralmente tratados no componente/contexto que chama
      throw error.response?.data || new Error('Falha no login.');
    }
  },

  async getCurrentUser() {
    console.log("authService: Tentando buscar getCurrentUser...");
    try {
      // CORREÇÃO: Remover a barra final para corresponder à definição do endpoint FastAPI
      const response = await apiClient.get('/auth/users/me'); // ANTES: '/auth/users/me/'
      console.log("authService: getCurrentUser response data:", response.data);
      return response.data;
    } catch (error) {
      console.error('Error fetching current user (authService):', error.response?.data || error.message);
      // O AuthContext tratará este erro (ex: limpando o usuário, redirecionando para login)
      throw error.response?.data || new Error('Falha ao buscar usuário atual.');
    }
  },

  async register(userData) {
    try {
      // Assumindo que seu backend tem um endpoint /auth/register ou /users/
      // Se for /users/ (como em main.py), o apiClient já tem /api/v1
      // Ajuste o endpoint conforme necessário. Se for /api/v1/users/ :
      const response = await apiClient.post('/users/', userData);
      showSuccessToast('Registro bem-sucedido! Faça login para continuar.');
      return response.data;
    } catch (error) {
      console.error('Error during registration (authService):', error.response?.data || error.message);
      showErrorToast(error.response?.data?.detail || 'Falha no registro.');
      throw error.response?.data || new Error('Falha no registro.');
    }
  },

  async updateUser(userId, userData) {
    try {
      // O endpoint em auth.py é /auth/users/{user_id}
      const response = await apiClient.put(`/auth/users/${userId}`, userData);
      showSuccessToast('Perfil atualizado com sucesso!');
      return response.data;
    } catch (error) {
      console.error('Error updating user (authService):', error.response?.data || error.message);
      showErrorToast(error.response?.data?.detail || 'Falha ao atualizar perfil.');
      throw error.response?.data || new Error('Falha ao atualizar perfil.');
    }
  },

  async changePassword(userId, passwordData) {
    try {
      // O endpoint em auth.py é /auth/users/{user_id}/change-password
      const response = await apiClient.put(`/auth/users/${userId}/change-password`, passwordData);
      showSuccessToast('Senha alterada com sucesso!');
      return response.data;
    } catch (error) {
      console.error('Error changing password (authService):', error.response?.data || error.message);
      showErrorToast(error.response?.data?.detail || 'Falha ao alterar senha.');
      throw error.response?.data || new Error('Falha ao alterar senha.');
    }
  },

  // Adicione outras funções de autenticação/usuário conforme necessário
  // Ex: forgotPassword, resetPassword, etc.
};

export default authService;
