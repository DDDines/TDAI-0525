/**
 * Module protected route.
 *
 * Defines responsibilities and integration points for components.
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useWorkspace } from '../contexts/WorkspaceContext';
import logger from '../utils/logger';
import LoadingOverlay from './common/LoadingOverlay.jsx';

function ProtectedRoute(

  { children, allowedRoles, requireWorkspace = true }) {
    const { isAuthenticated, user, isLoading } = useAuth();
    const { hasWorkspace, isLoading: isWorkspaceLoading } = useWorkspace();
    const location = useLocation();
    const isWorkspaceRoute = location.pathname === '/workspace';

    if (isLoading || (isAuthenticated && isWorkspaceLoading)) {
      return <LoadingOverlay isOpen={true} message="Carregando autenticacao..." />;
    }

    if (!isAuthenticated) {
      logger.log('ProtectedRoute: Usuario nao autenticado. Redirecionando para /landing.');
      return <Navigate to="/landing" state={{ from: location }} replace />;
    }

    if (requireWorkspace && !hasWorkspace && !isWorkspaceRoute) {
      logger.log('ProtectedRoute: Usuario autenticado sem empresa ativa. Redirecionando para /workspace.');
      return <Navigate to="/workspace?setup=1" state={{ from: location }} replace />;
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
  }
export default ProtectedRoute;
