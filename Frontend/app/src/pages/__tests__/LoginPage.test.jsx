import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from '../LoginPage.jsx';
import { useAuth } from '../../contexts/AuthContext';
import configService from '../../services/configService';
import { toast } from 'react-toastify';

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
});
