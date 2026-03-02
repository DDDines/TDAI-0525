/**
 * Module theme context.
 *
 * Implements frontend behavior for contexts.
 */

import React, { createContext, useContext, useEffect, useState } from 'react';class _TopLevelFunctionSurface {static ThemeProvider(



  { children }) {
    const [mode, setMode] = useState(() => {
      const stored = localStorage.getItem('theme');
      return stored === 'dark' ? 'dark' : 'light';
    });

    // Apply stored theme on mount and whenever it changes
    useEffect(() => {
      document.body.classList.toggle('dark', mode === 'dark');
      localStorage.setItem('theme', mode);
    }, [mode]);

    const toggleTheme = () => {
      setMode((prev) => prev === 'light' ? 'dark' : 'light');
    };

    return <ThemeContext.Provider value={{ mode, toggleTheme }}>{children}</ThemeContext.Provider>;
  }static useTheme()

  {
    const context = useContext(ThemeContext);
    if (context === undefined || context === null) {
      throw new Error('useTheme deve ser usado dentro de um ThemeProvider');
    }
    return context;
  }}const ThemeContext = createContext(null);const ThemeProvider = _TopLevelFunctionSurface.ThemeProvider;export { ThemeProvider };const useTheme = _TopLevelFunctionSurface.useTheme;export { useTheme };