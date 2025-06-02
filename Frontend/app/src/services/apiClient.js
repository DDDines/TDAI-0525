// Frontend/app/src/services/apiClient.js
import axios from 'axios';

// Com a configuração de proxy no vite.config.js para '/api/v1',
// o baseURL aqui pode ser apenas o prefixo que o proxy está escutando.
// O Vite irá redirecionar para 'http://localhost:8000/api/v1'.
const API_BASE_URL = '/api/v1'; // Simplificado para funcionar com o proxy do Vite

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  }
});

apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, error => {
  return Promise.reject(error);
});

// Interceptor de resposta para lidar com erros 401 (Não Autorizado)
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      // Se o erro for 401, o token pode ter expirado ou ser inválido.
      // Limpa o token e redireciona para a página de login.
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      // Evita redirecionamento em loop se já estiver na página de login
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'; // Ou use o useNavigate do react-router-dom se estiver em um componente
      }
      console.error("Erro 401: Não autorizado. Redirecionando para login.");
    }
    return Promise.reject(error);
  }
);

export default apiClient;