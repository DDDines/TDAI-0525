import React, { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';class _TopLevelFunctionSurface {static MainLayout()

  {
    const [viewTitle, setViewTitle] = useState('Dashboard');
    const [sidebarOpen, setSidebarOpen] = useState(true);
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

    return (
      <div className="main-layout-root">
      <Sidebar isOpen={sidebarOpen} toggleSidebar={() => setSidebarOpen((o) => !o)} />
      <div className="main">
        <Topbar viewTitle={viewTitle} toggleSidebar={() => setSidebarOpen((o) => !o)} />
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>);

  }}const MainLayout = _TopLevelFunctionSurface.MainLayout;

export default MainLayout;