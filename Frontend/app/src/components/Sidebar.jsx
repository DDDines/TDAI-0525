/**
 * Module sidebar.
 *
 * Defines responsibilities and integration points for components.
 */

import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LuBox,
  LuBoxes,
  LuBuilding2,
  LuChevronDown,
  LuGlobe,
  LuHistory,
  LuLayoutDashboard,
  LuLogOut,
  LuSearch,
  LuSettings,
  LuTag,
  LuTruck,
  LuX,
  LuZap,
} from 'react-icons/lu';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../contexts/AuthContext';
import { useWorkspace } from '../contexts/WorkspaceContext';
import dashboardService from '../services/dashboardService';
import LogoImg from '../assets/Logo.png';
import './Sidebar.css';

function usageColor(pct) {
  if (pct >= 90) return '#dc2626';
  if (pct >= 70) return '#d97706';
  return '#16a34a';
}

function SidebarUsageWidget({ isOpen, user }) {
  const { data } = useQuery({
    queryKey: ['dashboard-me'],
    queryFn: dashboardService.getMyDashboard,
    staleTime: 5 * 60_000,
    enabled: !!user && !user.is_superuser,
  });

  if (!data) return null;

  const iaUsed = Number(data.uso_mes_atual?.geracao_ia ?? 0);
  const iaLimit = Number(data.limites?.geracao_ia ?? 0);
  const webUsed = Number(data.uso_mes_atual?.enriquecimento_web ?? 0);
  const webLimit = Number(data.limites?.enriquecimento_web ?? 0);
  const iaPct = iaLimit > 0 ? Math.min((iaUsed / iaLimit) * 100, 100) : 0;
  const webPct = webLimit > 0 ? Math.min((webUsed / webLimit) * 100, 100) : 0;
  const worstPct = Math.max(iaPct, webPct);

  if (!isOpen) {
    return (
      <div
        className="sidebar-usage-mini"
        title={`Uso: IA ${Math.round(iaPct)}% · Web ${Math.round(webPct)}%`}
      >
        <span className="sidebar-usage-dot" style={{ background: usageColor(worstPct) }} />
      </div>
    );
  }

  return (
    <NavLink to="/workspace" className="sidebar-usage-widget">
      <div className="sidebar-usage-header">
        <span>Uso do plano</span>
        <span className="sidebar-usage-plan">{data.plano_nome || 'Gratuito'}</span>
      </div>
      <div className="sidebar-usage-item">
        <div className="sidebar-usage-row">
          <span className="sidebar-usage-label"><LuZap /> Geração IA</span>
          <span className="sidebar-usage-val">{iaUsed}/{iaLimit}</span>
        </div>
        <div className="sidebar-usage-track">
          <div className="sidebar-usage-fill" style={{ width: `${iaPct}%`, background: usageColor(iaPct) }} />
        </div>
      </div>
      <div className="sidebar-usage-item">
        <div className="sidebar-usage-row">
          <span className="sidebar-usage-label"><LuSearch /> Busca web</span>
          <span className="sidebar-usage-val">{webUsed}/{webLimit}</span>
        </div>
        <div className="sidebar-usage-track">
          <div className="sidebar-usage-fill" style={{ width: `${webPct}%`, background: usageColor(webPct) }} />
        </div>
      </div>
    </NavLink>
  );
}

function Sidebar({ isOpen, toggleSidebar, isMobileViewport = false }) {
  const { logout, user } = useAuth();
  const { workspace, hasWorkspace } = useWorkspace();
  const location = useLocation();
  const isAdmin = user?.is_superuser;
  const companyLabel = workspace?.nome || user?.nome_empresa || 'Configurar empresa';
  const companyHint = hasWorkspace ? 'Empresa ativa' : 'Crie ou entre em uma empresa';


  const sections = [
    {
      label: null,
      items: [
        { path: '/dashboard', name: 'Dashboard', icon: <LuLayoutDashboard />, matches: ['/dashboard'] },
      ],
    },
    {
      label: 'Catálogo',
      items: [
        { path: '/produtos', name: 'Produtos', icon: <LuBox />, matches: ['/produtos'] },
        { path: '/fornecedores', name: 'Fornecedores', icon: <LuTruck />, matches: ['/fornecedores'] },
        { path: '/tipos-de-produto', name: 'Tipos de Produto', icon: <LuTag />, matches: ['/tipos-de-produto'] },
      ],
    },
    {
      label: 'Operações',
      items: [
        { path: '/enriquecimento', name: 'Enriquecimento', icon: <LuGlobe />, matches: ['/enriquecimento'] },
        { path: '/monitoramento', name: 'Monitoramento', icon: <LuHistory />, matches: ['/monitoramento', '/historico'] },
      ],
    },
    {
      label: null,
      items: [
        { path: '/workspace', name: 'Empresa', icon: <LuBuilding2 />, matches: ['/workspace', '/financeiro'] },
        { path: '/configuracoes', name: 'Configurações', icon: <LuSettings />, matches: ['/configuracoes', ...(isAdmin ? ['/admin'] : [])] },
      ],
    },
  ];

  const isItemActive = (item) => item.matches.some((p) => location.pathname.startsWith(p));

  return (
    <aside className={`sidebar ${isOpen ? 'open' : 'closed'} ${isMobileViewport ? 'mobile' : 'desktop'}`}>
      <div className="sidebar-header">
        {isMobileViewport ? (
          <button
            type="button"
            className="sidebar-close-btn"
            aria-label="Fechar menu"
            onClick={toggleSidebar}
          >
            <LuX />
          </button>
        ) : null}

        <div className="sidebar-brand-row">
          <div className="sidebar-brand-stack">
            <div className="sidebar-brand-lockup">
              <img src={LogoImg} alt="CommerceFolio logo" className="sidebar-logo" />
              {isOpen ? (
                <div className="sidebar-brand-copy">
                  <h1 className="sidebar-title" aria-label="CommerceFolio">
                    Commerce<wbr />Folio
                  </h1>
                </div>
              ) : null}
            </div>
          </div>
        </div>

        {isOpen ? (
          <NavLink to="/workspace" className="sidebar-company-switcher" title={companyLabel}>
            <span className="sidebar-company-icon">
              <LuBuilding2 />
            </span>
            <span className="sidebar-company-copy">
              <strong>{companyLabel}</strong>
              <small>{companyHint}</small>
            </span>
            <LuChevronDown className="sidebar-company-chevron" />
          </NavLink>
        ) : null}
      </div>

      <nav className="sidebar-nav">
        {sections.map((section, si) => (
          <div key={si} className="sidebar-section">
            {section.label && isOpen ? (
              <span className="sidebar-section-label">{section.label}</span>
            ) : null}
            <ul>
              {section.items.map((item) => (
                <li key={item.name}>
                  <NavLink
                    to={item.path}
                    className={isItemActive(item) ? 'nav-link active' : 'nav-link'}
                    title={item.name}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    {isOpen ? <span className="nav-text">{item.name}</span> : null}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <SidebarUsageWidget isOpen={isOpen} user={user} />
        {isOpen && user ? (
          <div className="sidebar-user-info">
            <span className="sidebar-user-label">USUÁRIO</span>
            <span className="sidebar-user-name">{user.nome_completo || user.email?.split('@')[0]}</span>
          </div>
        ) : null}
        <button type="button" onClick={logout} className="logout-button" title="Sair">
          <LuLogOut />
          {isOpen ? <span className="nav-text">Sair</span> : null}
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
