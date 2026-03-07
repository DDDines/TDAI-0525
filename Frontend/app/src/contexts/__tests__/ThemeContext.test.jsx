import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, useTheme } from '../ThemeContext.jsx';

function Probe() {
  const { mode, toggleTheme } = useTheme();
  return (
    <div>
      <span data-testid="mode">{mode}</span>
      <button type="button" onClick={toggleTheme}>
        toggle-theme
      </button>
    </div>
  );
}

function InvalidProbe() {
  useTheme();
  return <div>invalid</div>;
}

describe('ThemeContext', () => {
  beforeEach(() => {
    localStorage.clear();
    document.body.className = '';
  });

  test('loads the stored theme and toggles it', () => {
    localStorage.setItem('theme', 'dark');

    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>
    );

    expect(screen.getByTestId('mode')).toHaveTextContent('dark');
    expect(document.body).toHaveClass('dark');

    fireEvent.click(screen.getByText('toggle-theme'));

    expect(screen.getByTestId('mode')).toHaveTextContent('light');
    expect(document.body).not.toHaveClass('dark');
    expect(localStorage.getItem('theme')).toBe('light');
  });

  test('falls back to light mode when storage contains an unknown theme', () => {
    localStorage.setItem('theme', 'sepia');

    render(
      <ThemeProvider>
        <Probe />
      </ThemeProvider>
    );

    expect(screen.getByTestId('mode')).toHaveTextContent('light');
    expect(document.body).not.toHaveClass('dark');
    expect(localStorage.getItem('theme')).toBe('light');

    fireEvent.click(screen.getByText('toggle-theme'));
    expect(screen.getByTestId('mode')).toHaveTextContent('dark');
    expect(document.body).toHaveClass('dark');
  });

  test('throws when the hook is used outside the provider', () => {
    expect(() => render(<InvalidProbe />)).toThrow(
      'useTheme deve ser usado dentro de um ThemeProvider'
    );
  });
});
