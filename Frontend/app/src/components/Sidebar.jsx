// Frontend/app/src/components/Sidebar.jsx
import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext'; // Importar useAuth

// Ícones (exemplo, substitua pelos seus ou por uma biblioteca de ícones)
const DashboardIcon = () => <span>📊</span>;
const ProductsIcon = () => <span>📦</span>;
const TypesIcon = () => <span>🏷️</span>; // Novo ícone para Tipos de Produto
const SuppliersIcon = () => <span>🚚</span>;
const EnrichmentIcon = () => <span>✨</span>;
const HistoryIcon = () => <span>📜</span>;
const PlanIcon = () => <span>💳</span>;
const SettingsIcon = () => <span>⚙️</span>;
const LogoutIcon = () => <span>🚪</span>;


function Sidebar() {
  const { user, logout } = useAuth(); // Obter o usuário do contexto
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    // O AuthContext já deve cuidar do redirecionamento via navigate('/login')
  };

  // Apenas mostrar a sidebar se o usuário estiver logado
  // O ProtectedRoute já cuida do acesso, mas isso evita renderizar a sidebar na tela de login se não desejado.
  if (!user) {
    return null;
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-logo-icon">🚀</span>
        <h1 className="sidebar-logo-text">TDAI</h1>
      </div>
      <nav className="sidebar-nav">
        <NavLink to="/dashboard" className={({ isActive }) => isActive ? "sidebar-link active" : "sidebar-link"}>
          <DashboardIcon /> Dashboard
        </NavLink>
        <NavLink to="/produtos" className={({ isActive }) => isActive ? "sidebar-link active" : "sidebar-link"}>
          <ProductsIcon /> Produtos
        </NavLink>
        {/* Adicionar link para Tipos de Produto */}
        {user && user.is_superuser && ( // Mostrar apenas para superusuários, por exemplo
          <NavLink to="/tipos-produto" className={({ isActive }) => isActive ? "sidebar-link active" : "sidebar-link"}>
            <TypesIcon /> Tipos de Produto
          </NavLink>
        )}
        <NavLink to="/fornecedores" className={({ isActive }) => isActive ? "sidebar-link active" : "sidebar-link"}>
          <SuppliersIcon /> Fornecedores
        </NavLink>
        <NavLink to="/enriquecimento" className={({ isActive }) => isActive ? "sidebar-link active" : "sidebar-link"}>
          <EnrichmentIcon /> Enriquecimento
        </NavLink>
        <NavLink to="/historico" className={({ isActive }) => isActive ? "sidebar-link active" : "sidebar-link"}>
          <HistoryIcon /> Histórico
        </NavLink>
        <NavLink to="/plano" className={({ isActive }) => isActive ? "sidebar-link active" : "sidebar-link"}>
          <PlanIcon /> Meu Plano
        </NavLink>
        <NavLink to="/configuracoes" className={({ isActive }) => isActive ? "sidebar-link active" : "sidebar-link"}>
          <SettingsIcon /> Configurações
        </NavLink>
      </nav>
      <div className="sidebar-footer">
        <button onClick={handleLogout} className="sidebar-link logout-button">
          <LogoutIcon /> Sair
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;