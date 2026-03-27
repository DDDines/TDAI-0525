import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import HistoricoPage from '../HistoricoPage.jsx';
import usoIAService from '../../services/usoIAService';
import historicoService from '../../services/historicoService';
import { useAuth } from '../../contexts/AuthContext';
import { useWorkspace } from '../../contexts/WorkspaceContext';
import logger from '../../utils/logger';

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

jest.mock('../../contexts/WorkspaceContext', () => ({
  useWorkspace: jest.fn(),
}));

jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
  },
}));

jest.mock('../../components/common/PaginationControls', () => ({
  __esModule: true,
  default: ({
    currentPage,
    itemsPerPage,
    onItemsPerPageChange,
    onPageChange,
    totalItems,
  }) => (
    <div>
      <span>{`pagina-${currentPage}`}</span>
      <span>{`total-${totalItems}`}</span>
      <button onClick={() => onPageChange(1)}>next-page</button>
      {onItemsPerPageChange ? (
        <button onClick={() => onItemsPerPageChange(itemsPerPage === 10 ? 25 : 10)}>
          change-size
        </button>
      ) : null}
    </div>
  ),
}));

describe('HistoricoPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      user: { id: 8 },
      isLoading: false,
    });
    useWorkspace.mockReturnValue({
      workspace: { nome: 'Dines' },
    });
    usoIAService.getMeuHistoricoUsoIA.mockResolvedValue({
      items: [
        {
          id: 1,
          produto_id: 2558,
          tipo_acao: 'enriquecimento_web_produto',
          provedor_ia: 'lm_studio',
          modelo_ia: 'gemma-3-12b',
          prompt_utilizado: 'Prompt de teste',
          resposta_ia: 'Texto gerado para o produto',
          tokens_prompt: 10,
          tokens_resposta: 12,
          custo_estimado_usd: 0.0042,
          creditos_consumidos: 2,
          status: 'SUCESSO',
          detalhes_erro: null,
          created_at: '2026-03-07T10:20:30.000Z',
        },
        {
          id: 2,
          produto_id: 2559,
          tipo_acao: 'criacao_descricao_produto',
          provedor_ia: 'lm_studio',
          modelo_ia: 'gemma-3-12b',
          prompt_utilizado: 'Prompt com falha',
          resposta_ia: '',
          tokens_prompt: 5,
          tokens_resposta: 0,
          custo_estimado_usd: null,
          creditos_consumidos: 1,
          status: 'FALHA',
          detalhes_erro: 'timeout no provider',
          created_at: '2026-03-08T08:00:00.000Z',
        },
      ],
      total_items: 15,
    });
    historicoService.getHistorico.mockResolvedValue({
      items: [
        {
          id: 9,
          user_id: 8,
          entidade: 'produto',
          acao: 'ATUALIZACAO',
          entity_id: 2558,
          detalhes_json: { nome_base: 'Produto Teste', campo: 'descricao' },
          created_at: '2026-03-07T11:20:30.000Z',
        },
        {
          id: 10,
          user_id: 8,
          entidade: 'fornecedor',
          acao: 'CRIACAO',
          entity_id: 20,
          detalhes_json: { nome: 'Fornecedor XPTO' },
          created_at: '2026-03-08T09:00:00.000Z',
        },
      ],
      total_items: 4,
    });
    usoIAService.getTiposHistorico.mockResolvedValue([
      'enriquecimento_web_produto',
      'criacao_descricao_produto',
    ]);
  });

  test('nao chama APIs quando o usuario nao esta autenticado', async () => {
    useAuth.mockReturnValue({
      user: null,
      isLoading: false,
    });

    render(<HistoricoPage />);

    await waitFor(() => {
      expect(screen.getByText(/Nenhuma execução com IA encontrada com os filtros atuais/i)).toBeInTheDocument();
    });

    expect(usoIAService.getMeuHistoricoUsoIA).not.toHaveBeenCalled();
    expect(historicoService.getHistorico).not.toHaveBeenCalled();
  });

  test('mostra estado de carregamento enquanto a autenticação ainda não terminou', () => {
    useAuth.mockReturnValue({
      user: { id: 8 },
      isLoading: true,
    });

    render(<HistoricoPage />);

    expect(screen.getByText(/Carregando monitoramento/i)).toBeInTheDocument();
    expect(usoIAService.getMeuHistoricoUsoIA).not.toHaveBeenCalled();
    expect(historicoService.getHistorico).not.toHaveBeenCalled();
  });

  test('carrega resumo, filtro de IA e usa tipo_geracao corretamente', async () => {
    render(<HistoricoPage />);

    expect(await screen.findByText(/Central de monitoramento/i)).toBeInTheDocument();
    expect(screen.getByText('Execuções IA')).toBeInTheDocument();
    expect(screen.getByText('15')).toBeInTheDocument();
    expect(screen.getByText('Falhas ativas')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Tipo de ação de IA/i), {
      target: { value: 'criacao_descricao_produto' },
    });

    await waitFor(() => {
      expect(usoIAService.getMeuHistoricoUsoIA).toHaveBeenLastCalledWith({
        data_fim: undefined,
        data_inicio: undefined,
        limit: 10,
        skip: 0,
        tipo_geracao: 'criacao_descricao_produto',
      });
    });

    fireEvent.click(screen.getByText('next-page'));

    await waitFor(() => {
      expect(usoIAService.getMeuHistoricoUsoIA).toHaveBeenLastCalledWith({
        data_fim: undefined,
        data_inicio: undefined,
        limit: 10,
        skip: 10,
        tipo_geracao: 'criacao_descricao_produto',
      });
    });
  });

  test('expande detalhes do uso de IA e mostra prompt, resposta e erro', async () => {
    render(<HistoricoPage />);

    expect(await screen.findByText(/Texto gerado para o produto/i)).toBeInTheDocument();

    const detailButtons = screen.getAllByRole('button', { name: /^Ver$/i });
    fireEvent.click(detailButtons[0]);

    expect(await screen.findByText(/Prompt utilizado/i)).toBeInTheDocument();
    expect(screen.getByText(/Prompt de teste/i)).toBeInTheDocument();
    expect(screen.getByText(/Resposta retornada/i)).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button', { name: /^Ver$/i })[0]);
    expect(await screen.findByText(/Erro registrado/i)).toBeInTheDocument();
    expect(screen.getAllByText(/timeout no provider/i).length).toBeGreaterThan(0);
  });

  test('separa eventos do sistema em aba propria e filtra por entidade e acao', async () => {
    render(<HistoricoPage />);

    await screen.findByText(/Central de monitoramento/i);

    fireEvent.click(screen.getByRole('tab', { name: /Eventos da plataforma/i }));
    expect(await screen.findByLabelText(/Entidade do histórico do sistema/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Entidade do histórico do sistema/i), {
      target: { value: 'produto' },
    });

    await waitFor(() => {
      expect(historicoService.getHistorico).toHaveBeenLastCalledWith({
        acao: undefined,
        entidade: 'produto',
        limit: 10,
        skip: 0,
      });
    });

    fireEvent.change(screen.getByLabelText(/Ação do histórico do sistema/i), {
      target: { value: 'ATUALIZACAO' },
    });

    await waitFor(() => {
      expect(historicoService.getHistorico).toHaveBeenLastCalledWith({
        acao: 'ATUALIZACAO',
        entidade: 'produto',
        limit: 10,
        skip: 0,
      });
    });

    fireEvent.click(screen.getAllByRole('button', { name: /^Ver$/i })[0]);
    expect(await screen.findByText(/Detalhes registrados/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Produto Teste/i).length).toBeGreaterThan(0);
  });

  test('aplica busca textual local nas duas abas', async () => {
    render(<HistoricoPage />);

    await screen.findByText(/Central de monitoramento/i);

    fireEvent.change(screen.getByLabelText(/Busca textual no histórico de IA/i), {
      target: { value: 'timeout' },
    });

    await waitFor(() => {
      expect(screen.getByText(/timeout no provider/i)).toBeInTheDocument();
      expect(screen.queryByText(/Texto gerado para o produto/i)).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('tab', { name: /Eventos da plataforma/i }));
    fireEvent.change(screen.getByLabelText(/Busca textual no histórico do sistema/i), {
      target: { value: 'Fornecedor XPTO' },
    });

    await waitFor(() => {
      const table = screen.getByRole('table');
      expect(within(table).getByText(/Nome relacionado: Fornecedor XPTO/i)).toBeInTheDocument();
      expect(within(table).queryByText(/Produto relacionado: Produto Teste/i)).not.toBeInTheDocument();
    });
  });

  test('renderiza estado de erro do historico de IA sem quebrar a pagina', async () => {
    usoIAService.getMeuHistoricoUsoIA.mockRejectedValueOnce(new Error('historico indisponivel'));

    render(<HistoricoPage />);

    expect(await screen.findByText(/historico indisponivel/i)).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Eventos da plataforma/i })).toBeInTheDocument();
  });

  test('registra warnings e erros secundarios para payloads inesperados', async () => {
    const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    usoIAService.getMeuHistoricoUsoIA.mockResolvedValueOnce({ invalid: true });
    historicoService.getHistorico.mockResolvedValueOnce({ invalid: true });
    usoIAService.getTiposHistorico.mockRejectedValueOnce(new Error('falha tipos'));

    render(<HistoricoPage />);

    await waitFor(() => {
      expect(screen.getByText(/Nenhuma execução com IA encontrada com os filtros atuais/i)).toBeInTheDocument();
    });

    expect(consoleWarnSpy).toHaveBeenCalledWith(
      'HistoricoPage: formato de dados inesperado recebido para historico IA:',
      { invalid: true }
    );
    expect(consoleWarnSpy).toHaveBeenCalledWith(
      'HistoricoPage: formato de dados inesperado recebido para historico do sistema:',
      { invalid: true }
    );
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'HistoricoPage: erro ao carregar tipos de acao de IA:',
      expect.any(Error)
    );

    consoleWarnSpy.mockRestore();
    consoleErrorSpy.mockRestore();
  });

  test('mantém o log de autenticação enquanto aguarda carregar histórico autenticado', () => {
    useAuth.mockReturnValue({
      user: { id: 8 },
      isLoading: true,
    });

    render(<HistoricoPage />);

    expect(logger.log).not.toHaveBeenCalledWith(expect.stringMatching(/usuario nao autenticado/i));
  });
});
