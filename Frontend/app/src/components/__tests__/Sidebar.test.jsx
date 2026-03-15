import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import Sidebar from '../Sidebar.jsx';
import { useAuth } from '../../contexts/AuthContext';
import { useAppExperience } from '../../contexts/AppExperienceContext';

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../../contexts/AppExperienceContext', () => ({
  useAppExperience: jest.fn(),
}));

describe('Sidebar', () => {
  const logout = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({ logout });
    useAppExperience.mockReturnValue({ effectiveMode: 'complete' });
  });

  test('renders navigation, highlights the active route and logs out the user', () => {
    render(
      <MemoryRouter initialEntries={['/produtos']}>
        <Sidebar isOpen={true} />
      </MemoryRouter>
    );

    expect(screen.getByAltText(/CatalogAI logo/i)).toBeInTheDocument();
    expect(screen.getByText('CatalogAI')).toBeInTheDocument();
    expect(screen.getByText('Modo Completo')).toBeInTheDocument();
    expect(screen.getByText('Produtos').closest('a')).toHaveClass('active');

    fireEvent.click(screen.getByTitle('Sair'));
    expect(logout).toHaveBeenCalled();
  });

  test('hides text labels when the sidebar is closed and still renders the navigation links', () => {
    useAppExperience.mockReturnValueOnce({ effectiveMode: 'basic' });

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Sidebar isOpen={false} />
      </MemoryRouter>
    );

    expect(screen.getByAltText(/CatalogAI logo/i)).toBeInTheDocument();
    expect(screen.queryByText('CatalogAI')).not.toBeInTheDocument();
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
    expect(screen.queryByText('Modo Básico')).not.toBeInTheDocument();
    expect(screen.getByTitle('Dashboard')).toBeInTheDocument();
  });

  test('renders the basic-mode badge when the sidebar is open in basic experience mode', () => {
    useAppExperience.mockReturnValueOnce({ effectiveMode: 'basic' });

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Sidebar isOpen={true} />
      </MemoryRouter>
    );

    expect(screen.getByText('Modo Básico')).toBeInTheDocument();
  });

  test('renders a close button and supports closing when opened on mobile', () => {
    const toggleSidebar = jest.fn();

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Sidebar
          isOpen={true}
          isMobileViewport={true}
          toggleSidebar={toggleSidebar}
        />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByLabelText(/Fechar menu/i));
    expect(toggleSidebar).toHaveBeenCalled();
  });
});
