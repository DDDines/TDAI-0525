import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = ({ children, allowedRoles }) => {
    const { isAuthenticated, user, isLoading } = useAuth();
    const location = useLocation();

    if (isLoading) {
        // Enquanto o AuthContext está verificando a sessão,
        // pode-se exibir um loader global ou simplesmente não renderizar nada ainda.
        // Retornar null ou um spinner evita renderização prematura da página de login
        // ou do conteúdo protegido.
        return <div>Carregando autenticação...</div>; // Ou um componente de Spinner/Loading
    }

    if (!isAuthenticated) {
        // Usuário não está logado, redireciona para a página de login.
        // Salva a localização atual para que possamos enviar o usuário de volta após o login.
        console.log("ProtectedRoute: Usuário não autenticado. Redirecionando para /login.");
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    // Verifica se o usuário tem uma das roles permitidas (se allowedRoles for fornecido)
    // Supondo que user.role.name exista e seja uma string.
    // Se user.role for um objeto, ajuste para user.role.name ou user.role_name etc.
    // Se o seu modelo de usuário no frontend não tiver 'role.name',
    // você pode precisar buscar o role do usuário ou ajustar essa lógica.
    // Por enquanto, vamos assumir que user.role é uma string ou que user.role.name existe.
    
    // Ajuste esta lógica de role conforme a estrutura do seu objeto 'user' no AuthContext
    const userRole = user?.role?.name || user?.role; // Tenta user.role.name, depois user.role

    if (allowedRoles && allowedRoles.length > 0) {
        if (!userRole || !allowedRoles.includes(userRole)) {
            console.log(`ProtectedRoute: Usuário autenticado mas sem permissão. Role: ${userRole}, Permitidas: ${allowedRoles}. Redirecionando para /nao-autorizado ou dashboard.`);
            // Redireciona para uma página de "Não Autorizado" ou para o dashboard como fallback
            return <Navigate to="/dashboard" state={{ from: location }} replace />; // Ou para uma página específica de "Não Autorizado"
        }
    }

    return children; // Usuário está autenticado (e tem a role, se especificado)
};

export default ProtectedRoute;
