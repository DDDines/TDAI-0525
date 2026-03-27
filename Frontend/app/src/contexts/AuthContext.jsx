/**
 * Module auth context.
 *
 * Defines responsibilities and integration points for contexts.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import authService from '../services/authService';
import apiClient from '../services/apiClient';
import logger from '../utils/logger';

const AuthContext = createContext(null);

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  const clearAuthData = useCallback(() => {
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('accessToken');
    delete apiClient.defaults.headers.common.Authorization;
    logger.log('AuthContext: sessão limpa e header de autorização removido.');
    setIsLoading(false);
  }, []);

  const setAuthData = useCallback((userData, token) => {
    setUser(userData);
    setIsAuthenticated(true);
    localStorage.setItem('accessToken', token);
    apiClient.defaults.headers.common.Authorization = `Bearer ${token}`;
    logger.log('AuthContext: sessao autenticada e header configurado.');
    setIsLoading(false);
  }, []);

  const checkUserSession = useCallback(async () => {
    logger.log('AuthContext: verificando sessão do usuário...');
    setIsLoading(true);
    const token = localStorage.getItem('accessToken');

    if (!token) {
      logger.log('AuthContext: nenhum token encontrado no localStorage.');
      clearAuthData();
      return;
    }

    apiClient.defaults.headers.common.Authorization = `Bearer ${token}`;
    try {
      const userData = await authService.getCurrentUser();
      if (userData) {
        setAuthData(userData, token);
      } else {
        logger.warn('AuthContext: getCurrentUser retornou vazio. Limpando sessão.');
        clearAuthData();
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message;
      logger.error('AuthContext: falha ao recuperar usuário autenticado.', errorMsg);
      if (error.response?.status === 401) {
        logger.warn('AuthContext: token inválido/expirado (401).');
      }
      clearAuthData();
    }
  }, [clearAuthData, setAuthData]);

  useEffect(() => {
    void checkUserSession();
  }, [checkUserSession]);

  const login = async (email, password, options = {}) => {
    logger.log('AuthContext: iniciando login...');
    setIsLoading(true);
    try {
      const response = await authService.login(email, password);
      const token = response?.access_token;
      if (!token) {
        const detail =
          response?.data?.detail ||
          'Resposta de login inválida ou sem token de acesso.';
        throw new Error(detail);
      }

      localStorage.setItem('accessToken', token);
      apiClient.defaults.headers.common.Authorization = `Bearer ${token}`;

      const userData = await authService.getCurrentUser();
      if (!userData) {
        clearAuthData();
        throw new Error('Falha ao obter dados do usuário após login.');
      }

      setAuthData(userData, token);

      const redirectPath = options?.redirectPath || location.state?.from?.pathname || '/dashboard';
      navigate(redirectPath, { replace: true });
      return true;
    } catch (error) {
      const errorMsg =
        error.response?.data?.detail ||
        error.message ||
        'Erro desconhecido durante o login.';
      logger.error('AuthContext: erro no login.', errorMsg);
      clearAuthData();
      if (error.response?.data) {
        throw error.response.data;
      }
      throw new Error(errorMsg);
    } finally {
      logger.log('AuthContext: fluxo de login finalizado.');
    }
  };

  const logout = async (redirectTo = '/login') => {
    logger.log('AuthContext: efetuando logout...');
    clearAuthData();
    navigate(redirectTo);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        currentUser: user,
        isAuthenticated,
        isLoading,
        login,
        logout,
        checkUserSession,
        setUser,
        setIsAuthenticated,
        setIsLoading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined || context === null) {
    throw new Error('useAuth deve ser usado dentro de um AuthProvider');
  }
  return context;
}

export { AuthProvider, useAuth };
