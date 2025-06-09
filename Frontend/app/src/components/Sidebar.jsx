import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext'; // Se precisar do logout ou dados do usuário
import './Sidebar.css'; // Certifique-se de que este arquivo CSS existe e está correto

// Ícones (exemplo, substitua pelos seus ou remova se não usar)
import {
  LuLayoutDashboard,
  LuBox,
  LuUsers,
  LuTag,
  LuFileText,
  LuHistory,
  LuSettings,
  LuLogOut,
  LuZap, // Ícone para Enriquecimento
  LuLayers // Ícone para Plano/Assinatura
} from 'react-icons/lu'; // Exemplo com react-icons

const Sidebar = ({ isOpen, toggleSidebar }) => {
  const { user, logout } = useAuth(); // Obtenha o usuário e a função de logout do AuthContext

  const handleLogout = () => {
    logout();
    // navigate('/login'); // O logout no AuthContext já deve redirecionar
  };

  const menuItems = [
    { path: "/dashboard", name: "Dashboard", icon: <LuLayoutDashboard /> },
    { path: "/produtos", name: "Produtos", icon: <LuBox /> },
    { path: "/fornecedores", name: "Fornecedores", icon: <LuUsers /> },
    { path: "/tipos-de-produto", name: "Tipos de Produto", icon: <LuTag /> }, // <-- ROTA CORRIGIDA
    { path: "/enriquecimento", name: "Enriquecimento", icon: <LuZap /> },
    { path: "/historico", name: "Histórico", icon: <LuHistory /> },
    { path: "/plano", name: "Meu Plano", icon: <LuLayers /> },
    { path: "/configuracoes", name: "Configurações", icon: <LuSettings /> },
  ];

  return (
    <aside className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      <div className="sidebar-header">
        {/* Pode adicionar um logo ou título aqui */}
        <h1 className="sidebar-title">{isOpen ? "TDAI" : "T"}</h1>
        {/* O botão de toggle pode ser movido para o Topbar se preferir */}
        {/* <button onClick={toggleSidebar} className="sidebar-toggle-btn">
          {isOpen ? <LuX /> : <LuMenu />}
        </button> */}
      </div>
      <nav className="sidebar-nav">
        <ul>
          {menuItems.map((item) => (
            <li key={item.name}>
              <NavLink
                to={item.path}
                className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                title={item.name}
              >
                <span className="nav-icon">{item.icon}</span>
                {isOpen && <span className="nav-text">{item.name}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="sidebar-footer">
        {user && isOpen && (
          <div className="user-info">
            {/* <p>Bem-vindo, {user.nome_completo || user.email}!</p> */}
          </div>
        )}
        <button onClick={handleLogout} className="logout-button" title="Sair">
          <LuLogOut />
          {isOpen && <span className="nav-text">Sair</span>}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
