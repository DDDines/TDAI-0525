import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import DashboardPage from '../DashboardPage.jsx';
import authService from '../../services/authService';
import adminService from '../../services/adminService';
import dashboardService from '../../services/dashboardService';
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

jest.mock('../../services/dashboardService', () => ({
  __esModule: true,
  default: {
    getMyDashboard: jest.fn(),
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
    adminService.getProductStatusCounts.mockResolvedValue([{ status: 'NAO_INICIADO', total: 6 }]);
    adminService.getRecentHistorico.mockResolvedValue([
      {
        id: 99,
        entidade: 'produto',
        acao: 'CRIACAO',
        user_id: 1,
        created_at: '2025-12-01T00:00:00Z',
      },
    ]);
    dashboardService.getMyDashboard.mockResolvedValue({
      plano_nome: 'Gratuito',
      product_experience_mode: 'basic',
      limites: {
        produtos: 10,
        enriquecimento_web: 25,
        geracao_ia: 0,
      },
      uso_mes_atual: {
        geracao_ia: 0,
        enriquecimento_web: 3,
      },
      totais: {
        produtos: 7,
        fornecedores: 2,
      },
      status_produtos: [{ status: 'CONCLUIDO', total: 4 }],
      atividade_recente: [
        {
          id: 11,
          entidade: 'produto',
          tipo_acao: 'ATUALIZACAO',
          created_at: '2025-12-01T00:00:00Z',
        },
      ],
      atalhos: [{ label: 'Produtos', route: '/produtos' }],
    });
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  test('renders admin dashboard shell without duplicating the internal title', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('Total Produtos')).toBeInTheDocument();
    expect(document.querySelectorAll('.pro-card-metric')).toHaveLength(4);
    expect(screen.getByText('Painel administrativo')).toBeInTheDocument();
    expect(screen.queryByText('Visao geral')).not.toBeInTheDocument();
    expect(screen.getByText('Prioridades do dia')).toBeInTheDocument();
    expect(screen.queryByText(/Busca rapida do sistema/i)).not.toBeInTheDocument();
    expect(adminService.getTotalCounts).toHaveBeenCalled();
    expect(adminService.getProductStatusCounts).toHaveBeenCalled();
    expect(adminService.getRecentHistorico).toHaveBeenCalledWith(5);
  });

  test('renders the real dashboard for non-admin users', async () => {
    authService.getCurrentUser.mockResolvedValue({
      id: 2,
      is_superuser: false,
      plano: { nome: 'Gratuito' },
      product_experience_mode: 'basic',
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText(/Limites do plano/i)).toBeInTheDocument();
    expect(screen.getByText('Painel do cliente')).toBeInTheDocument();
    expect(screen.getByText(/Plano Gratuito/i)).toBeInTheDocument();
    expect(screen.queryByText('Modo Basico')).not.toBeInTheDocument();
    expect(document.querySelectorAll('.dashboard-side-stat')).toHaveLength(0);
    expect(screen.queryByText('Acoes rapidas')).not.toBeInTheDocument();
    expect(screen.queryByText(/Busca rapida do sistema/i)).not.toBeInTheDocument();
    expect(document.querySelectorAll('.pro-card-metric')).toHaveLength(4);
    expect(dashboardService.getMyDashboard).toHaveBeenCalled();
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

  test('renders zero fallbacks and empty-search feedback when admin metrics are sparse', async () => {
    adminService.getTotalCounts.mockResolvedValueOnce({
      total_produtos: null,
      total_fornecedores: undefined,
      total_usuarios: undefined,
      total_geracoes_ia_mes: null,
      total_enriquecimentos_mes: undefined,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('Total Produtos')).toBeInTheDocument();
    expect(screen.getAllByText('0').length).toBeGreaterThan(0);
    expect(screen.getByText('Usuarios')).toBeInTheDocument();
    expect(screen.getByText('Geracoes IA no mes')).toBeInTheDocument();
    expect(screen.queryByText(/Busca rapida do sistema/i)).not.toBeInTheDocument();
  });
});
