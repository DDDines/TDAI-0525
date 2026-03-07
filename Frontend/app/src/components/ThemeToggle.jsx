/**
 * Module theme toggle.
 *
 * Defines responsibilities and integration points for components.
 */

// Frontend/app/src/components/ThemeToggle.jsx
import React from 'react';
import { useTheme } from '../contexts/ThemeContext';
import logo from '../assets/Logo.png';

function ThemeToggle(

  { className }) {
    const { mode, toggleTheme } = useTheme();
    const nextMode = mode === 'dark' ? 'claro' : 'escuro';

    return (
      <button
        onClick={toggleTheme}
        className={className}
        aria-label={`Alternar tema (ir para ${nextMode})`}
        title={`Alternar tema (ir para ${nextMode})`}>

      <img src={logo} alt="" className="theme-toggle-logo" />
      <span className="visually-hidden">{`Tema atual: ${mode === 'dark' ? 'escuro' : 'claro'}`}</span>
    </button>);

  }
export default ThemeToggle;
