import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import UserMenu from '../UserMenu.jsx';
import { useAuth } from '../../contexts/AuthContext';

const mockNavigate = jest.fn();

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

describe('UserMenu', () => {
  const onLogout = jest.fn();
  const onNavigate = jest.fn();
  const logout = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      user: {
        nome_completo: 'Julio Cesar',
        email: 'julio@example.com',
        nome_empresa: 'CatalogAI',
        is_superuser: true,
        plano: { nome: 'Pro' },
      },
      logout,
      isLoading: false,
    });
  });

  test('renders user identity and navigates through dropdown actions', async () => {
    const user = userEvent.setup();

    render(<UserMenu onLogout={onLogout} onNavigate={onNavigate} />);

    expect(screen.getByRole('button', { name: /Julio Cesar/i })).toBeInTheDocument();
    expect(screen.getByText('JC')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Julio Cesar/i }));

    expect(screen.getByText('julio@example.com')).toBeInTheDocument();
    expect(screen.getByText('CatalogAI')).toBeInTheDocument();
    expect(screen.getByText('Administrador')).toBeInTheDocument();
    expect(screen.getByText('Plano: Pro')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Configuracoes/i }));
    expect(onNavigate).toHaveBeenCalledWith('/configuracoes');

    await user.click(screen.getByRole('button', { name: /Julio Cesar/i }));
    await user.click(screen.getByRole('button', { name: /Meu Plano/i }));
    expect(onNavigate).toHaveBeenCalledWith('/plano');

    await user.click(screen.getByRole('button', { name: /Julio Cesar/i }));
    await user.click(screen.getByRole('button', { name: /Historico/i }));
    expect(onNavigate).toHaveBeenCalledWith('/historico');

    await user.click(screen.getByRole('button', { name: /Julio Cesar/i }));
    await user.click(screen.getByRole('button', { name: /Sair/i }));
    expect(onLogout).toHaveBeenCalledTimes(1);
  });

  test('closes the dropdown when clicking outside', async () => {
    const user = userEvent.setup();

    render(<UserMenu onLogout={onLogout} onNavigate={onNavigate} />);

    await user.click(screen.getByRole('button', { name: /Julio Cesar/i }));
    expect(screen.getByRole('menu')).toBeInTheDocument();

    await user.click(document.body);

    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });

  test('keeps the menu disabled when showDropdown is false', async () => {
    const user = userEvent.setup();

    render(<UserMenu showDropdown={false} onLogout={onLogout} onNavigate={onNavigate} />);

    await user.click(screen.getByRole('button', { name: /Julio Cesar/i }));

    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });

  test('falls back to router navigation and auth logout when callbacks are not provided', async () => {
    const user = userEvent.setup();

    render(<UserMenu />);

    await user.click(screen.getByRole('button', { name: /Julio Cesar/i }));
    await user.click(screen.getByRole('button', { name: /Configuracoes/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/configuracoes');

    await user.click(screen.getByRole('button', { name: /Julio Cesar/i }));
    await user.click(screen.getByRole('button', { name: /Sair/i }));
    expect(logout).toHaveBeenCalledTimes(1);
  });
});
