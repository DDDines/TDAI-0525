// Frontend/app/src/contexts/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import authService from '../services/authService';
import apiClient from '../services/apiClient'; // Para definir o header padrão após login
import { showSuccessToast, showErrorToast, showInfoToast } from '../utils/notifications';

const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(false); // Para operações de login/logout
  const [isSessionLoading, setIsSessionLoading] = useState(true); // Para verificação inicial da sessão

  const navigate = useNavigate();
  const location = useLocation();

  const verifyUserSession = useCallback(async () => {
    console.log("AuthContext: Verificando sessão do usuário...");
    const token = localStorage.getItem('accessToken');
    if (!token) {
      console.log("AuthContext: Nenhum token encontrado no localStorage.");
      setUser(null);
      setIsSessionLoading(false);
      return;
    }

    // Se há um token, tentamos definir no apiClient e buscar o usuário
    // O interceptor do apiClient já deve estar fazendo isso, mas uma garantia extra não faz mal.
    // apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;

    try {
      // Não precisa de setIsLoading(true) aqui, pois temos isSessionLoading
      const currentUser = await authService.getCurrentUser();
      console.log("AuthContext: Usuário da sessão verificado:", currentUser);
      setUser(currentUser);
    } catch (error) {
      console.error("AuthContext: Nenhuma sessão de usuário ativa encontrada ou erro ao verificar usuário:", error.response?.data || error.message);
      setUser(null);
      localStorage.removeItem('accessToken'); // Limpa token inválido
      localStorage.removeItem('refreshToken');
      // Não redirecionar para login aqui, o interceptor do apiClient fará isso se necessário
      // e ProtectedRoute cuidará do redirecionamento se o usuário não estiver autenticado.
    } finally {
      setIsSessionLoading(false);
    }
  }, []);

  useEffect(() => {
    verifyUserSession();
  }, [verifyUserSession]);

  const login = async (email, password) => {
    try {
      setIsLoading(true);
      const data = await authService.login(email, password);
      console.log("AuthContext: Login API response data:", data);
      if (data.access_token) {
        localStorage.setItem('accessToken', data.access_token);
        if (data.refresh_token) {
          localStorage.setItem('refreshToken', data.refresh_token);
        }
        // O interceptor de requisição do apiClient pegará o token do localStorage na próxima chamada.
        // Não é estritamente necessário definir o header padrão aqui se o interceptor já faz isso.
        // apiClient.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
        
        // Após salvar o token, verificar a sessão para definir o usuário e o estado de carregamento da sessão
        await verifyUserSession(); // Isso agora definirá o usuário
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
      setUser(null); // Garante que o usuário seja nulo em caso de falha
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
    } finally {
      setIsLoading(false);
    }
  };

  const logout = useCallback(() => { // Envolver logout em useCallback
    console.log("AuthContext: Efetuando logout...");
    setUser(null);
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    delete apiClient.defaults.headers.common['Authorization'];
    showInfoToast("Você foi desconectado.");
    navigate('/login', { replace: true });
  }, [navigate]);

  const updateUser = (updatedUserData) => {
    setUser(prevUser => ({ ...prevUser, ...updatedUserData }));
  };

  const value = {
    user,
    isLoading, // Loading para operações de login/logout
    isSessionLoading, // Loading para verificação inicial da sessão
    login,
    logout,
    updateUser,
    isAuthenticated: !!user, // Adicionado para conveniência
  };

  // Não renderiza children até que a verificação inicial da sessão seja concluída,
  // a menos que seja uma rota pública (mas App.jsx já cuida de rotas públicas/protegidas)
  // Se quisermos um spinner global, podemos adicionar aqui:
  // if (isSessionLoading && !user && window.location.pathname !== '/login' /* e outras rotas públicas */) {
  //   return <div>Verificando sessão...</div>; // Ou um spinner
  // }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};