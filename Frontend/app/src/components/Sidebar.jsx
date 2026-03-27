/**
 * Module sidebar.
 *
 * Defines responsibilities and integration points for components.
 */

import React, { useEffect, useRef, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LuBox,
  LuBoxes,
  LuBuilding2,
  LuChevronDown,
  LuChevronRight,
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

  // Persist collapsed state per section in localStorage
  const [collapsedSections, setCollapsedSections] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('sidebar-collapsed-sections') || '{}');
    } catch {
      return {};
    }
  });

  // Flyout for collapsed sidebar mode
  const [flyout, setFlyout] = useState(null); // { sectionId, top, items, label }
  const flyoutTimerRef = useRef(null);

  // --- Navigation structure ---
  const SECTIONS = [
    {
      id: 'catalog',
      label: 'Catálogo',
      icon: <LuBoxes />,
      items: [
        { path: '/produtos',        name: 'Produtos',          icon: <LuBox />,     matches: ['/produtos'] },
        { path: '/fornecedores',    name: 'Fornecedores',      icon: <LuTruck />,   matches: ['/fornecedores'] },
        { path: '/tipos-de-produto',name: 'Tipos de Produto',  icon: <LuTag />,     matches: ['/tipos-de-produto', '/importacoes'] },
      ],
    },
    {
      id: 'ops',
      label: 'Operações',
      icon: <LuZap />,
      items: [
        { path: '/enriquecimento',  name: 'Enriquecimento',    icon: <LuGlobe />,   matches: ['/enriquecimento'] },
        { path: '/monitoramento',   name: 'Monitoramento',     icon: <LuHistory />, matches: ['/monitoramento', '/historico'] },
      ],
    },
  ];

  const STANDALONE_TOP = [
    { path: '/dashboard', name: 'Dashboard', icon: <LuLayoutDashboard />, matches: ['/dashboard'] },
  ];

  const STANDALONE_BOTTOM = [
    { path: '/workspace',     name: 'Empresa',       icon: <LuBuilding2 />, matches: ['/workspace', '/financeiro'] },
    { path: '/configuracoes', name: 'Configurações',  icon: <LuSettings />, matches: ['/configuracoes', ...(isAdmin ? ['/admin'] : [])] },
  ];

  // Helpers
  const isItemActive = (item) =>
    (item.matches || [item.path]).some((p) => location.pathname.startsWith(p));

  const isSectionActive = (section) =>
    section.items.some((item) => isItemActive(item));

  // Auto-expand section when route changes to one of its pages
  useEffect(() => {
    SECTIONS.forEach((section) => {
      if (isSectionActive(section) && collapsedSections[section.id]) {
        setCollapsedSections((prev) => {
          const next = { ...prev, [section.id]: false };
          localStorage.setItem('sidebar-collapsed-sections', JSON.stringify(next));
          return next;
        });
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);

  const toggleSection = (sectionId) => {
    setCollapsedSections((prev) => {
      const next = { ...prev, [sectionId]: !prev[sectionId] };
      localStorage.setItem('sidebar-collapsed-sections', JSON.stringify(next));
      return next;
    });
  };

  // Close flyout when sidebar opens
  useEffect(() => {
    if (isOpen) setFlyout(null);
  }, [isOpen]);

  const showFlyout = (e, section) => {
    if (isOpen) return;
    clearTimeout(flyoutTimerRef.current);
    const rect = e.currentTarget.getBoundingClientRect();
    setFlyout({ sectionId: section.id, top: rect.top, items: section.items, label: section.label });
  };

  const scheduleFlyoutHide = () => {
    flyoutTimerRef.current = setTimeout(() => setFlyout(null), 160);
  };

  const cancelFlyoutHide = () => clearTimeout(flyoutTimerRef.current);

  const renderStandaloneLink = (item) => (
    <li key={item.path} className="sidebar-nav-item">
      <NavLink
        to={item.path}
        className={isItemActive(item) ? 'nav-link active' : 'nav-link'}
        title={item.name}
      >
        <span className="nav-icon">{item.icon}</span>
        {isOpen ? <span className="nav-text">{item.name}</span> : null}
      </NavLink>
    </li>
  );

  return (
    <aside className={`sidebar ${isOpen ? 'open' : 'closed'} ${isMobileViewport ? 'mobile' : 'desktop'}`}>

      {/* ── Header ────────────────────────────────────── */}
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
            <span className="sidebar-company-icon"><LuBuilding2 /></span>
            <span className="sidebar-company-copy">
              <strong>{companyLabel}</strong>
              <small>{companyHint}</small>
            </span>
            <LuChevronDown className="sidebar-company-chevron" />
          </NavLink>
        ) : null}
      </div>

      {/* ── Navigation ────────────────────────────────── */}
      <nav className="sidebar-nav">

        {/* Standalone top items (Dashboard) */}
        <ul className="sidebar-nav-list">
          {STANDALONE_TOP.map(renderStandaloneLink)}
        </ul>

        {/* Collapsible sections */}
        {SECTIONS.map((section) => {
          const isCollapsed = !!collapsedSections[section.id];
          const sectionActive = isSectionActive(section);

          if (!isOpen) {
            // Icon-only mode → flyout trigger
            return (
              <ul key={section.id} className="sidebar-nav-list sidebar-nav-list--section-gap">
                <li className="sidebar-nav-item">
                  <div
                    className={`nav-link sidebar-section-trigger${sectionActive ? ' section-has-active' : ''}`}
                    onMouseEnter={(e) => showFlyout(e, section)}
                    onMouseLeave={scheduleFlyoutHide}
                    title={section.label}
                    role="button"
                    tabIndex={0}
                  >
                    <span className="nav-icon">{section.icon}</span>
                  </div>
                </li>
              </ul>
            );
          }

          // Expanded mode → collapsible section
          return (
            <div key={section.id} className="sidebar-section sidebar-nav-list--section-gap">
              <button
                type="button"
                className={`sidebar-section-header${sectionActive ? ' section-has-active' : ''}`}
                onClick={() => toggleSection(section.id)}
                aria-expanded={!isCollapsed}
              >
                <span className="sidebar-section-label">{section.label}</span>
                <LuChevronRight
                  className={`sidebar-section-chevron${isCollapsed ? '' : ' rotated'}`}
                />
              </button>

              <div className={`sidebar-subitems${isCollapsed ? ' collapsed' : ''}`}>
                <ul className="sidebar-nav-list">
                  {section.items.map((item) => (
                    <li key={item.path} className="sidebar-nav-item">
                      <NavLink
                        to={item.path}
                        className={isItemActive(item) ? 'nav-link nav-link--sub active' : 'nav-link nav-link--sub'}
                        title={item.name}
                      >
                        <span className="nav-icon">{item.icon}</span>
                        <span className="nav-text">{item.name}</span>
                      </NavLink>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          );
        })}

        {/* Standalone bottom items (Empresa, Configurações) */}
        <ul className="sidebar-nav-list sidebar-nav-list--section-gap">
          {STANDALONE_BOTTOM.map(renderStandaloneLink)}
        </ul>

      </nav>

      {/* ── Flyout panel (collapsed mode only) ────────── */}
      {flyout && !isOpen ? (
        <div
          className="sidebar-flyout"
          style={{ top: flyout.top }}
          onMouseEnter={cancelFlyoutHide}
          onMouseLeave={scheduleFlyoutHide}
        >
          <div className="sidebar-flyout-label">{flyout.label}</div>
          {flyout.items.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={isItemActive(item) ? 'sidebar-flyout-link active' : 'sidebar-flyout-link'}
              onClick={() => setFlyout(null)}
            >
              <span className="sidebar-flyout-icon">{item.icon}</span>
              {item.name}
            </NavLink>
          ))}
        </div>
      ) : null}

      {/* ── Footer ────────────────────────────────────── */}
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
