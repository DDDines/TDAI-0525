import React, { useState } from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import { AuthProvider, useAuth } from '../AuthContext.jsx';
import authService from '../../services/authService';
import apiClient from '../../services/apiClient';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

jest.mock('../../services/authService', () => ({
  __esModule: true,
  default: {
    login: jest.fn(),
    getCurrentUser: jest.fn(),
  },
}));

jest.mock('../../services/apiClient', () => ({
  __esModule: true,
  default: {
    defaults: {
      headers: {
        common: {},
      },
    },
  },
}));

jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  },
}));

function AuthProbe() {
  const { user, isAuthenticated, isLoading, login, logout } = useAuth();
  const [error, setError] = useState('');

  return (
    <div>
      <div data-testid="user-email">{user?.email || 'none'}</div>
      <div data-testid="is-authenticated">{String(isAuthenticated)}</div>
      <div data-testid="is-loading">{String(isLoading)}</div>
      <div data-testid="login-error">{error}</div>
      <button
        onClick={() => {
          login('admin@example.com', '123456').catch((err) => {
            setError(err?.message || err?.detail || String(err));
          });
        }}
      >
        login
      </button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

function InvalidAuthProbe() {
  useAuth();
  return <div>invalid</div>;
}

function renderProvider(initialEntries = ['/login']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>
    </MemoryRouter>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    apiClient.defaults.headers.common = {};
  });

  test('clears the session when there is no token on mount', async () => {
    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });

    expect(authService.getCurrentUser).not.toHaveBeenCalled();
    expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('user-email')).toHaveTextContent('none');
  });

  test('restores the authenticated user from a stored token', async () => {
    localStorage.setItem('accessToken', 'stored-token');
    authService.getCurrentUser.mockResolvedValueOnce({ email: 'admin@example.com' });

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
    });

    expect(authService.getCurrentUser).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId('user-email')).toHaveTextContent('admin@example.com');
    expect(apiClient.defaults.headers.common.Authorization).toBe('Bearer stored-token');
  });

  test('clears the stored session when the backend returns no user for the token', async () => {
    localStorage.setItem('accessToken', 'stored-token');
    authService.getCurrentUser.mockResolvedValueOnce(null);

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });

    expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('user-email')).toHaveTextContent('none');
    expect(localStorage.getItem('accessToken')).toBeNull();
    expect(apiClient.defaults.headers.common.Authorization).toBeUndefined();
  });

  test('clears the session when restoring a token returns 401', async () => {
    localStorage.setItem('accessToken', 'expired-token');
    authService.getCurrentUser.mockRejectedValueOnce({
      message: 'expired',
      response: { status: 401, data: { detail: 'token expirado' } },
    });

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });

    expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
    expect(localStorage.getItem('accessToken')).toBeNull();
    expect(apiClient.defaults.headers.common.Authorization).toBeUndefined();
  });

  test('clears the session when restoring a token fails without a backend payload', async () => {
    localStorage.setItem('accessToken', 'broken-token');
    authService.getCurrentUser.mockRejectedValueOnce(new Error('falha local'));

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });

    expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
    expect(localStorage.getItem('accessToken')).toBeNull();
    expect(apiClient.defaults.headers.common.Authorization).toBeUndefined();
  });

  test('login stores the token, loads the user and redirects to the requested page', async () => {
    authService.login.mockResolvedValueOnce({ access_token: 'login-token' });
    authService.getCurrentUser.mockResolvedValueOnce({ email: 'admin@example.com' });

    renderProvider([{ pathname: '/login', state: { from: { pathname: '/produtos' } } }]);

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });

    fireEvent.click(screen.getByText('login'));

    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
    });

    expect(localStorage.getItem('accessToken')).toBe('login-token');
    expect(apiClient.defaults.headers.common.Authorization).toBe('Bearer login-token');
    expect(screen.getByTestId('user-email')).toHaveTextContent('admin@example.com');
    expect(mockNavigate).toHaveBeenCalledWith('/produtos', { replace: true });
  });

  test('login redirects to the dashboard when there is no previous route stored', async () => {
    authService.login.mockResolvedValueOnce({ access_token: 'login-token' });
    authService.getCurrentUser.mockResolvedValueOnce({ email: 'admin@example.com' });

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });

    fireEvent.click(screen.getByText('login'));

    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
    });

    expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true });
  });

  test('login failure clears auth data and exposes the error', async () => {
    localStorage.setItem('accessToken', 'old-token');
    apiClient.defaults.headers.common.Authorization = 'Bearer old-token';
    authService.login.mockResolvedValueOnce({});

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });

    fireEvent.click(screen.getByText('login'));

    await waitFor(() => {
      expect(screen.getByTestId('login-error')).toHaveTextContent(
        'Resposta de login inválida ou sem token de acesso.'
      );
    });

    expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
    expect(localStorage.getItem('accessToken')).toBeNull();
    expect(apiClient.defaults.headers.common.Authorization).toBeUndefined();
  });

  test('login propagates backend payload errors after clearing auth data', async () => {
    localStorage.setItem('accessToken', 'old-token');
    apiClient.defaults.headers.common.Authorization = 'Bearer old-token';
    authService.login.mockRejectedValueOnce({
      response: { data: { detail: 'credenciais invalidas' } },
    });

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });

    fireEvent.click(screen.getByText('login'));

    await waitFor(() => {
      expect(screen.getByTestId('login-error')).toHaveTextContent('credenciais invalidas');
    });

    expect(localStorage.getItem('accessToken')).toBeNull();
    expect(apiClient.defaults.headers.common.Authorization).toBeUndefined();
  });

  test('login falls back to a generic error message when the failure has no payload or message', async () => {
    authService.login.mockRejectedValueOnce({});

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });

    fireEvent.click(screen.getByText('login'));

    await waitFor(() => {
      expect(screen.getByTestId('login-error')).toHaveTextContent(
        'Erro desconhecido durante o login.'
      );
    });
  });

  test('login clears auth data when the user payload is missing after authentication', async () => {
    authService.login.mockResolvedValueOnce({ access_token: 'login-token' });
    authService.getCurrentUser.mockResolvedValueOnce(null);

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId('is-loading')).toHaveTextContent('false');
    });

    fireEvent.click(screen.getByText('login'));

    await waitFor(() => {
      expect(screen.getByTestId('login-error')).toHaveTextContent(
        /Falha ao obter dados do usu.rio ap.s login\./i
      );
    });

    expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
    expect(localStorage.getItem('accessToken')).toBeNull();
    expect(apiClient.defaults.headers.common.Authorization).toBeUndefined();
  });

  test('logout clears the session and navigates back to login', async () => {
    localStorage.setItem('accessToken', 'stored-token');
    authService.getCurrentUser.mockResolvedValueOnce({ email: 'admin@example.com' });

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('true');
    });

    fireEvent.click(screen.getByText('logout'));

    await waitFor(() => {
      expect(screen.getByTestId('is-authenticated')).toHaveTextContent('false');
    });

    expect(localStorage.getItem('accessToken')).toBeNull();
    expect(apiClient.defaults.headers.common.Authorization).toBeUndefined();
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });

  test('throws when useAuth is called outside the provider', () => {
    expect(() => render(<InvalidAuthProbe />)).toThrow(
      'useAuth deve ser usado dentro de um AuthProvider'
    );
  });
});
