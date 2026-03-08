/**
 * Module user menu.
 *
 * Defines responsibilities and integration points for components.
 */

import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LuHistory, LuLogOut, LuSettings, LuWalletCards } from 'react-icons/lu';
import { useAuth } from '../contexts/AuthContext';

function getInitials(name) {
  if (!name || typeof name !== 'string') return '--';
  const names = name.split(' ').filter(Boolean);
  let initials = names[0].substring(0, 1).toUpperCase();
  if (names.length > 1) {
    initials += names[names.length - 1].substring(0, 1).toUpperCase();
  }
  return initials;
}

function UserMenu({ onLogout, onNavigate, showDropdown = true }) {
  const navigate = useNavigate();
  const { user, logout, isLoading } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const navigateAction = onNavigate ?? navigate;
  const logoutAction = onLogout ?? logout;

  const userNameDisplay = isLoading ? 'Carregando...' : user?.nome_completo || user?.email || 'Usuario';
  const userInitials = isLoading ? '...' : getInitials(user?.nome_completo || user?.email);
  const userAvatarUrl = isLoading ? '' : user?.avatar_url || '';
  const userEmailDisplay = isLoading ? '' : user?.email || 'Sem e-mail';
  const userCompanyDisplay = isLoading ? '' : user?.nome_empresa || '';
  const userPlanDisplay = isLoading ? '' : user?.plano?.nome || '';
  const userRoleDisplay = isLoading ? '' : user?.is_superuser ? 'Administrador' : 'Usuario';

  const handleNavigate = (path) => {
    setMenuOpen(false);
    navigateAction(path);
  };

  const handleLogout = () => {
    setMenuOpen(false);
    logoutAction();
  };

  const enableMenu = showDropdown;

  useEffect(() => {
    if (!menuOpen) return undefined;

    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setMenuOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [menuOpen]);

  const toggleMenu = () => {
    if (enableMenu) {
      setMenuOpen((prev) => !prev);
    }
  };

  return (
    <div className="user-area" ref={menuRef} tabIndex={enableMenu ? '0' : undefined}>
      <button
        type="button"
        className="user-trigger"
        onClick={toggleMenu}
        aria-haspopup="menu"
        aria-expanded={menuOpen ? 'true' : 'false'}
      >
        <div className="user-avatar">
          {userAvatarUrl ? (
            <img
              src={userAvatarUrl}
              alt={`Avatar de ${userNameDisplay}`}
              className="user-avatar-image"
              referrerPolicy="no-referrer"
            />
          ) : (
            userInitials
          )}
        </div>
        <span className="user-name">{userNameDisplay}</span>
      </button>

      {enableMenu && menuOpen ? (
        <div className="user-menu" role="menu">
          <div className="user-menu-profile">
            <p className="user-menu-profile-name">{userNameDisplay}</p>
            <p className="user-menu-profile-email">{userEmailDisplay}</p>
            {userCompanyDisplay ? (
              <p className="user-menu-profile-company">{userCompanyDisplay}</p>
            ) : null}
            <div className="user-menu-profile-meta">
              <span>{userRoleDisplay}</span>
              {userPlanDisplay ? <span>Plano: {userPlanDisplay}</span> : null}
            </div>
          </div>

          <button onClick={() => handleNavigate('/configuracoes')}>
            <span className="menu-item-icon"><LuSettings /></span>
            Configuracoes
          </button>
          <button onClick={() => handleNavigate('/plano')}>
            <span className="menu-item-icon"><LuWalletCards /></span>
            Meu Plano
          </button>
          <button onClick={() => handleNavigate('/historico')}>
            <span className="menu-item-icon"><LuHistory /></span>
            Historico
          </button>
          <button onClick={handleLogout}>
            <span className="menu-item-icon"><LuLogOut /></span>
            Sair
          </button>
        </div>
      ) : null}
    </div>
  );
}

export default UserMenu;
