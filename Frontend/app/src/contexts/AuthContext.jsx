// Frontend/app/src/contexts/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import authService from '../services/authService';
import apiClient from '../services/apiClient'; // Importar apiClient para definir header
import { showSuccessToast, showErrorToast, showInfoToast } from '../utils/notifications';

const AuthContext = createContext(null);

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === null) {
        throw new Error('useAuth deve ser usado dentro de um AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSessionLoading, setIsSessionLoading] = useState(true);

  const navigate = useNavigate();
  const location = useLocation();

  const verifyUserSession = useCallback(async () => {
    console.log("AuthContext: Verificando sessão do usuário...");
    const token = localStorage.getItem('accessToken');
    if (!token) {
      console.log("AuthContext: Nenhum token encontrado no localStorage.");
      setUser(null);
      // Se não há token, não há necessidade de definir o header padrão no apiClient
      // delete apiClient.defaults.headers.common['Authorization']; // Removido daqui, logout cuida disso
      setIsSessionLoading(false);
      return;
    }

    // O interceptor de requisição do apiClient deve adicionar o token automaticamente.
    // Mas, para garantir, podemos definir aqui também, embora possa ser redundante.
    // apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;

    try {
      const currentUser = await authService.getCurrentUser();
      console.log("AuthContext: Usuário da sessão verificado:", currentUser);
      setUser(currentUser);
    } catch (error) {
      console.error("AuthContext: Nenhuma sessão de usuário ativa ou erro ao verificar:", error.response?.data || error.message);
      setUser(null);
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      delete apiClient.defaults.headers.common['Authorization']; // Limpa o header se a verificação falhar
    } finally {
      setIsSessionLoading(false);
    }
  }, []);

  useEffect(() => {
    verifyUserSession();
  }, [verifyUserSession]);

  const login = async (email, password) => {
    setIsLoading(true);
    try {
      const data = await authService.login(email, password);
      console.log("AuthContext: Login API response data:", data);
      if (data.access_token) {
        localStorage.setItem('accessToken', data.access_token);
        if (data.refresh_token) {
          localStorage.setItem('refreshToken', data.refresh_token);
        }
        // **ADIÇÃO IMPORTANTE AQUI:**
        // Define o header de autorização padrão no apiClient imediatamente.
        // Isso garante que as próximas chamadas usem este token,
        // mesmo que haja um pequeno delay para o interceptor pegar do localStorage.
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;

        await verifyUserSession(); // Verifica a sessão e define o usuário
        showSuccessToast("Login realizado com sucesso!");
        const from = location.state?.from?.pathname || "/dashboard";
        navigate(from, { replace: true });
      } else {
        throw new Error(data.detail || "Falha no login: Token não recebido.");
      }
    } catch (error) {
      console.error("AuthContext: Erro no login:", error.response?.data || error.message);
      const errorMsg = error.response?.data?.detail || error.message || 'Falha ao fazer login.';
      showErrorToast(errorMsg);
      setUser(null);
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      delete apiClient.defaults.headers.common['Authorization'];
    } finally {
      setIsLoading(false);
    }
  };

  const logout = useCallback(() => {
    console.log("AuthContext: Efetuando logout...");
    setUser(null);
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    delete apiClient.defaults.headers.common['Authorization']; // Limpa o header padrão
    showInfoToast("Você foi desconectado.");
    navigate('/login', { replace: true });
  }, [navigate]);

  const updateUser = (updatedUserData) => {
    setUser(prevUser => ({ ...prevUser, ...updatedUserData }));
  };

  const value = {
    user,
    isLoading,
    isSessionLoading,
    login,
    logout,
    updateUser,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};