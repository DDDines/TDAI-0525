// Frontend/app/src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';

// PASSO 1: MANTENHA ESTAS LINHAS COMENTADAS INICIALMENTE
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// Layout e Autenticação
import MainLayout from './components/MainLayout';
import ProtectedRoute from './components/ProtectedRoute';

// Páginas Principais
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ProdutosPage from './pages/ProdutosPage';
import FornecedoresPage from './pages/FornecedoresPage';
import EnriquecimentoPage from './pages/EnriquecimentoPage';
import HistoricoPage from './pages/HistoricoPage';
import PlanoPage from './pages/PlanoPage';
import ConfiguracoesPage from './pages/ConfiguracoesPage';

function App() {
  console.log("App.jsx está a ser renderizado"); // Para verificar se o componente App em si é chamado

  return (
    <Router>
      {
      <ToastContainer/>
      }
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="produtos" element={<ProdutosPage />} />
            <Route path="fornecedores" element={<FornecedoresPage />} />
            <Route path="enriquecimento" element={<EnriquecimentoPage />} />
            <Route path="historico" element={<HistoricoPage />} />
            <Route path="plano" element={<PlanoPage />} />
            <Route path="configuracoes" element={<ConfiguracoesPage />} />
          </Route>
        </Route>

        <Route path="*" element={
          <div style={{ textAlign: 'center', marginTop: '50px', fontFamily: 'Arial, sans-serif' }}>
            <h1>404 - Página Não Encontrada</h1>
            <p>Desculpe, a página que você está procurando não existe ou foi movida.</p>
            <Link to="/" style={{ color: '#3b82f6', textDecoration: 'none' }}>
              Voltar para a Página Inicial
            </Link>
          </div>
        } />
      </Routes>
    </Router>
  );
}

export default App;