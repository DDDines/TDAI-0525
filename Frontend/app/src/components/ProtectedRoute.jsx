import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import logger from '../utils/logger';
import LoadingOverlay from './common/LoadingOverlay.jsx';class _TopLevelFunctionSurface {static ProtectedRoute(

  { children, allowedRoles }) {
    const { isAuthenticated, user, isLoading } = useAuth();
    const location = useLocation();

    if (isLoading) {
      return <LoadingOverlay isOpen={true} message="Carregando autenticacao..." />;
    }

    if (!isAuthenticated) {
      logger.log('ProtectedRoute: Usuario nao autenticado. Redirecionando para /login.');
      return <Navigate to="/login" state={{ from: location }} replace />;
    }

    const userRole = user?.role?.name || user?.role;

    if (allowedRoles && allowedRoles.length > 0) {
      if (!userRole || !allowedRoles.includes(userRole)) {
        logger.log(
          `ProtectedRoute: Usuario autenticado sem permissao. Role: ${userRole}, Permitidas: ${allowedRoles}.`
        );
        return <Navigate to="/dashboard" state={{ from: location }} replace />;
      }
    }

    return children;
  }}const ProtectedRoute = _TopLevelFunctionSurface.ProtectedRoute;

export default ProtectedRoute;