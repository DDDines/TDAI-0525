import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import MainLayout from '../MainLayout.jsx';

jest.mock('../Sidebar', () => ({
  __esModule: true,
  default: ({ isOpen, toggleSidebar }) => (
    <div data-testid="sidebar-state">
      <span>{isOpen ? 'open' : 'closed'}</span>
      <button onClick={toggleSidebar}>toggle-sidebar</button>
    </div>
  ),
}));

jest.mock('../Topbar', () => ({
  __esModule: true,
  default: ({ viewTitle, toggleSidebar }) => (
    <div>
      <span data-testid="topbar-title">{viewTitle}</span>
      <button onClick={toggleSidebar}>toggle-topbar</button>
    </div>
  ),
}));

function renderLayout(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route path="historico" element={<div>Historico screen</div>} />
          <Route path="tipos-de-produto" element={<div>Tipos screen</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe('MainLayout', () => {
  test('maps route names to friendly view titles', () => {
    renderLayout('/historico');

    expect(screen.getByTestId('topbar-title')).toHaveTextContent('Histórico de Uso');
    expect(screen.getByText('Historico screen')).toBeInTheDocument();
  });

  test('toggles the sidebar from the topbar and sidebar controls', () => {
    renderLayout('/tipos-de-produto');

    expect(screen.getByTestId('topbar-title')).toHaveTextContent('Tipos de Produto');
    expect(screen.getByTestId('sidebar-state')).toHaveTextContent('open');

    fireEvent.click(screen.getByText('toggle-topbar'));
    expect(screen.getByTestId('sidebar-state')).toHaveTextContent('closed');

    fireEvent.click(screen.getByText('toggle-sidebar'));
    expect(screen.getByTestId('sidebar-state')).toHaveTextContent('open');
  });
});
