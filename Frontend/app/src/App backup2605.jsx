// Frontend/app/src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';

// Layout e Autenticação
import MainLayout from './components/MainLayout';
import ProtectedRoute from './components/ProtectedRoute';

// Páginas Principais
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ProdutosPage from './pages/ProdutosPage'; // Certifique-se que este arquivo existe e exporta um componente

// Páginas da Sidebar (placeholders ou completas)
// Certifique-se que todos estes arquivos existem em './pages/' e exportam um componente React
import FornecedoresPage from './pages/FornecedoresPage';
import EnriquecimentoPage from './pages/EnriquecimentoPage';
import HistoricoPage from './pages/HistoricoPage';
import PlanoPage from './pages/PlanoPage';
import ConfiguracoesPage from './pages/ConfiguracoesPage';

// Páginas futuras (descomente e crie os arquivos quando precisar)
// import RegisterPage from './pages/RegisterPage';
// import PasswordRecoveryPage from './pages/PasswordRecoveryPage';
// import ResetPasswordPage from './pages/ResetPasswordPage';


function App() {
  return (
    <Router>
      <Routes>
        {/* Rotas públicas que NÃO usam o MainLayout */}
        <Route path="/login" element={<LoginPage />} />
        {/* Descomente e crie estas rotas quando for implementar:
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/password-recovery" element={<PasswordRecoveryPage />} />
          <Route path="/reset-password/:token" element={<ResetPasswordPage />} /> 
        */}

        {/* Rotas protegidas que usam o MainLayout */}
        <Route element={<ProtectedRoute />}> {/* Verifica autenticação */}
          <Route path="/" element={<MainLayout />}> {/* Aplica o layout com Sidebar/Topbar */}
            {/* Rota padrão para / vai para /dashboard se autenticado */}
            <Route index element={<Navigate to="/dashboard" replace />} />
            
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="produtos" element={<ProdutosPage />} />
            <Route path="fornecedores" element={<FornecedoresPage />} />
            <Route path="enriquecimento" element={<EnriquecimentoPage />} />
            <Route path="historico" element={<HistoricoPage />} />
            <Route path="plano" element={<PlanoPage />} />
            <Route path="configuracoes" element={<ConfiguracoesPage />} />
            
            {/* Adicione outras rotas internas aqui conforme necessário */}
          </Route>
        </Route>

        {/* Rota para página não encontrada */}
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
