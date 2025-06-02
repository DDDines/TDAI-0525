// Frontend/app/src/components/ProtectedRoute.jsx
import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext'; // Importa o hook useAuth do nosso AuthContext

function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoadingAuth } = useAuth();
  const location = useLocation();

  if (isLoadingAuth) {
    // Enquanto o AuthContext estiver verificando o estado de autenticação,
    // você pode exibir um loader global ou simplesmente não renderizar nada.
    // Retornar null ou um componente de carregamento é uma boa prática.
    // Exemplo: return <SpinnerGlobal />; ou
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        Carregando autenticação...
      </div>
    ); 
  }

  if (!isAuthenticated) {
    // Se não estiver autenticado (após o carregamento inicial ter sido concluído),
    // redireciona para a página de login.
    // Passamos o `location` atual para que o usuário possa ser redirecionado
    // de volta para a página que tentava acessar após o login.
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Se `children` for fornecido (para rotas que não usam <Outlet /> diretamente no ProtectedRoute,
  // embora seja menos comum com a estrutura atual de <Outlet />).
  if (children) {
    return children;
  }

  // Se autenticado e o carregamento inicial terminou, renderiza o <Outlet />
  // para as rotas aninhadas (como quando usado com MainLayout).
  return <Outlet />;
}

export default ProtectedRoute;