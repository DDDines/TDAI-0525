import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import HistoricoPage from '../HistoricoPage.jsx';
import usoIAService from '../../services/usoIAService';
import historicoService from '../../services/historicoService';
import { useAuth } from '../../contexts/AuthContext';
import { showErrorToast } from '../../utils/notifications';

jest.mock('../../services/usoIAService', () => ({
  __esModule: true,
  default: {
    getMeuHistoricoUsoIA: jest.fn(),
    getTiposHistorico: jest.fn(),
  },
}));

jest.mock('../../services/historicoService', () => ({
  __esModule: true,
  default: {
    getHistorico: jest.fn(),
  },
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../../utils/notifications', () => ({
  showErrorToast: jest.fn(),
}));

jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
  },
}));

jest.mock('../../components/common/PaginationControls', () => ({
  __esModule: true,
  default: ({ onPageChange }) => <button onClick={() => onPageChange(1)}>next-page</button>,
}));

jest.mock('../../components/common/LoadingPopup.jsx', () => ({
  __esModule: true,
  default: ({ isOpen, message }) => (isOpen ? <div>{message}</div> : null),
}));

describe('HistoricoPage', () => {
  let consoleErrorSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    useAuth.mockReturnValue({
      user: { id: 8 },
      isLoading: false,
    });
    usoIAService.getMeuHistoricoUsoIA.mockResolvedValue({
      items: [
        {
          id: 1,
          produto_id: 2558,
          tipo_acao: 'enriquecimento_web',
          resposta_ia: 'Texto gerado para o produto',
          tokens_prompt: 10,
          tokens_resposta: 12,
          created_at: '2026-03-07T10:20:30.000Z',
        },
      ],
      total_items: 15,
    });
    historicoService.getHistorico.mockResolvedValue({
      items: [
        {
          id: 9,
          entidade: 'produto',
          acao: 'atualizacao',
          entity_id: 2558,
          created_at: '2026-03-07T11:20:30.000Z',
        },
      ],
      total_items: 1,
    });
    usoIAService.getTiposHistorico.mockResolvedValue([
      'enriquecimento_web',
      'geracao_titulo_ia',
    ]);
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  test('skips API calls when the user is not authenticated', async () => {
    useAuth.mockReturnValue({
      user: null,
      isLoading: false,
    });

    render(<HistoricoPage />);

    await waitFor(() => {
      expect(screen.getByText('Nenhum registro de uso de IA encontrado.')).toBeInTheDocument();
    });

    expect(usoIAService.getMeuHistoricoUsoIA).not.toHaveBeenCalled();
    expect(historicoService.getHistorico).not.toHaveBeenCalled();
  });

  test('loads IA history, system events, filters and paginates results', async () => {
    render(<HistoricoPage />);

    expect(await screen.findByText(/Texto gerado para o produto/)).toBeInTheDocument();
    expect(screen.getByText('produto')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Filtrar por tipo de ação:'), {
      target: { value: 'geracao_titulo_ia' },
    });

    await waitFor(() => {
      expect(usoIAService.getMeuHistoricoUsoIA).toHaveBeenLastCalledWith({
        skip: 0,
        limit: 10,
        tipo_acao: 'geracao_titulo_ia',
      });
    });

    fireEvent.click(screen.getByText('next-page'));

    await waitFor(() => {
      expect(usoIAService.getMeuHistoricoUsoIA).toHaveBeenLastCalledWith({
        skip: 10,
        limit: 10,
        tipo_acao: 'geracao_titulo_ia',
      });
    });
  });

  test('shows an error toast when the IA history request fails', async () => {
    usoIAService.getMeuHistoricoUsoIA.mockRejectedValueOnce(new Error('historico indisponivel'));

    render(<HistoricoPage />);

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('historico indisponivel');
    });
    expect(screen.getByText(/Erro ao carregar histórico/)).toBeInTheDocument();
  });
});
