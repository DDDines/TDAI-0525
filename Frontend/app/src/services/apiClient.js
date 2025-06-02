// Frontend/app/src/services/apiClient.js
import axios from 'axios';

// A VITE_API_BASE_URL deve ser a URL base do seu backend, ex: http://localhost:8000
// O prefixo /api/v1 será adicionado aqui.
const API_PREFIX = '/api/v1';
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: `${BASE_URL}${API_PREFIX}`, // ex: http://localhost:8000/api/v1
  headers: {
    'Content-Type': 'application/json',
  }
});

// Interceptor para adicionar o token de autenticação a cada requisição
apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, error => {
  return Promise.reject(error);
});

// Interceptor de resposta para lidar com erros 401 (Não Autorizado) globalmente
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      // Token inválido ou expirado.
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken'); // Se estiver usando refresh tokens

      // Evita redirecionamento se já estiver na página de login para não criar loop
      if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
        // Redireciona para a página de login.
        // Idealmente, isso seria tratado por um contexto de autenticação que atualizaria o estado
        // e o Router faria o redirecionamento com base nesse estado.
        // Por simplicidade, um redirecionamento direto aqui pode funcionar, mas pode ter efeitos colaterais.
        // Uma abordagem melhor seria disparar um evento customizado ou usar um estado global.
        console.warn("Interceptor: Token inválido ou expirado. Deslogando...");
        window.location.href = '/login'; 
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;