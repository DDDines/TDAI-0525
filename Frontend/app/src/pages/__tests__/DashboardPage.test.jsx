import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import DashboardPage from '../DashboardPage.jsx';
import authService from '../../services/authService';
import adminService from '../../services/adminService';
import dashboardService from '../../services/dashboardService';
import { showErrorToast } from '../../utils/notifications';

let consoleErrorSpy;

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
    });
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  test('renders a simplified admin dashboard shell', async () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText('Total produtos')).toBeInTheDocument();
    expect(screen.getByText('Em atenção')).toBeInTheDocument();
    expect(screen.getByText('Em andamento')).toBeInTheDocument();
    expect(screen.queryByText('Próximos passos')).not.toBeInTheDocument();
    expect(screen.queryByText('Prioridades do dia')).not.toBeInTheDocument();
    expect(screen.getByText('Status dos produtos')).toBeInTheDocument();
    expect(screen.getByText('Atividade recente')).toBeInTheDocument();
    expect(document.querySelectorAll('.pro-card-metric')).toHaveLength(0);
    expect(adminService.getTotalCounts).toHaveBeenCalled();
    expect(adminService.getProductStatusCounts).toHaveBeenCalled();
    expect(adminService.getRecentHistorico).toHaveBeenCalledWith(5);
  });

  test('renders the real dashboard for non-admin users without extra shortcut blocks', async () => {
    authService.getCurrentUser.mockResolvedValue({
      id: 2,
      is_superuser: false,
      plano: { nome: 'Gratuito' },
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(await screen.findByText(/Limites do plano/i)).toBeInTheDocument();
    expect(screen.getAllByText('Produtos').length).toBeGreaterThan(0);
    expect(screen.getByText('Busca web disponível')).toBeInTheDocument();
    expect(screen.getByText('IA disponível')).toBeInTheDocument();
    expect(screen.queryByText('Próximos passos')).not.toBeInTheDocument();
    expect(screen.queryByText('Onde agir agora')).not.toBeInTheDocument();
    expect(document.querySelectorAll('.dashboard-side-stat')).toHaveLength(0);
    expect(document.querySelectorAll('.pro-card-metric')).toHaveLength(0);
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

    expect(await screen.findByText('Total produtos')).toBeInTheDocument();
    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Erro ao buscar dados adicionais do dashboard:',
        expect.any(Error)
      );
    });
  });
});




