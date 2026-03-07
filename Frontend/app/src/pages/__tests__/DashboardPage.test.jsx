import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import DashboardPage from '../DashboardPage.jsx';
import authService from '../../services/authService';
import adminService from '../../services/adminService';
import searchService from '../../services/searchService';
import { showErrorToast } from '../../utils/notifications';

const mockNavigate = jest.fn();
let consoleErrorSpy;

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
    getCurrentUser: jest.fn(),
  },
}));

jest.mock('../../services/adminService', () => ({
  __esModule: true,
  default: {
    getTotalCounts: jest.fn(),
    getProductStatusCounts: jest.fn(),
    getRecentHistorico: jest.fn(),
  },
}));

jest.mock('../../services/searchService', () => ({
  __esModule: true,
  default: {
    searchAll: jest.fn(),
  },
}));

jest.mock('../../utils/notifications', () => ({
  showErrorToast: jest.fn(),
}));

describe('DashboardPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    authService.getCurrentUser.mockResolvedValue({ id: 1, is_superuser: true });
    adminService.getTotalCounts.mockResolvedValue({
      total_produtos: 10,
      total_fornecedores: 3,
      total_usuarios: 2,
      total_geracoes_ia_mes: 1,
      total_enriquecimentos_mes: 0,
    });
    adminService.getProductStatusCounts.mockResolvedValue([
      { status: 'NAO_INICIADO', total: 6 },
    ]);
    adminService.getRecentHistorico.mockResolvedValue([
      {
        id: 99,
        entidade: 'produto',
        acao: 'CRIACAO',
        user_id: 1,
        created_at: '2025-12-01T00:00:00Z',
      },
    ]);
    searchService.searchAll.mockImplementation(async (term) => {
      if (term === 'abc') {
        return { results: [{ type: 'produto', id: 42, name: 'Produto 42' }] };
      }
      return { results: [] };
    });
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  test('renders admin dashboard and allows search navigation', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('Total Produtos')).toBeInTheDocument();
    expect(adminService.getTotalCounts).toHaveBeenCalled();
    expect(adminService.getProductStatusCounts).toHaveBeenCalled();
    expect(adminService.getRecentHistorico).toHaveBeenCalledWith(5);

    const searchInput = screen.getByPlaceholderText(/pesquisar/i);
    await userEvent.type(searchInput, 'abc');

    expect(await screen.findByText('Produto 42')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /ver detalhes/i }));

    expect(mockNavigate).toHaveBeenCalledWith('/produtos?id=42');
  });

  test('shows fallback dashboard for non-admin users', async () => {
    authService.getCurrentUser.mockResolvedValue({ id: 2, is_superuser: false });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText(/bem-vindo ao catalogai/i)).toBeInTheDocument();
    expect(adminService.getTotalCounts).not.toHaveBeenCalled();
  });

  test('shows error toast when initial dashboard load fails', async () => {
    authService.getCurrentUser.mockRejectedValue(new Error('Falha ao carregar dashboard'));

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao carregar dashboard');
    });
  });

  test('prefers error detail and default fallback messages when dashboard bootstrap fails', async () => {
    authService.getCurrentUser.mockRejectedValueOnce({ detail: 'detalhe do backend' });

    const { unmount } = render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('detalhe do backend');
    });

    unmount();
    jest.clearAllMocks();
    authService.getCurrentUser.mockRejectedValueOnce({});

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao carregar dados do dashboard.');
    });
  });

  test('logs additional admin data failures without breaking the dashboard shell', async () => {
    adminService.getProductStatusCounts.mockRejectedValueOnce(new Error('status offline'));

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('Total Produtos')).toBeInTheDocument();
    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Erro ao buscar dados adicionais do dashboard:',
        expect.any(Error)
      );
    });
  });

  test('logs search failures and keeps the screen usable', async () => {
    searchService.searchAll.mockRejectedValueOnce(new Error('busca indisponivel'));

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('Total Produtos')).toBeInTheDocument();
    await userEvent.type(screen.getByPlaceholderText(/pesquisar/i), 'erro');

    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith('Erro ao buscar:', expect.any(Error));
    });
  });

  test('renders zero fallbacks and empty-search feedback when admin metrics are sparse', async () => {
    adminService.getTotalCounts.mockResolvedValueOnce({
      total_produtos: null,
      total_fornecedores: undefined,
      total_usuarios: undefined,
      total_geracoes_ia_mes: null,
      total_enriquecimentos_mes: undefined,
    });
    searchService.searchAll.mockResolvedValueOnce({}).mockResolvedValueOnce({});

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('Total Produtos')).toBeInTheDocument();
    expect(screen.getAllByText('0').length).toBeGreaterThan(0);
    expect(screen.getByText('Usuários: 0')).toBeInTheDocument();
    expect(screen.getByText('Gerações IA (mês): 0')).toBeInTheDocument();
    expect(screen.getByText('Enriquecimentos (mês): 0')).toBeInTheDocument();

    const searchInput = screen.getByPlaceholderText(/pesquisar/i);
    await userEvent.type(searchInput, 'sem resultado');

    expect(await screen.findByText(/Nenhum resultado encontrado/i)).toBeInTheDocument();
  });
});
