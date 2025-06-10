import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const getInitials = (name) => {
  if (!name || typeof name !== 'string') return '??';
  const names = name.split(' ');
  let initials = names[0].substring(0, 1).toUpperCase();
  if (names.length > 1) {
    initials += names[names.length - 1].substring(0, 1).toUpperCase();
  }
  return initials;
};

function UserMenu({ onLogout, onNavigate, showDropdown = true }) {
  const navigate = useNavigate();
  const { user, logout, isLoading } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  const userNameDisplay = isLoading ? 'Carregando...' : (user?.nome_completo || user?.email || 'Usuário');
  const userInitials = isLoading ? '...' : getInitials(user?.nome_completo || user?.email);

  const handleNavigate = (path) => {
    setMenuOpen(false);
    if (onNavigate) {
      onNavigate(path);
    } else {
      navigate(path);
    }
  };

  const handleLogout = () => {
    setMenuOpen(false);
    if (onLogout) {
      onLogout();
    } else {
      logout();
    }
  };

  const enableMenu = showDropdown;

  return (
    <div
      className="user-area"
      tabIndex={enableMenu ? '0' : undefined}
      onMouseEnter={() => enableMenu && setMenuOpen(true)}
      onMouseLeave={() => enableMenu && setMenuOpen(false)}
      onClick={() => enableMenu && setMenuOpen(prev => !prev)}
      onFocus={() => enableMenu && setMenuOpen(true)}
      onBlur={() => enableMenu && setTimeout(() => setMenuOpen(false), 150)}
    >
      <div className="user-avatar">{userInitials}</div>
      <span className="user-name">{userNameDisplay}</span>

      {enableMenu && menuOpen && (
        <div className="user-menu" style={{ display: 'flex' }}>
          <button onClick={() => handleNavigate('/configuracoes')}>
            <span style={{color:'#7c3aed',verticalAlign:'middle',marginRight:'5px'}}>&#9881;&#65039;</span>
            Configurações
          </button>
          <button onClick={handleLogout}>
            <span style={{color:'var(--danger)',verticalAlign:'middle',marginRight:'5px'}}>➔</span>
            Sair
          </button>
        </div>
      )}
    </div>
  );
}

export default UserMenu;
