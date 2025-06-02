// Frontend/app/src/contexts/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../services/authService'; // Seu serviço de autenticação

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth deve ser usado dentro de um AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true); // Para o carregamento inicial
  const navigate = useNavigate();

  // Função para verificar o usuário atual ao carregar o contexto
  const checkCurrentUser = useCallback(async () => {
    setIsLoadingAuth(true);
    try {
      const currentUserData = await authService.getCurrentUser(); // authService.getCurrentUser já deve retornar o usuário ou null
      if (currentUserData) {
        setUser(currentUserData);
        setIsAuthenticated(true);
      } else {
        setUser(null);
        setIsAuthenticated(false);
        // O token pode ser inválido/expirado; authService.getCurrentUser já deve ter limpado do localStorage.
      }
    } catch (error) {
      console.error('Nenhuma sessão de usuário ativa encontrada ou erro ao verificar usuário:', error);
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setIsLoadingAuth(false);
    }
  }, []);

  useEffect(() => {
    checkCurrentUser();
  }, [checkCurrentUser]);

  const login = async (email, password) => {
    try {
      setIsLoadingAuth(true);
      // authService.loginUser deve salvar o token no localStorage e retornar dados do usuário
      const loggedInData = await authService.loginUser(email, password); 
      // Supondo que loggedInData.user contenha os dados do usuário
      // e que o token já foi salvo pelo serviço.
      // O endpoint /users/me será chamado por checkCurrentUser ou explicitamente se necessário.
      // Após login, é bom buscar os dados completos do usuário para popular o contexto.
      await checkCurrentUser(); // Recarrega os dados do usuário após login bem-sucedido
      
      // Se checkCurrentUser não navegar, e você quiser navegar explicitamente após login:
      // if (authService.getToken()) { // Verifica se o token foi realmente setado
      //   navigate('/'); 
      // }
      // navigate('/'); // Ou navega incondicionalmente se loginUser não der erro

      return loggedInData; // Retorna o que o serviço de login retornou
    } catch (error) {
      console.error('Falha no login (AuthContext):', error);
      setUser(null);
      setIsAuthenticated(false);
      throw error; 
    } finally {
      setIsLoadingAuth(false);
    }
  };

  const logout = () => {
    authService.logoutUser(); // Limpa o token do localStorage
    setUser(null);
    setIsAuthenticated(false);
    navigate('/login'); 
  };
  
  const value = {
    user,
    isAuthenticated,
    isLoadingAuth,
    login,
    logout,
    // isAdmin: user ? user.is_superuser : false // Exemplo
  };

  // Não renderiza children até que a verificação inicial de autenticação termine,
  // ou renderiza um loader global aqui se preferir.
  // Para simplificar, vamos renderizar children, e os componentes/rotas protegidas
  // podem usar isLoadingAuth para decidir o que mostrar.
  // if (isLoadingAuth) {
  //   return <div>Carregando autenticação...</div>; // Ou um spinner
  // }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};