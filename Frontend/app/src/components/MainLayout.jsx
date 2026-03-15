/**
 * Module main layout.
 *
 * Defines responsibilities and integration points for components.
 */

import React, { useEffect, useRef, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

const MOBILE_BREAKPOINT = 900;

function isMobileViewport() {
  if (typeof window === 'undefined') {
    return false;
  }
  return window.innerWidth <= MOBILE_BREAKPOINT;
}

function MainLayout() {
    const [viewTitle, setViewTitle] = useState('Dashboard');
    const mobileViewportRef = useRef(isMobileViewport());
    const [isMobileLayout, setIsMobileLayout] = useState(mobileViewportRef.current);
    const [sidebarOpen, setSidebarOpen] = useState(() => !mobileViewportRef.current);
    const location = useLocation();

    useEffect(() => {
      const pathSegments = location.pathname.split('/').filter(Boolean);
      let title = 'Dashboard';

      if (pathSegments.length > 0) {
        const mainPath = pathSegments[0];
        title = mainPath.replace(/-/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
      }

      const titleMap = {
        Dashboard: 'Dashboard',
        Produtos: 'Produtos',
        Fornecedores: 'Fornecedores',
        'Tipos De Produto': 'Tipos de Produto',
        Enriquecimento: 'Enriquecimento',
        Historico: 'Histórico de Uso',
        Plano: 'Meu Plano',
        Configuracoes: 'Configurações'
      };

      setViewTitle(titleMap[title] || title);
    }, [location]);

    useEffect(() => {
      if (typeof window === 'undefined') {
        return undefined;
      }

      const handleResize = () => {
        const nextIsMobile = isMobileViewport();
        setIsMobileLayout(nextIsMobile);
        if (mobileViewportRef.current !== nextIsMobile) {
          mobileViewportRef.current = nextIsMobile;
          setSidebarOpen(!nextIsMobile);
        }
      };

      window.addEventListener('resize', handleResize);
      return () => {
        window.removeEventListener('resize', handleResize);
      };
    }, []);

    useEffect(() => {
      if (isMobileLayout) {
        setSidebarOpen(false);
      }
    }, [isMobileLayout, location.pathname]);

    const toggleSidebar = () => {
      setSidebarOpen((open) => !open);
    };

    return (
      <div className={`main-layout-root ${isMobileLayout ? 'mobile-layout' : 'desktop-layout'} ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
      <Sidebar
        isOpen={sidebarOpen}
        isMobileViewport={isMobileLayout}
        toggleSidebar={toggleSidebar}
      />
      {isMobileLayout && sidebarOpen ? (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Fechar menu"
          onClick={() => setSidebarOpen(false)}
        />
      ) : null}
      <div className="main">
        <Topbar viewTitle={viewTitle} toggleSidebar={toggleSidebar} />
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>);

  }
export default MainLayout;
