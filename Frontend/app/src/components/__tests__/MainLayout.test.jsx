import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import MainLayout from '../MainLayout.jsx';

jest.mock('../Sidebar', () => ({
  __esModule: true,
  default: ({ isOpen, toggleSidebar, isMobileViewport }) => (
    <div data-testid="sidebar-state">
      <span>{isOpen ? 'open' : 'closed'}</span>
      <span data-testid="sidebar-viewport">{isMobileViewport ? 'mobile' : 'desktop'}</span>
      <button onClick={toggleSidebar}>toggle-sidebar</button>
    </div>
  ),
}));

jest.mock('../Topbar', () => ({
  __esModule: true,
  default: ({ viewTitle }) => (
    <div>
      <span data-testid="topbar-title">{viewTitle}</span>
    </div>
  ),
}));

function renderLayout(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<div>Dashboard screen</div>} />
          <Route path="dashboard" element={<div>Dashboard screen</div>} />
          <Route path="monitoramento" element={<div>Monitoramento screen</div>} />
          <Route path="tipos-de-produto" element={<div>Tipos screen</div>} />
          <Route path="rota-customizada" element={<div>Custom screen</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe('MainLayout', () => {
  const originalInnerWidth = window.innerWidth;

  beforeEach(() => {
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: originalInnerWidth,
    });
  });

  afterAll(() => {
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: originalInnerWidth,
    });
  });

  test('maps route names to friendly view titles', () => {
    renderLayout('/monitoramento');

    expect(screen.getByTestId('topbar-title')).toHaveTextContent('Monitoramento');
    expect(screen.getByText('Monitoramento screen')).toBeInTheDocument();
  });

  test('toggles the sidebar from the sidebar control', () => {
    renderLayout('/tipos-de-produto');

    expect(screen.getByTestId('topbar-title')).toHaveTextContent('Tipos de Produto');
    expect(screen.getByTestId('sidebar-state')).toHaveTextContent('open');

    fireEvent.click(screen.getByText('toggle-sidebar'));
    expect(screen.getByTestId('sidebar-state')).toHaveTextContent('closed');
  });

  test('uses dashboard as the default title and formats unknown routes', () => {
    const { unmount } = renderLayout('/');

    expect(screen.getByTestId('topbar-title')).toHaveTextContent('Dashboard');
    expect(screen.getByText('Dashboard screen')).toBeInTheDocument();

    unmount();
    renderLayout('/rota-customizada');

    expect(screen.getByTestId('topbar-title')).toHaveTextContent('Rota Customizada');
    expect(screen.getByText('Custom screen')).toBeInTheDocument();
  });

  test('starts with the sidebar closed on mobile widths and keeps the mobile flag', () => {
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: 390,
    });

    renderLayout('/dashboard');

    expect(screen.getByTestId('sidebar-state')).toHaveTextContent('closed');
    expect(screen.getByTestId('sidebar-viewport')).toHaveTextContent('mobile');
  });
});
