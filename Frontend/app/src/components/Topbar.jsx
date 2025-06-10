// Frontend/app/src/components/Topbar.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { LuMenu } from 'react-icons/lu';
// Se você criar um AuthContext, importe-o:
// import { AuthContext } from '../contexts/AuthContext';


const getInitials = (name) => {
  if (!name || typeof name !== 'string') return '??';
  const names = name.split(' ');
  let initials = names[0].substring(0, 1).toUpperCase();
  if (names.length > 1) {
    initials += names[names.length - 1].substring(0, 1).toUpperCase();
  }
  return initials;
};

function Topbar({ viewTitle, toggleSidebar }) {
  const navigate = useNavigate();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { user, logout, isLoading: loadingUser } = useAuth();


  const userNameDisplay = loadingUser ? "Carregando..." : (user?.nome_completo || user?.email || "Usuário");
  const userInitials = loadingUser ? "..." : getInitials(user?.nome_completo || user?.email);

  return (
    <header className="topbar">
      <button onClick={toggleSidebar} className="sidebar-toggle-btn" aria-label="Alternar menu">
        <LuMenu />
      </button>
      <h1>{viewTitle || "Dashboard"}</h1>
      <div 
        className="user-area"
        tabIndex="0" 
        onMouseEnter={() => setUserMenuOpen(true)}
        onMouseLeave={() => setUserMenuOpen(false)}
        onClick={() => setUserMenuOpen(prev => !prev)}
        onFocus={() => setUserMenuOpen(true)} // Para acessibilidade com teclado
        onBlur={() => setTimeout(() => setUserMenuOpen(false), 150)} // Pequeno delay para permitir clique no menu
      >
        <div className="user-avatar">
          {userInitials}
        </div>
        <span className="user-name">{userNameDisplay}</span>
        
        {userMenuOpen && (
          <div className="user-menu" style={{ display: 'flex' }}> {/* Mantido flex para layout interno dos botões */}
            <button onClick={() => { setUserMenuOpen(false); navigate('/configuracoes'); }}> 
              <span style={{color:"#7c3aed",verticalAlign:"middle", marginRight:"5px"}}>&#9881;&#65039;</span> 
              Configurações
            </button>
            <button onClick={() => { setUserMenuOpen(false); logout(); }}>
              <span style={{color:"var(--danger)",verticalAlign:"middle", marginRight:"5px"}}>➔</span>
              Sair
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

export default Topbar;
