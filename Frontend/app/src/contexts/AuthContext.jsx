import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import authService from '../services/authService';
import apiClient from '../services/apiClient'; // Para configurar o token no Axios

const AuthContext = createContext(null);

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true); // Começa como true para verificação inicial
    const navigate = useNavigate();
    const location = useLocation();

    const setAuthData = useCallback((userData, token) => {
        setUser(userData);
        setIsAuthenticated(true);
        localStorage.setItem('token', token);
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        console.log("AuthContext: Usuário autenticado e token armazenado.", userData);
        setIsLoading(false); // Garante que o loading termine após autenticação
    }, []);

    const clearAuthData = useCallback(() => {
        setUser(null);
        setIsAuthenticated(false);
        localStorage.removeItem('token');
        delete apiClient.defaults.headers.common['Authorization'];
        console.log("AuthContext: Dados de autenticação limpos.");
        setIsLoading(false); // Garante que o loading termine
    }, []);

    const login = async (email, password) => {
        console.log("AuthContext: Tentando login...");
        setIsLoading(true);
        try {
            const response = await authService.login(email, password);
            if (response && response.access_token) {
                console.log("AuthContext: Token recebido, buscando dados do usuário...");
                // Configura o token no apiClient ANTES de chamar getCurrentUser
                apiClient.defaults.headers.common['Authorization'] = `Bearer ${response.access_token}`;
                const userData = await authService.getCurrentUser(); // Não precisa passar o token aqui, já está no apiClient
                
                if (userData) {
                    setAuthData(userData, response.access_token);
                    const from = location.state?.from?.pathname || '/'; // Redireciona para a página anterior ou dashboard
                    navigate(from, { replace: true });
                    return true;
                } else {
                    console.error("AuthContext: Falha ao obter dados do usuário após login bem-sucedido.");
                    clearAuthData();
                    throw new Error("Falha ao obter dados do usuário após o login.");
                }
            } else {
                 throw new Error(response.data?.detail || "Falha no login. Resposta inesperada do token endpoint.");
            }
        } catch (error) {
            console.error("AuthContext: Erro no login:", error.response?.data?.detail || error.message);
            clearAuthData();
            // Não precisa setIsLoading(false) aqui, pois o finally já faz
            throw error; // Re-throw para que LoginPage possa tratar
        } finally {
            setIsLoading(false);
        }
    };

    const logout = useCallback(() => {
        console.log("AuthContext: Efetuando logout...");
        clearAuthData();
        navigate('/login', { replace: true });
    }, [clearAuthData, navigate]);

    const checkUserSession = useCallback(async () => {
        console.log("AuthContext: Verificando sessão do usuário na inicialização...");
        setIsLoading(true); // Inicia o carregamento
        const token = localStorage.getItem('token');
        if (token) {
            console.log("AuthContext: Token encontrado no localStorage. Validando...");
            apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            try {
                const userData = await authService.getCurrentUser();
                if (userData) {
                    setAuthData(userData, token); // Reutiliza o token existente
                    console.log("AuthContext: Sessão restaurada com sucesso.", userData);
                } else {
                    // Isso não deveria acontecer se getCurrentUser não lançar erro mas retornar nulo
                    console.warn("AuthContext: Token encontrado, mas getCurrentUser não retornou dados do usuário. Limpando token.");
                    clearAuthData();
                }
            } catch (error) {
                console.error("AuthContext: Erro ao verificar sessão (getCurrentUser falhou):", error.response?.data?.detail || error.message);
                clearAuthData(); // Token inválido ou expirado
            }
        } else {
            console.log("AuthContext: Nenhum token encontrado no localStorage.");
            clearAuthData(); // Garante que o estado esteja limpo se não houver token
        }
        setIsLoading(false); // Finaliza o carregamento após a verificação
    }, [setAuthData, clearAuthData]);

    useEffect(() => {
        checkUserSession();
    }, [checkUserSession]);

    const value = {
        user,
        isAuthenticated,
        isLoading,
        login,
        logout,
        checkUserSession, // Pode ser útil para revalidar
        setAuthData, // Expondo para casos de uso específicos (ex: OAuth)
        clearAuthData
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};
