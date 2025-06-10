import React, { useState, useEffect, useRef } from 'react';
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
  const menuRef = useRef(null);

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

  useEffect(() => {
    if (!menuOpen) return;
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [menuOpen]);

  const toggleMenu = () => {
    if (enableMenu) setMenuOpen(prev => !prev);
  };

  return (
    <div className="user-area" ref={menuRef} tabIndex={enableMenu ? '0' : undefined}>
      <div className="user-avatar" onClick={toggleMenu}>{userInitials}</div>
      <span className="user-name" onClick={toggleMenu}>{userNameDisplay}</span>

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
