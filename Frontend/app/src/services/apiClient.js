// Frontend/app/src/services/apiClient.js
import axios from 'axios';
import logger from '../utils/logger';

// Use VITE_API_BASE_URL if defined (e.g. in production) otherwise fall back to
// the relative path so Vite's dev proxy can handle API requests during
// development.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  }
});

apiClient.interceptors.request.use(
  config => {
    const token = localStorage.getItem('accessToken');
    const tokenSnippet = token ? `${token.substring(0, 15)}...${token.substring(token.length - 15)}` : "N/A";

    logger.log(`apiClient: Interceptando requisição para ${config.url}. Token no localStorage (snippet): ${tokenSnippet}`);

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      // LOG DETALHADO DO HEADER (PARA DEBUG - REMOVER DEPOIS)
      logger.log(`apiClient: Header Authorization DEFINIDO para ${config.url}: "${config.headers.Authorization.substring(0,30)}..."`);
    } else {
      logger.log(`apiClient: Nenhum token encontrado no localStorage para ${config.url}.`);
      // Garantir que o header de autorização seja removido se não houver token
      delete config.headers.Authorization;
    }
    return config;
  },
  error => {
    console.error('apiClient: Erro no interceptor de requisição:', error);
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  response => response,
  error => {
    // Log mais detalhado do erro, incluindo a config da requisição que falhou
    logger.log(
        `apiClient: Interceptor de resposta pegou um erro. URL: ${error.config?.url}`,
        `Status: ${error.response?.status}`,
        `Data: ${JSON.stringify(error.response?.data)}`,
        // `Headers da Requisição que Falhou: ${JSON.stringify(error.config?.headers)}` // Log verboso, descomentar se necessário
    );

    if (error.response && error.response.status === 401) {
      // Apenas redireciona se NÃO estiver já na página de login para evitar loops
      if (window.location.pathname !== '/login') {
        console.warn("apiClient: Erro 401! Limpando tokens e redirecionando para /login. URL original:", error.config?.url);
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        delete apiClient.defaults.headers.common['Authorization']; // Limpa o header padrão também
        window.location.href = '/login';
      } else {
        console.warn("apiClient: Erro 401 na página de login ou durante verificação inicial, não redirecionando para evitar loop.");
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;
