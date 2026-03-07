import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from '../LoginPage.jsx';
import { useAuth } from '../../contexts/AuthContext';
import configService from '../../services/configService';
import { toast } from 'react-toastify';
import logger from '../../utils/logger';

const mockNavigate = jest.fn();
const mockLocation = { state: null };
let consoleErrorSpy;

jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => mockLocation,
  };
});

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../../services/configService', () => ({
  __esModule: true,
  default: {
    getSocialLoginConfig: jest.fn(),
  },
}));

jest.mock('react-toastify', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: { log: jest.fn() },
}));

describe('LoginPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockLocation.state = null;
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    configService.getSocialLoginConfig.mockResolvedValue({
      google_enabled: false,
      facebook_enabled: false,
    });
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  test('shows loading popup while auth context is loading', async () => {
    useAuth.mockReturnValue({
      login: jest.fn(),
      isAuthenticated: false,
      isLoading: true,
      user: null,
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/carregando/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(configService.getSocialLoginConfig).toHaveBeenCalled();
    });
  });

  test('redirects authenticated users to previous route', async () => {
    useAuth.mockReturnValue({
      login: jest.fn(),
      isAuthenticated: true,
      isLoading: false,
      user: { nome_completo: 'Admin' },
    });
    mockLocation.state = { from: { pathname: '/fornecedores' } };

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/fornecedores', { replace: true });
    });
  });

  test('redirects authenticated users to dashboard when there is no previous route', async () => {
    useAuth.mockReturnValue({
      login: jest.fn(),
      isAuthenticated: true,
      isLoading: false,
      user: { nome_completo: 'Admin' },
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true });
    });
    expect(logger.log).toHaveBeenCalled();
  });

  test('submits login successfully and shows success toast', async () => {
    const loginMock = jest.fn().mockResolvedValue(true);
    useAuth.mockReturnValue({
      login: loginMock,
      isAuthenticated: false,
      isLoading: false,
      user: { nome_completo: 'Julio' },
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/email/i), 'julio@teste.com');
    await userEvent.type(screen.getByLabelText(/senha/i), '123456');
    await userEvent.click(screen.getByRole('button', { name: /entrar/i }));

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith('julio@teste.com', '123456');
    });
    expect(toast.success).toHaveBeenCalledWith(expect.stringContaining('Bem-vindo de volta'));
  });

  test('shows error message when login fails', async () => {
    const loginMock = jest.fn().mockRejectedValue(new Error('Credenciais inválidas'));
    useAuth.mockReturnValue({
      login: loginMock,
      isAuthenticated: false,
      isLoading: false,
      user: null,
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/email/i), 'julio@teste.com');
    await userEvent.type(screen.getByLabelText(/senha/i), 'senhaerrada');
    await userEvent.click(screen.getByRole('button', { name: /entrar/i }));

    expect(await screen.findByText('Credenciais inválidas')).toBeInTheDocument();
    expect(toast.error).toHaveBeenCalledWith(expect.stringContaining('Falha no login'));
  });

  test('prefers backend detail payloads when login fails', async () => {
    const loginMock = jest.fn().mockRejectedValue({
      response: { data: { detail: 'usuario bloqueado' } },
    });
    useAuth.mockReturnValue({
      login: loginMock,
      isAuthenticated: false,
      isLoading: false,
      user: null,
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/email/i), 'julio@teste.com');
    await userEvent.type(screen.getByLabelText(/senha/i), 'senhaerrada');
    await userEvent.click(screen.getByRole('button', { name: /entrar/i }));

    expect(await screen.findByText('usuario bloqueado')).toBeInTheDocument();
    expect(toast.error).toHaveBeenCalledWith(expect.stringContaining('usuario bloqueado'));
  });

  test('loads social login links and marks disabled providers as unavailable', async () => {
    useAuth.mockReturnValue({
      login: jest.fn(),
      isAuthenticated: false,
      isLoading: false,
      user: null,
    });
    configService.getSocialLoginConfig.mockResolvedValueOnce({
      google_enabled: true,
      facebook_enabled: false,
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    const googleLink = await screen.findByRole('link', { name: /Entrar com Google/i });
    const facebookLink = screen.getByText(/Entrar com Facebook/i).closest('a');
    expect(googleLink).toHaveAttribute('href', '/api/v1/auth/google/login');
    expect(facebookLink).not.toHaveAttribute('href');
    expect(facebookLink).toHaveClass('disabled');
  });

  test('prevents clicks for disabled providers and keeps enabled providers navigable', async () => {
    useAuth.mockReturnValue({
      login: jest.fn(),
      isAuthenticated: false,
      isLoading: false,
      user: null,
    });
    configService.getSocialLoginConfig.mockResolvedValue({
      google_enabled: false,
      facebook_enabled: true,
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    const googleLink = (await screen.findByText(/Entrar com Google/i)).closest('a');
    const facebookLink = screen.getByText(/Entrar com Facebook/i).closest('a');

    await waitFor(() => {
      expect(facebookLink).toHaveAttribute('href', '/api/v1/auth/facebook/login');
    });

    const googleClick = fireEvent.click(googleLink);

    expect(googleClick).toBe(false);
    expect(facebookLink).not.toHaveClass('disabled');
  });

  test('logs social config loading failures without blocking the form', async () => {
    useAuth.mockReturnValue({
      login: jest.fn(),
      isAuthenticated: false,
      isLoading: false,
      user: null,
    });
    configService.getSocialLoginConfig.mockRejectedValueOnce(new Error('falha config social'));

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    expect(await screen.findByRole('button', { name: /entrar/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'LoginPage: Erro ao obter configuracao de social login',
        expect.any(Error)
      );
    });
  });
});
