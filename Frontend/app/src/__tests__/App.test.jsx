import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from '../App.jsx';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { useWorkspace } from '../contexts/WorkspaceContext';

jest.mock('../contexts/AuthContext', () => ({
  AuthProvider: ({ children }) => <>{children}</>,
  useAuth: jest.fn(),
}));

jest.mock('../contexts/AppExperienceContext', () => ({
  AppExperienceProvider: ({ children }) => <>{children}</>,
}));

jest.mock('../contexts/ProductTypeContext', () => ({
  ProductTypeProvider: ({ children }) => <>{children}</>,
}));

jest.mock('../contexts/WorkspaceContext', () => ({
  WorkspaceProvider: ({ children }) => <>{children}</>,
  useWorkspace: jest.fn(),
}));

jest.mock('../contexts/ThemeContext', () => ({
  ThemeProvider: ({ children }) => <>{children}</>,
  useTheme: jest.fn(),
}));

jest.mock('react-toastify', () => ({
  ToastContainer: ({ theme }) => <div data-testid="toast-theme">{theme}</div>,
}));

jest.mock('../components/MainLayout', () => {
  const { Outlet } = jest.requireActual('react-router-dom');
  return {
    __esModule: true,
    default: () => (
      <div data-testid="main-layout">
        <Outlet />
      </div>
    ),
  };
});

jest.mock('../components/ProtectedRoute', () => ({
  __esModule: true,
  default: ({ children }) => <>{children}</>,
}));

jest.mock('../components/common/LoadingOverlay.jsx', () => ({
  __esModule: true,
  default: ({ message }) => <div>{message}</div>,
}));

jest.mock('../pages/LoginPage', () => ({
  __esModule: true,
  default: () => <div>login-page</div>,
}));

jest.mock('../pages/LandingPage', () => ({
  __esModule: true,
  default: () => <div>landing-page</div>,
}));

jest.mock('../pages/SignupPage', () => ({
  __esModule: true,
  default: () => <div>signup-page</div>,
}));

jest.mock('../pages/WorkspacePage', () => ({
  __esModule: true,
  default: () => <div>workspace-page</div>,
}));

jest.mock('../pages/DashboardPage', () => ({
  __esModule: true,
  default: () => <div>dashboard-page</div>,
}));

jest.mock('../pages/ProdutosPage', () => ({
  __esModule: true,
  default: () => <div>produtos-page</div>,
}));

jest.mock('../pages/ProdutoConteudoPage', () => ({
  __esModule: true,
  default: () => <div>produto-conteudo-page</div>,
}));

jest.mock('../pages/FornecedoresPage', () => ({
  __esModule: true,
  default: () => <div>fornecedores-page</div>,
}));

jest.mock('../pages/TiposProdutoPage', () => ({
  __esModule: true,
  default: () => <div>tipos-produto-page</div>,
}));

jest.mock('../pages/EnriquecimentoPage', () => ({
  __esModule: true,
  default: () => <div>enriquecimento-page</div>,
}));

jest.mock('../pages/HistoricoPage', () => ({
  __esModule: true,
  default: () => <div>historico-page</div>,
}));

jest.mock('../pages/PlanoPage', () => ({
  __esModule: true,
  default: () => <div>plano-page</div>,
}));

jest.mock('../pages/ConfiguracoesPage', () => ({
  __esModule: true,
  default: () => <div>configuracoes-page</div>,
}));

jest.mock('../pages/RecuperarSenhaPage', () => ({
  __esModule: true,
  default: () => <div>recuperar-senha-page</div>,
}));

jest.mock('../pages/ResetSenhaPage', () => ({
  __esModule: true,
  default: () => <div>resetar-senha-page</div>,
}));

jest.mock('../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
  },
}));

describe('App', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useTheme.mockReturnValue({ mode: 'light' });
    useAuth.mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });
    useWorkspace.mockReturnValue({
      hasWorkspace: true,
      isLoading: false,
    });
  });

  test('shows the global loading overlay while auth state is loading', () => {
    window.history.pushState({}, '', '/dashboard');
    useAuth.mockReturnValueOnce({
      isAuthenticated: false,
      isLoading: true,
    });
    useWorkspace.mockReturnValueOnce({
      hasWorkspace: false,
      isLoading: false,
    });

    render(<App />);

    expect(screen.getByText('Carregando Aplicação...')).toBeInTheDocument();
  });

  test('renders public and protected routes through the root router', () => {
    window.history.pushState({}, '', '/login');
    const { unmount } = render(<App />);
    expect(screen.getByText('login-page')).toBeInTheDocument();
    unmount();

    window.history.pushState({}, '', '/produtos');
    render(<App />);
    expect(screen.getByTestId('main-layout')).toBeInTheDocument();
    expect(screen.getByText('produtos-page')).toBeInTheDocument();
  });

  test('applies the toast theme from the current theme mode', () => {
    window.history.pushState({}, '', '/dashboard');
    useTheme.mockReturnValueOnce({ mode: 'dark' });

    render(<App />);

    expect(screen.getByTestId('toast-theme')).toHaveTextContent('dark');
  });

  test('redirects unknown paths back into the authenticated app shell', () => {
    window.history.pushState({}, '', '/rota-inexistente');

    render(<App />);

    expect(screen.getByTestId('main-layout')).toBeInTheDocument();
    expect(screen.getByText('dashboard-page')).toBeInTheDocument();
  });

  test('redirects authenticated users without a company into workspace setup', () => {
    window.history.pushState({}, '', '/');
    useWorkspace.mockReturnValueOnce({
      hasWorkspace: false,
      isLoading: false,
    });

    render(<App />);

    expect(screen.getByTestId('main-layout')).toBeInTheDocument();
    expect(window.location.pathname).toBe('/workspace');
    expect(window.location.search).toBe('?setup=1');
    expect(screen.getByText('workspace-page')).toBeInTheDocument();
  });
});
