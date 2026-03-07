/**
 * Module sidebar.
 *
 * Defines responsibilities and integration points for components.
 */

import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useAppExperience } from '../contexts/AppExperienceContext';
import './Sidebar.css';
import LogoImg from '../assets/Logo.png';
import {
  LuLayoutDashboard,
  LuBox,
  LuUsers,
  LuTag,
  LuHistory,
  LuSettings,
  LuLogOut,
  LuZap,
  LuLayers } from
'react-icons/lu';

function Sidebar(

  { isOpen }) {
    const { logout } = useAuth();
    const { effectiveMode } = useAppExperience();
    const isCompleteMode = effectiveMode === 'complete';

    const handleLogout = () => {
      logout();
    };

    const menuItems = [
    { path: '/dashboard', name: 'Dashboard', icon: <LuLayoutDashboard /> },
    { path: '/produtos', name: 'Produtos', icon: <LuBox /> },
    { path: '/fornecedores', name: 'Fornecedores', icon: <LuUsers /> },
    { path: '/tipos-de-produto', name: 'Tipos de Produto', icon: <LuTag /> },
    { path: '/enriquecimento', name: 'Enriquecimento', icon: <LuZap /> },
    { path: '/historico', name: 'Histórico', icon: <LuHistory /> },
    { path: '/plano', name: 'Meu Plano', icon: <LuLayers /> },
    { path: '/configuracoes', name: 'Configurações', icon: <LuSettings /> }];


    return (
      <aside className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      <div className="sidebar-header">
        <img src={LogoImg} alt="CatalogAI logo" className="sidebar-logo" />
        {isOpen && <h1 className="sidebar-title">CatalogAI</h1>}
        {isOpen &&
        <span className={`sidebar-mode-chip ${isCompleteMode ? 'complete' : 'basic'}`}>
            {isCompleteMode ? 'Modo Completo' : 'Modo Básico'}
          </span>
        }
      </div>
      <nav className="sidebar-nav">
        <ul>
          {menuItems.map((item) =>
            <li key={item.name}>
              <NavLink
                to={item.path}
                className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}
                title={item.name}>

                <span className="nav-icon">{item.icon}</span>
                {isOpen && <span className="nav-text">{item.name}</span>}
              </NavLink>
            </li>
            )}
        </ul>
      </nav>
      <div className="sidebar-footer">
        <button onClick={handleLogout} className="logout-button" title="Sair">
          <LuLogOut />
          {isOpen && <span className="nav-text">Sair</span>}
        </button>
      </div>
    </aside>);

  }
export default Sidebar;
