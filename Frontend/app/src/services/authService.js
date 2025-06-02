// Frontend/app/src/services/authService.js
import apiClient from './apiClient'; // Importa a instância centralizada do Axios

// A baseURL (ex: http://localhost:8000/api/v1) já está configurada no apiClient
// Os paths dos endpoints aqui são relativos a essa baseURL.

export const login = async (email, password) => {
  const loginData = new URLSearchParams();
  loginData.append('username', email); // O backend espera 'username' para o email
  login_data.append('password', password);

  try {
    // O endpoint de token está em /auth/token (relativo ao baseURL do apiClient)
    const response = await apiClient.post('/auth/token', loginData, {
       headers: {
         // Sobrescreve Content-Type para este request específico, pois o backend espera form-urlencoded
         'Content-Type': 'application/x-www-form-urlencoded',
       },
    });
    if (response.data.access_token) {
      localStorage.setItem('accessToken', response.data.access_token);
      if (response.data.refresh_token) {
        localStorage.setItem('refreshToken', response.data.refresh_token);
      }
    }
    return response.data; // Retorna { access_token, refresh_token, token_type }
  } catch (error) {
    // O interceptor de resposta no apiClient já pode ter lidado com 401.
    // Aqui podemos tratar outros erros específicos do login ou relançar.
    console.error('Error during login:', error.response?.data || error.message);
    throw error.response?.data || new Error('Falha no login. Verifique suas credenciais.');
  }
};

export const getCurrentUser = async () => {
  try {
    // A URL completa será: baseURL + /auth/users/me/
    const response = await apiClient.get('/auth/users/me/'); 
    return response.data; 
  } catch (error) {
    console.error('Error fetching current user:', error.response?.data || error.message);
    // O interceptor de resposta já lida com 401 e redireciona.
    // Lançar o erro permite que o componente chamador (ex: Topbar) reaja se necessário.
    throw error.response?.data || new Error('Falha ao buscar dados do usuário.');
  }
};

export const updateCurrentUser = async (userData) => {
  try {
    // O endpoint PUT para /users/me/ está em main.py, não sob /auth.
    // O baseURL do apiClient já inclui /api/v1.
    const response = await apiClient.put('/users/me/', userData); // A URL será /api/v1/users/me/
    return response.data; 
  } catch (error) {
    console.error('Error updating current user:', error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao atualizar dados do usuário.');
  }
};

export const changePassword = async (passwordData) => {
  try {
    // O endpoint de change-password também está em main.py como /users/me/change-password
    const response = await apiClient.post('/users/me/change-password', passwordData); 
    return response.data; 
  } catch (error) {
    console.error('Error changing password:', error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao alterar senha.');
  }
};

// As funções getTotalCounts, getMeuHistoricoUsoIA, getHistoricoUsoIAPorProduto
// foram movidas ou serão definidas em seus próprios arquivos de serviço
// (ex: adminService.js, usoIaService.js) para melhor organização,
// ou podem permanecer aqui se fizer sentido para a sua estrutura.
// Por agora, vou remover as que não são estritamente de "auth".

export default {
  login,
  getCurrentUser,
  updateCurrentUser,
  changePassword,
};