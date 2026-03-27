import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import Sidebar from '../Sidebar.jsx';
import { useAuth } from '../../contexts/AuthContext';
import { useWorkspace } from '../../contexts/WorkspaceContext';

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../../contexts/WorkspaceContext', () => ({
  useWorkspace: jest.fn(),
}));

describe('Sidebar', () => {
  const logout = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      logout,
      user: {
        is_superuser: false,
      },
    });
    useWorkspace.mockReturnValue({
      workspace: { nome: 'Dines' },
      hasWorkspace: true,
    });
  });

  test('renders branding, company context, grouped navigation and logout action', () => {
    render(
      <MemoryRouter initialEntries={['/produtos']}>
        <Sidebar isOpen={true} />
      </MemoryRouter>
    );

    expect(screen.getByAltText(/CommerceFolio logo/i)).toBeInTheDocument();
    expect(screen.getByLabelText('CommerceFolio')).toBeInTheDocument();
    expect(screen.getByText('Dines')).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Catálogo')).toBeInTheDocument();
    expect(screen.getByText('Operações')).toBeInTheDocument();
    expect(screen.getByText('Empresa')).toBeInTheDocument();
    expect(screen.getByText('Configurações')).toBeInTheDocument();
    expect(screen.getByText('Catálogo').closest('a')).toHaveClass('active');

    fireEvent.click(screen.getByTitle('Sair'));
    expect(logout).toHaveBeenCalled();
  });

  test('hides text labels when the sidebar is closed and still renders navigation links', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Sidebar isOpen={false} />
      </MemoryRouter>
    );

    expect(screen.getByAltText(/CommerceFolio logo/i)).toBeInTheDocument();
    expect(screen.queryByLabelText('CommerceFolio')).not.toBeInTheDocument();
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
    expect(screen.getByTitle('Dashboard')).toBeInTheDocument();
  });

  test('renders a close button and supports closing when opened on mobile', () => {
    const toggleSidebar = jest.fn();

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Sidebar isOpen={true} isMobileViewport={true} toggleSidebar={toggleSidebar} />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByLabelText(/Fechar menu/i));
    expect(toggleSidebar).toHaveBeenCalled();
  });
});
