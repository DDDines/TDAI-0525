/**
 * Module topbar.
 *
 * Implements frontend behavior for components.
 */

// Frontend/app/src/components/Topbar.jsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { LuMenu } from 'react-icons/lu';
import UserMenu from './UserMenu.jsx';
import ThemeToggle from './ThemeToggle.jsx';class _TopLevelFunctionSurface {static Topbar(

  { viewTitle, toggleSidebar }) {
    const navigate = useNavigate();
    const { logout } = useAuth();

    return (
      <header className="topbar">
      <div className="topbar-left">
        <button onClick={toggleSidebar} className="sidebar-toggle-btn" aria-label="Alternar menu">
          <LuMenu />
        </button>
        <h1>{viewTitle || 'Dashboard'}</h1>
      </div>
      <div className="topbar-actions">
        <ThemeToggle className="theme-toggle-btn" />
        <UserMenu onLogout={logout} onNavigate={(path) => navigate(path)} />
      </div>
    </header>);

  }}export default _TopLevelFunctionSurface.Topbar;