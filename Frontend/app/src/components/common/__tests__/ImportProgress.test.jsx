import { act, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ImportProgress from '../ImportProgress.jsx';
import fornecedorService from '../../../services/fornecedorService';

jest.mock('../../../services/fornecedorService', () => ({
  __esModule: true,
  default: {
    getImportacaoStatus: jest.fn(),
    getImportacaoResult: jest.fn(),
  },
}));

describe('common ImportProgress', () => {
  let consoleErrorSpy;

  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  test('shows initial state and does not poll without file id', () => {
    render(<ImportProgress fileId={null} onDone={jest.fn()} />);

    expect(screen.getByText(/Iniciando processamento/i)).toBeInTheDocument();
    expect(fornecedorService.getImportacaoStatus).not.toHaveBeenCalled();
  });

  test('polls until a terminal status fetches final result', async () => {
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'DONE',
      pages_processed: 4,
      total_pages: 4,
      result_ready: true,
    });
    fornecedorService.getImportacaoResult.mockResolvedValue({
      ready: true,
      created: 8,
    });

    const onDone = jest.fn();
    render(<ImportProgress fileId={55} onDone={onDone} />);

    expect(await screen.findByText(/Status: DONE/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(fornecedorService.getImportacaoResult).toHaveBeenCalledWith(55);
    });
    expect(onDone).toHaveBeenCalledWith({ ready: true, created: 8 });
  });

  test('times out waiting for final consolidated result after repeated terminal polls', async () => {
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'PARTIAL',
      pages_processed: 3,
      total_pages: 3,
      result_ready: false,
    });

    const onDone = jest.fn();
    render(<ImportProgress fileId={77} onDone={onDone} />);

    for (let index = 0; index < 19; index += 1) {
      await act(async () => {
        await jest.runOnlyPendingTimersAsync();
      });
    }

    expect(
      await screen.findByText(/resultado final ainda n[ãa]o foi consolidado/i),
    ).toBeInTheDocument();
    expect(onDone).toHaveBeenCalledWith(null);
    expect(fornecedorService.getImportacaoResult).not.toHaveBeenCalled();
  });

  test('shows fetch error and resolves with null when status polling fails', async () => {
    fornecedorService.getImportacaoStatus.mockRejectedValue(new Error('Falha de rede'));

    const onDone = jest.fn();
    render(<ImportProgress fileId={12} onDone={onDone} />);

    expect(await screen.findByText('Falha de rede')).toBeInTheDocument();
    expect(onDone).toHaveBeenCalledWith(null);
  });
});
