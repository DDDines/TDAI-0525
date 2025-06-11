// Frontend/app/src/components/ThemeToggle.jsx
import React from 'react';
import { LuSun, LuMoon } from 'react-icons/lu';
import { useTheme } from '../contexts/ThemeContext';

function ThemeToggle({ className }) {
  const { mode, toggleTheme } = useTheme();
  return (
    <button onClick={toggleTheme} className={className} aria-label="Alternar tema">
      {mode === 'dark' ? <LuSun /> : <LuMoon />}
    </button>
  );
}

export default ThemeToggle;
