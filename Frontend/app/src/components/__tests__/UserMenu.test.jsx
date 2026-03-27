import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import UserMenu from '../UserMenu.jsx';
import { useAuth } from '../../contexts/AuthContext';
import { useWorkspace } from '../../contexts/WorkspaceContext';

const mockNavigate = jest.fn();

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../../contexts/WorkspaceContext', () => ({
  useWorkspace: jest.fn(),
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
        nome_empresa: 'CommerceFolio',
        is_superuser: true,
        plano: { nome: 'Pro' },
      },
      logout,
      isLoading: false,
    });
    useWorkspace.mockReturnValue({
      workspace: { nome: 'CommerceFolio' },
      workspaceName: 'CommerceFolio',
    });
  });

  test('renders user identity and navigates through dropdown actions', async () => {
    const user = userEvent.setup();

    render(<UserMenu onLogout={onLogout} onNavigate={onNavigate} />);

    expect(screen.getByRole('button', { name: /Julio Cesar/i })).toBeInTheDocument();
    expect(screen.getByText('JC')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Julio Cesar/i }));

    expect(screen.getByText('julio@example.com')).toBeInTheDocument();
    expect(screen.getByText('CommerceFolio')).toBeInTheDocument();
    expect(screen.getByText('Administrador')).toBeInTheDocument();
    expect(screen.getByText('Plano: Pro')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Configuracoes/i }));
    expect(onNavigate).toHaveBeenCalledWith('/configuracoes');

    await user.click(screen.getByRole('button', { name: /Julio Cesar/i }));
    await user.click(screen.getByRole('button', { name: /Financeiro/i }));
    expect(onNavigate).toHaveBeenCalledWith('/financeiro');

    await user.click(screen.getByRole('button', { name: /Julio Cesar/i }));
    await user.click(screen.getByRole('button', { name: /Monitoramento/i }));
    expect(onNavigate).toHaveBeenCalledWith('/monitoramento');

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

  test('renders loading and minimal user states safely', async () => {
    const user = userEvent.setup();

    useAuth.mockReturnValueOnce({
      user: {
        nome_completo: 'Julio',
        email: '',
        nome_empresa: '',
        is_superuser: false,
        plano: null,
        avatar_url: 'https://img.example/avatar.png',
      },
      logout,
      isLoading: true,
    });

    const { unmount } = render(<UserMenu />);
    expect(screen.getByRole('button', { name: /Carregando/i })).toBeInTheDocument();
    expect(screen.getByText('...')).toBeInTheDocument();

    unmount();
    useAuth.mockReturnValue({
      user: {
        nome_completo: 'Julio Silva',
        email: '',
        nome_empresa: '',
        is_superuser: false,
        plano: null,
        avatar_url: 'https://img.example/avatar.png',
      },
      logout,
      isLoading: false,
    });
    useWorkspace.mockReturnValue({
      workspace: null,
      workspaceName: '',
    });

    render(<UserMenu />);

    await user.click(screen.getByRole('button', { name: /Julio Silva/i }));
    expect(screen.getByAltText(/Avatar de Julio Silva/i)).toBeInTheDocument();
    expect(screen.getByText('Usuario')).toBeInTheDocument();
    expect(screen.queryByText(/Plano:/i)).not.toBeInTheDocument();
    expect(screen.queryByText('CommerceFolio')).not.toBeInTheDocument();
  });

  test('uses a single initial when the user has only one name token', async () => {
    const user = userEvent.setup();

    useAuth.mockReturnValue({
      user: {
        nome_completo: 'Julio',
        email: '',
        nome_empresa: '',
        is_superuser: false,
        plano: null,
        avatar_url: '',
      },
      logout,
      isLoading: false,
    });

    render(<UserMenu />);

    expect(screen.getByText('J')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Julio/i }));
    expect(screen.getByText('Usuario')).toBeInTheDocument();
  });

  test('falls back to email and safe initials when the profile data is sparse or malformed', async () => {
    const user = userEvent.setup();

    useAuth.mockReturnValue({
      user: {
        nome_completo: '',
        email: 'fallback@example.com',
        nome_empresa: '',
        is_superuser: false,
        plano: null,
        avatar_url: '',
      },
      logout,
      isLoading: false,
    });

    const { unmount } = render(<UserMenu />);

    expect(screen.getByRole('button', { name: /fallback@example.com/i })).toBeInTheDocument();
    expect(screen.getByText('F')).toBeInTheDocument();

    unmount();
    useAuth.mockReturnValue({
      user: {
        nome_completo: 123,
        email: '',
        nome_empresa: '',
        is_superuser: false,
        plano: null,
        avatar_url: '',
      },
      logout,
      isLoading: false,
    });

    render(<UserMenu />);

    expect(screen.getByRole('button', { name: /123/i })).toBeInTheDocument();
    expect(screen.getByText('--')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /123/i }));
    expect(screen.getByText('Sem e-mail')).toBeInTheDocument();
  });

  test('falls back to a generic label when there is no user object', async () => {
    const user = userEvent.setup();

    useAuth.mockReturnValue({
      user: null,
      logout,
      isLoading: false,
    });

    render(<UserMenu />);

    expect(screen.getByRole('button', { name: /Usuario/i })).toBeInTheDocument();
    expect(screen.getByText('--')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Usuario/i }));
    expect(screen.getByText('Sem e-mail')).toBeInTheDocument();
  });
});
