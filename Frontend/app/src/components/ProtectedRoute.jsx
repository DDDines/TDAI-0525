// Frontend/app/src/components/ProtectedRoute.jsx
import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';

const isAuthenticated = () => {
  // Verifica se o token de acesso existe no localStorage
  return !!localStorage.getItem('accessToken');
};

function ProtectedRoute({ children }) {
  if (!isAuthenticated()) {
    // Redireciona para a página de login se não estiver autenticado
    return <Navigate to="/login" replace />;
  }

  // Se `children` for fornecido (para rotas que não usam <Outlet /> diretamente no ProtectedRoute)
  if (children) {
    return children;
  }

  // Renderiza o <Outlet /> para rotas aninhadas (como quando usado com MainLayout)
  return <Outlet />; 
}

export default ProtectedRoute;