// Frontend/app/src/components/MainLayout.jsx
import React, { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar'; // Certifique-se que o caminho está correto
import Topbar from './Topbar';   // Certifique-se que o caminho está correto

function MainLayout() {
  const [viewTitle, setViewTitle] = useState('Dashboard');
  const location = useLocation();

  useEffect(() => {
    const pathSegments = location.pathname.split('/').filter(Boolean);
    let title = 'Dashboard'; // Título padrão

    if (pathSegments.length > 0) {
      const mainPath = pathSegments[0];
      // Capitaliza a primeira letra e remove hífens se houver (ex: 'meu-plano' -> 'Meu plano')
      title = mainPath.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    // Mapeamento para nomes de título mais amigáveis e traduções
    const titleMap = {
      'Dashboard': 'Dashboard',
      'Produtos': 'Produtos',
      'Fornecedores': 'Fornecedores',
      'Enriquecimento': 'Enriquecimento de Produtos',
      'Historico': 'Histórico de Uso',
      'Plano': 'Meu Plano',
      'Configuracoes': 'Configurações',
      // Adicione outros mapeamentos se os nomes das rotas forem diferentes dos títulos desejados
    };

    setViewTitle(titleMap[title] || title);
  }, [location]);

  // O div mais externo agora usa 100% da altura do #root e é um container flex
  // para a Sidebar e a área .main.
  // As classes .main e .content no JSX abaixo irão buscar os seus estilos do index.css.
  return (
    <div style={{ display: 'flex', height: '100%', width: '100%', fontFamily: 'var(--font)' }}>
      <Sidebar /> {/* A Sidebar terá largura fixa e altura 100% via CSS */}
      
      {/* A classe "main" agora será um item flex que ocupa o espaço restante */}
      <div className="main"> 
        <Topbar viewTitle={viewTitle} />
        {/* A classe "content" é o container interno que terá overflow-y: auto */}
        <main className="content"> 
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default MainLayout;
