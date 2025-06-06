// Frontend/app/src/contexts/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import authService from '../services/authService';
import apiClient from '../services/apiClient'; // Para configurar o header padrão globalmente

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  const clearAuthData = useCallback(() => {
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('accessToken'); // Chave corrigida
    delete apiClient.defaults.headers.common['Authorization'];
    console.log("AuthContext: clearAuthData chamado, token removido e header limpo.");
    setIsLoading(false);
  }, []);

  const setAuthData = useCallback((userData, token) => {
    setUser(userData);
    setIsAuthenticated(true);
    if (token) {
        localStorage.setItem('accessToken', token); // Chave corrigida
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        console.log("AuthContext: setAuthData chamado, token salvo e header configurado.", userData);
    } else {
        console.warn("AuthContext: setAuthData chamado sem token. UserData:", userData);
    }
    setIsLoading(false);
  }, []);

  const checkUserSession = useCallback(async () => {
    console.log("AuthContext: Verificando sessão do usuário...");
    setIsLoading(true);
    const token = localStorage.getItem('accessToken'); // Chave corrigida
    const tokenSnippet = token ? `${token.substring(0, 15)}...${token.substring(token.length - 15)}` : "N/A";
    console.log(`AuthContext: Token encontrado no localStorage (snippet): ${tokenSnippet}`);

    if (token) {
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      try {
        console.log("AuthContext: Token encontrado, tentando buscar dados do usuário atual...");
        const userData = await authService.getCurrentUser();
        if (userData) {
          console.log("AuthContext: Dados do usuário recuperados com sucesso:", userData);
          setAuthData(userData, token);
        } else {
          console.warn("AuthContext: getCurrentUser não retornou dados do usuário. Limpando...");
          clearAuthData();
        }
      } catch (error) {
        const errorMsg = error.response?.data?.detail || error.message;
        console.error("AuthContext: Erro ao buscar usuário com token existente:", errorMsg);
        if (error.response && error.response.status === 401) {
          console.warn("AuthContext: Token inválido ou expirado (401). Limpando sessão.");
        }
        clearAuthData();
      }
    } else {
      console.log("AuthContext: Nenhum token no localStorage. Sessão não iniciada.");
      clearAuthData();
    }
  }, [setAuthData, clearAuthData]);

  useEffect(() => {
    checkUserSession();
  }, [checkUserSession]);

  const login = async (email, password) => {
    console.log("AuthContext: Tentando login...");
    setIsLoading(true);
    try {
      const response = await authService.login(email, password);
      if (response && response.access_token) {
        const token = response.access_token;
        const tokenSnippetLogin = `${token.substring(0, 15)}...${token.substring(token.length - 15)}`;
        console.log(`AuthContext: Login bem-sucedido, token recebido (snippet): ${tokenSnippetLogin}`);
        
        localStorage.setItem('accessToken', token); // Chave corrigida
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        console.log("AuthContext: Token salvo no localStorage e configurado no header do apiClient.");

        console.log("AuthContext: Buscando dados do usuário após login...");
        const userData = await authService.getCurrentUser();
        
        if (userData) {
          console.log("AuthContext: Dados do usuário obtidos após login:", userData);
          setAuthData(userData, token);
          
          const from = location.state?.from?.pathname || '/dashboard';
          console.log(`AuthContext: Redirecionando para ${from}`);
          navigate(from, { replace: true });
          return true;
        } else {
          console.error("AuthContext: Falha ao obter dados do usuário após login bem-sucedido (userData vazio). Limpando token...");
          clearAuthData();
          throw new Error("Falha ao obter dados do usuário após o login.");
        }
      } else {
        const errorDetail = response.data?.detail || "Resposta de login inválida ou não continha token de acesso.";
        console.error("AuthContext: Login falhou - " + errorDetail);
        throw new Error(errorDetail);
      }
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || "Erro desconhecido durante o login.";
      console.error("AuthContext: Erro no processo de login (catch):", errorMsg);
      clearAuthData();
      if (error.response && error.response.data) {
        throw error.response.data;
      } else {
        throw new Error(errorMsg);
      }
    } finally {
      console.log("AuthContext: Processo de login finalizado (finally).");
    }
  };

  const logout = async (redirectTo = "/login") => {
    console.log("AuthContext: Efetuando logout...");
    clearAuthData();
    console.log(`AuthContext: Redirecionando para ${redirectTo} após logout.`);
    navigate(redirectTo);
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout, checkUserSession, setUser, setIsAuthenticated, setIsLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined || context === null) { // Adicionada verificação de null para robustez
    throw new Error('useAuth deve ser usado dentro de um AuthProvider');
  }
  return context;
};
