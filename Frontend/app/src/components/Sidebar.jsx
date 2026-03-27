/**
 * Module sidebar.
 *
 * Defines responsibilities and integration points for components.
 */

import React, { useEffect, useRef, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  LuBox,
  LuBoxes,
  LuBuilding2,
  LuChevronDown,
  LuChevronRight,
  LuExternalLink,
  LuGlobe,
  LuHistory,
  LuLayoutDashboard,
  LuLogOut,
  LuMoon,
  LuSearch,
  LuSettings,
  LuSun,
  LuTag,
  LuTruck,
  LuWalletCards,
  LuX,
  LuZap,
} from 'react-icons/lu';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../contexts/AuthContext';
import { useWorkspace } from '../contexts/WorkspaceContext';
import { useTheme } from '../contexts/ThemeContext';
import dashboardService from '../services/dashboardService';
import LogoImg from '../assets/Logo.png';
import './Sidebar.css';

/* ── Helpers ─────────────────────────────────────────────────── */

function usageColor(pct) {
  if (pct >= 90) return '#dc2626';
  if (pct >= 70) return '#d97706';
  return '#16a34a';
}

function getInitials(name) {
  if (!name || typeof name !== 'string') return '--';
  const parts = name.split(' ').filter(Boolean);
  let i = parts[0][0].toUpperCase();
  if (parts.length > 1) i += parts[parts.length - 1][0].toUpperCase();
  return i;
}

/* ── Usage widget ─────────────────────────────────────────────── */

function SidebarUsageWidget({ isOpen, user }) {
  const { data } = useQuery({
    queryKey: ['dashboard-me'],
    queryFn: dashboardService.getMyDashboard,
    staleTime: 5 * 60_000,
    enabled: !!user && !user.is_superuser,
  });

  if (!data) return null;

  const iaUsed  = Number(data.uso_mes_atual?.geracao_ia      ?? 0);
  const iaLimit = Number(data.limites?.geracao_ia             ?? 0);
  const webUsed  = Number(data.uso_mes_atual?.enriquecimento_web ?? 0);
  const webLimit = Number(data.limites?.enriquecimento_web    ?? 0);
  const iaPct  = iaLimit  > 0 ? Math.min((iaUsed  / iaLimit)  * 100, 100) : 0;
  const webPct = webLimit > 0 ? Math.min((webUsed / webLimit) * 100, 100) : 0;
  const worstPct = Math.max(iaPct, webPct);

  if (!isOpen) {
    return (
      <div className="sidebar-usage-mini" title={`Uso: IA ${Math.round(iaPct)}% · Web ${Math.round(webPct)}%`}>
        <span className="sidebar-usage-dot" style={{ background: usageColor(worstPct) }} />
      </div>
    );
  }

  return (
    <NavLink to="/financeiro" className="sidebar-usage-widget">
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

/* ── Main component ───────────────────────────────────────────── */

function Sidebar({ isOpen, toggleSidebar, isMobileViewport = false }) {
  const { logout, user } = useAuth();
  const { workspace, hasWorkspace } = useWorkspace();
  const { mode, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const isAdmin = user?.is_superuser;

  const companyLabel = workspace?.nome || user?.nome_empresa || 'Configurar empresa';
  const companyHint  = hasWorkspace ? 'Empresa ativa' : 'Crie ou entre em uma empresa';

  /* collapsed-section state (persisted) */
  const [collapsedSections, setCollapsedSections] = useState(() => {
    try { return JSON.parse(localStorage.getItem('sidebar-collapsed-sections') || '{}'); }
    catch { return {}; }
  });

  /* dropdown states */
  const [companyOpen, setCompanyOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  /* section flyout (collapsed sidebar) */
  const [flyout, setFlyout] = useState(null);
  const flyoutTimerRef = useRef(null);

  /* click-outside refs */
  const companyRef = useRef(null);
  const userMenuRef = useRef(null);

  /* ── Navigation structure ────────────────────────────────────── */
  const SECTIONS = [
    {
      id: 'catalog',
      label: 'Catálogo',
      icon: <LuBoxes />,
      items: [
        { path: '/produtos',         name: 'Produtos',         icon: <LuBox />,     matches: ['/produtos'] },
        { path: '/fornecedores',     name: 'Fornecedores',     icon: <LuTruck />,   matches: ['/fornecedores'] },
        { path: '/tipos-de-produto', name: 'Tipos de Produto', icon: <LuTag />,     matches: ['/tipos-de-produto', '/importacoes'] },
      ],
    },
    {
      id: 'ops',
      label: 'Operações',
      icon: <LuZap />,
      items: [
        { path: '/enriquecimento', name: 'Enriquecimento', icon: <LuGlobe />,   matches: ['/enriquecimento'] },
        { path: '/monitoramento',  name: 'Monitoramento',  icon: <LuHistory />, matches: ['/monitoramento', '/historico'] },
      ],
    },
  ];

  const STANDALONE_TOP = [
    { path: '/dashboard', name: 'Dashboard', icon: <LuLayoutDashboard />, matches: ['/dashboard'] },
  ];

  const STANDALONE_BOTTOM = [
    { path: '/workspace',     name: 'Empresa',      icon: <LuBuilding2 />, matches: ['/workspace', '/financeiro'] },
    { path: '/configuracoes', name: 'Configurações', icon: <LuSettings />, matches: ['/configuracoes', ...(isAdmin ? ['/admin'] : [])] },
  ];

  /* ── Helpers ─────────────────────────────────────────────────── */
  const isItemActive    = (item) => (item.matches || [item.path]).some((p) => location.pathname.startsWith(p));
  const isSectionActive = (section) => section.items.some((item) => isItemActive(item));

  /* auto-expand section on route change */
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

  const toggleSection = (id) => {
    setCollapsedSections((prev) => {
      const next = { ...prev, [id]: !prev[id] };
      localStorage.setItem('sidebar-collapsed-sections', JSON.stringify(next));
      return next;
    });
  };

  /* close flyout when sidebar opens */
  useEffect(() => { if (isOpen) setFlyout(null); }, [isOpen]);

  /* close dropdowns on outside click */
  useEffect(() => {
    function handle(e) {
      if (companyRef.current && !companyRef.current.contains(e.target)) setCompanyOpen(false);
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) setUserMenuOpen(false);
    }
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  /* flyout handlers */
  const showFlyout = (e, section) => {
    if (isOpen) return;
    clearTimeout(flyoutTimerRef.current);
    const rect = e.currentTarget.getBoundingClientRect();
    setFlyout({ sectionId: section.id, top: rect.top, items: section.items, label: section.label });
  };
  const scheduleFlyoutHide = () => { flyoutTimerRef.current = setTimeout(() => setFlyout(null), 160); };
  const cancelFlyoutHide   = () => clearTimeout(flyoutTimerRef.current);

  /* ── Render helpers ──────────────────────────────────────────── */
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

  /* user display */
  const userName    = user?.nome_completo || user?.email || 'Usuário';
  const userEmail   = user?.email || '';
  const userInitials = getInitials(userName);
  const avatarUrl   = user?.avatar_url || '';

  /* ── JSX ─────────────────────────────────────────────────────── */
  return (
    <aside className={`sidebar ${isOpen ? 'open' : 'closed'} ${isMobileViewport ? 'mobile' : 'desktop'}`}>

      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="sidebar-header">
        {isMobileViewport ? (
          <button type="button" className="sidebar-close-btn" aria-label="Fechar menu" onClick={toggleSidebar}>
            <LuX />
          </button>
        ) : null}

        <div className="sidebar-brand-row">
          <div className="sidebar-brand-lockup">
            <img src={LogoImg} alt="CommerceFolio" className="sidebar-logo" />
            {isOpen ? <h1 className="sidebar-title">Commerce<wbr />Folio</h1> : null}
          </div>
        </div>

        {/* Company switcher */}
        <div className="sidebar-company-wrapper" ref={companyRef}>
          <button
            type="button"
            className={`sidebar-company-switcher${companyOpen ? ' open' : ''}`}
            onClick={() => setCompanyOpen((v) => !v)}
            title={companyLabel}
          >
            <span className="sidebar-company-icon"><LuBuilding2 /></span>
            {isOpen ? (
              <>
                <span className="sidebar-company-copy">
                  <strong>{companyLabel}</strong>
                  <small>{companyHint}</small>
                </span>
                <LuChevronDown className={`sidebar-company-chevron${companyOpen ? ' flipped' : ''}`} />
              </>
            ) : null}
          </button>

          {/* Company dropdown */}
          {companyOpen ? (
            <div className={`sidebar-dropdown${isOpen ? ' sidebar-dropdown--inline' : ' sidebar-dropdown--flyout'}`}>
              <div className="sidebar-dropdown-label">Empresa ativa</div>
              <div className="sidebar-dropdown-item sidebar-dropdown-item--active">
                <span className="sidebar-dropdown-check">✓</span>
                <span>{companyLabel}</span>
              </div>
              <div className="sidebar-dropdown-divider" />
              <button
                type="button"
                className="sidebar-dropdown-item"
                onClick={() => { setCompanyOpen(false); navigate('/workspace'); }}
              >
                <span className="sidebar-dropdown-icon"><LuExternalLink /></span>
                <span>Gerenciar empresa</span>
              </button>
            </div>
          ) : null}
        </div>
      </div>

      {/* ── Navigation ──────────────────────────────────────────── */}
      <nav className="sidebar-nav">

        {/* Standalone top */}
        <ul className="sidebar-nav-list">
          {STANDALONE_TOP.map(renderStandaloneLink)}
        </ul>

        {/* Collapsible sections */}
        {SECTIONS.map((section) => {
          const isCollapsed  = !!collapsedSections[section.id];
          const sectionActive = isSectionActive(section);

          if (!isOpen) {
            return (
              <ul key={section.id} className="sidebar-nav-list sidebar-nav-list--gap">
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

          return (
            <div key={section.id} className="sidebar-section sidebar-nav-list--gap">
              <button
                type="button"
                className={`nav-link sidebar-section-header${sectionActive ? ' section-has-active' : ''}`}
                onClick={() => toggleSection(section.id)}
                aria-expanded={!isCollapsed}
              >
                <span className="nav-icon">{section.icon}</span>
                <span className="nav-text">{section.label}</span>
                <LuChevronRight className={`sidebar-section-chevron${isCollapsed ? '' : ' rotated'}`} />
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

        {/* Standalone bottom */}
        <ul className="sidebar-nav-list sidebar-nav-list--gap">
          {STANDALONE_BOTTOM.map(renderStandaloneLink)}
        </ul>

      </nav>

      {/* ── Section flyout (collapsed mode) ─────────────────────── */}
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

      {/* ── Footer ──────────────────────────────────────────────── */}
      <div className="sidebar-footer">
        <SidebarUsageWidget isOpen={isOpen} user={user} />

        {/* User card */}
        <div className="sidebar-user-wrapper" ref={userMenuRef}>
          <button
            type="button"
            className={`sidebar-user-card${userMenuOpen ? ' open' : ''}`}
            onClick={() => setUserMenuOpen((v) => !v)}
            title={userName}
          >
            <div className="sidebar-avatar">
              {avatarUrl
                ? <img src={avatarUrl} alt={userName} className="sidebar-avatar-img" referrerPolicy="no-referrer" />
                : <span>{userInitials}</span>}
            </div>
            {isOpen ? (
              <>
                <div className="sidebar-user-copy">
                  <strong>{userName}</strong>
                  <small>{userEmail}</small>
                </div>
                <LuChevronDown className={`sidebar-user-chevron${userMenuOpen ? ' flipped' : ''}`} />
              </>
            ) : null}
          </button>

          {/* User dropdown */}
          {userMenuOpen ? (
            <div className={`sidebar-dropdown sidebar-dropdown--user${isOpen ? ' sidebar-dropdown--inline sidebar-dropdown--up' : ' sidebar-dropdown--flyout'}`}>
              {/* Theme toggle */}
              <button
                type="button"
                className="sidebar-dropdown-item"
                onClick={() => { toggleTheme(); setUserMenuOpen(false); }}
              >
                <span className="sidebar-dropdown-icon">
                  {mode === 'dark' ? <LuSun /> : <LuMoon />}
                </span>
                <span>{mode === 'dark' ? 'Modo claro' : 'Modo escuro'}</span>
              </button>
              <div className="sidebar-dropdown-divider" />
              <button type="button" className="sidebar-dropdown-item" onClick={() => { setUserMenuOpen(false); navigate('/configuracoes'); }}>
                <span className="sidebar-dropdown-icon"><LuSettings /></span>
                <span>Configurações</span>
              </button>
              <button type="button" className="sidebar-dropdown-item" onClick={() => { setUserMenuOpen(false); navigate('/financeiro'); }}>
                <span className="sidebar-dropdown-icon"><LuWalletCards /></span>
                <span>Financeiro</span>
              </button>
              <button type="button" className="sidebar-dropdown-item" onClick={() => { setUserMenuOpen(false); navigate('/monitoramento'); }}>
                <span className="sidebar-dropdown-icon"><LuHistory /></span>
                <span>Monitoramento</span>
              </button>
              <div className="sidebar-dropdown-divider" />
              <button type="button" className="sidebar-dropdown-item sidebar-dropdown-item--danger" onClick={() => { setUserMenuOpen(false); logout(); }}>
                <span className="sidebar-dropdown-icon"><LuLogOut /></span>
                <span>Sair</span>
              </button>
            </div>
          ) : null}
        </div>

      </div>
    </aside>
  );
}

export default Sidebar;
