// Frontend/app/src/App.jsx
import React from 'react';
// Adicionado 'Link' à importação de react-router-dom
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// Context Providers
import { AuthProvider } from './contexts/AuthContext';
import { ProductTypeProvider } from './contexts/ProductTypeContext';

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
// Importe a nova página de Tipos de Produto quando ela for criada
// import TiposProdutoPage from './pages/TiposProdutoPage';

function App() {
  console.log("App.jsx está a ser renderizado com AuthProvider e ProductTypeProvider");

  return (
    <Router>
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
        theme="light"
      />
      <AuthProvider> {/* Provider de Autenticação envolvendo tudo */}
        <ProductTypeProvider> {/* Provider de Tipos de Produto */}
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            
            {/* Rotas Protegidas que usam MainLayout */}
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<MainLayout />}>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="produtos" element={<ProdutosPage />} />
                {/* Adicione a rota para TiposProdutoPage aqui quando criar a página */}
                {/* Exemplo: <Route path="tipos-produto" element={<TiposProdutoPage />} /> */}
                <Route path="fornecedores" element={<FornecedoresPage />} />
                <Route path="enriquecimento" element={<EnriquecimentoPage />} />
                <Route path="historico" element={<HistoricoPage />} />
                <Route path="plano" element={<PlanoPage />} />
                <Route path="configuracoes" element={<ConfiguracoesPage />} />
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
        </ProductTypeProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;