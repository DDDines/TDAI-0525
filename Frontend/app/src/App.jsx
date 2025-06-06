import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ProductTypeProvider } from './contexts/ProductTypeContext'; // Certifique-se que o caminho está correto
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import MainLayout from './components/MainLayout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ProdutosPage from './pages/ProdutosPage';
import FornecedoresPage from './pages/FornecedoresPage';
import TiposProdutoPage from './pages/TiposProdutoPage';
import EnriquecimentoPage from './pages/EnriquecimentoPage';
import HistoricoPage from './pages/HistoricoPage';
import PlanoPage from './pages/PlanoPage';
import ConfiguracoesPage from './pages/ConfiguracoesPage';
import ProtectedRoute from './components/ProtectedRoute';
// Importe outras páginas e componentes necessários

import './App.css';
import logger from './utils/logger';

function AppContent() {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  useEffect(() => {
    logger.log("App.jsx: Auth state changed - isAuthenticated:", isAuthenticated, "isLoading:", isLoading, "path:", location.pathname);
  }, [isAuthenticated, isLoading, location.pathname]);

  // Se ainda estiver carregando a informação de autenticação, pode mostrar um loader global
  // ou deixar o ProtectedRoute lidar com isso individualmente.
  // Para evitar piscar a tela de login, é bom ter um estado de carregamento aqui.
  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <h2>Carregando Aplicação...</h2>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      
      {/* Rotas Protegidas */}
      <Route 
        path="/" 
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} /> {/* Redireciona / para /dashboard */}
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="produtos" element={<ProdutosPage />} />
        <Route path="fornecedores" element={<FornecedoresPage />} />
        <Route path="tipos-de-produto" element={<TiposProdutoPage />} />
        <Route path="enriquecimento" element={<EnriquecimentoPage />} />
        <Route path="historico" element={<HistoricoPage />} />
        <Route path="plano" element={<PlanoPage />} />
        <Route path="configuracoes" element={<ConfiguracoesPage />} />
        {/* Adicione outras rotas filhas de MainLayout aqui */}
      </Route>

      {/* Rota para página não encontrada ou outras rotas públicas */}
      <Route path="*" element={<div>Página não encontrada</div>} />
    </Routes>
  );
}

function App() {
  useEffect(() => {
    logger.log("App.jsx está a ser renderizado com AuthProvider e ProductTypeProvider");
  }, []);

  return (
    <Router>
      <AuthProvider>
        <ProductTypeProvider> {/* Envolve com ProductTypeProvider se ele também usa useAuth ou precisa estar no contexto */}
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
            theme="colored"
          />
        </ProductTypeProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;

