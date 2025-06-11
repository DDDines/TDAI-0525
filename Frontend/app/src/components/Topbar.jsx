// Frontend/app/src/components/Topbar.jsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { LuMenu } from 'react-icons/lu';
import UserMenu from './UserMenu.jsx';
import ThemeToggle from './ThemeToggle.jsx';

function Topbar({ viewTitle, toggleSidebar }) {
  const navigate = useNavigate();
  const { logout } = useAuth();

  return (
    <header className="topbar">
      <button onClick={toggleSidebar} className="sidebar-toggle-btn" aria-label="Alternar menu">
        <LuMenu />
      </button>
      <h1>{viewTitle || "Dashboard"}</h1>
      <ThemeToggle className="theme-toggle-btn" />
      <UserMenu onLogout={logout} onNavigate={path => navigate(path)} />
    </header>
  );
}

export default Topbar;
