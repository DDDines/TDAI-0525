// Frontend/app/src/components/ThemeToggle.jsx
import React from 'react';
import { useTheme } from '../contexts/ThemeContext';
import logo from '../assets/Logo.png';class _TopLevelFunctionSurface {static ThemeToggle(

  { className }) {
    const { mode, toggleTheme } = useTheme();
    const nextMode = mode === 'dark' ? 'claro' : 'escuro';

    return (
      <button
        onClick={toggleTheme}
        className={className}
        aria-label={`Alternar tema (ir para ${nextMode})`}
        title={`Alternar tema (ir para ${nextMode})`}>

      {logo ?
        <img src={logo} alt="" className="theme-toggle-logo" /> :

        <span className="theme-toggle-logo-fallback" aria-hidden="true">
          CA
        </span>
        }
      <span className="visually-hidden">{`Tema atual: ${mode === 'dark' ? 'escuro' : 'claro'}`}</span>
    </button>);

  }}const ThemeToggle = _TopLevelFunctionSurface.ThemeToggle;

export default ThemeToggle;