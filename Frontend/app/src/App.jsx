/**
 * Module app.
 *
 * Defines responsibilities and integration points for frontend.
 */

import React, { useEffect } from 'react';
import {
  BrowserRouter as Router,
  Navigate,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import { AuthProvider, useAuth } from './contexts/AuthContext';
import { AppExperienceProvider } from './contexts/AppExperienceContext';
import { ProductTypeProvider } from './contexts/ProductTypeContext';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import { WorkspaceProvider, useWorkspace } from './contexts/WorkspaceContext';

import MainLayout from './components/MainLayout';
import ProtectedRoute from './components/ProtectedRoute';
import LoadingOverlay from './components/common/LoadingOverlay.jsx';

import AcceptInvitePage from './pages/AcceptInvitePage';
import AdminPage from './pages/AdminPage';
import ConfiguracoesPage from './pages/ConfiguracoesPage';
import DashboardPage from './pages/DashboardPage';
import EnriquecimentoPage from './pages/EnriquecimentoPage';
import FornecedoresPage from './pages/FornecedoresPage';
import HistoricoPage from './pages/HistoricoPage';
import ImportReviewPage from './pages/ImportReviewPage';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import OAuthCallbackPage from './pages/OAuthCallbackPage';
import PlanoPage from './pages/PlanoPage';
import ProdutoConteudoPage from './pages/ProdutoConteudoPage';
import ProdutosPage from './pages/ProdutosPage';
import RecuperarSenhaPage from './pages/RecuperarSenhaPage';
import ResetSenhaPage from './pages/ResetSenhaPage';
import SignupPage from './pages/SignupPage';
import TiposProdutoPage from './pages/TiposProdutoPage';
import WorkspacePage from './pages/WorkspacePage';

import './App.css';
import logger from './utils/logger';

function AppContent() {
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const { hasWorkspace, isLoading: isWorkspaceLoading } = useWorkspace();
  const location = useLocation();

  useEffect(() => {
    logger.log(
      'App.jsx: estado de sessao alterado',
      'isAuthenticated:',
      isAuthenticated,
      'authLoading:',
      isAuthLoading,
      'workspaceLoading:',
      isWorkspaceLoading,
      'hasWorkspace:',
      hasWorkspace,
      'path:',
      location.pathname
    );
  }, [hasWorkspace, isAuthenticated, isAuthLoading, isWorkspaceLoading, location.pathname]);

  if (isAuthLoading || (isAuthenticated && isWorkspaceLoading)) {
    return <LoadingOverlay isOpen={true} message="Carregando Aplicação..." />;
  }

  const authenticatedHomeRoute = hasWorkspace ? '/dashboard' : '/workspace?setup=1';

  return (
    <Routes>
      <Route
        path="/"
        element={isAuthenticated ? <Navigate to={authenticatedHomeRoute} replace /> : <LandingPage />}
      />
      <Route path="/landing" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/recuperar-senha" element={<RecuperarSenhaPage />} />
      <Route path="/resetar-senha" element={<ResetSenhaPage />} />
      <Route path="/auth/oauth-callback" element={<OAuthCallbackPage />} />
      <Route path="/invite/:token" element={<AcceptInvitePage />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to={authenticatedHomeRoute} replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="produtos" element={<ProdutosPage />} />
        <Route path="produtos/:produtoId/conteudo" element={<ProdutoConteudoPage />} />
        <Route path="fornecedores" element={<FornecedoresPage />} />
        <Route path="importacoes/:fileId/quarentena" element={<ImportReviewPage />} />
        <Route path="tipos-de-produto" element={<TiposProdutoPage />} />
        <Route path="enriquecimento" element={<EnriquecimentoPage />} />
        <Route path="monitoramento" element={<HistoricoPage />} />
        <Route path="historico" element={<Navigate to="/monitoramento" replace />} />
        <Route path="financeiro" element={<PlanoPage />} />
        <Route path="plano" element={<Navigate to="/financeiro" replace />} />
        <Route path="configuracoes" element={<ConfiguracoesPage />} />
        <Route path="workspace" element={<WorkspacePage />} />
        <Route path="admin" element={<AdminPage />} />
      </Route>

      <Route
        path="*"
        element={<Navigate to={isAuthenticated ? authenticatedHomeRoute : '/landing'} replace />}
      />
    </Routes>
  );
}

function ProvidersWrapper() {
  const { mode } = useTheme();

  return (
    <>
      <AppContent />
      <ToastContainer
        position="top-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme={mode === 'dark' ? 'dark' : 'colored'}
      />
    </>
  );
}

function App() {
  useEffect(() => {
    logger.log('App.jsx está a ser renderizado com AuthProvider e ProductTypeProvider');
  }, []);

  return (
    <Router>
      <ThemeProvider>
        <AuthProvider>
          <WorkspaceProvider>
            <AppExperienceProvider>
              <ProductTypeProvider>
                <ProvidersWrapper />
              </ProductTypeProvider>
            </AppExperienceProvider>
          </WorkspaceProvider>
        </AuthProvider>
      </ThemeProvider>
    </Router>
  );
}

export default App;
