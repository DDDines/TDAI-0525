/**
 * Module topbar.
 *
 * Thin action bar — only ThemeToggle + UserMenu.
 * Each page renders its own PageHeader with contextual title and actions.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { LuMenu } from 'react-icons/lu';
import { useAuth } from '../contexts/AuthContext';
import UserMenu from './UserMenu.jsx';
import ThemeToggle from './ThemeToggle.jsx';

function Topbar({ toggleSidebar, isMobileLayout }) {
  const navigate = useNavigate();
  const { logout } = useAuth();

  return (
    <header className="topbar">
      <div className="topbar-inner">
        {isMobileLayout ? (
          <button
            type="button"
            className="sidebar-toggle-btn"
            aria-label="Abrir menu"
            onClick={toggleSidebar}
          >
            <LuMenu />
          </button>
        ) : null}
        <div className="topbar-actions">
          <ThemeToggle className="theme-toggle-btn" />
          <UserMenu onLogout={logout} onNavigate={(path) => navigate(path)} />
        </div>
      </div>
    </header>
  );
}

export default Topbar;
