import { act, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ImportProgress from '../ImportProgress.jsx';
import fornecedorService from '../../../services/fornecedorService';
import { renderWithQueryClient } from '../../../../test-utils/renderWithQueryClient.jsx';

jest.mock('../../../services/fornecedorService', () => ({
  __esModule: true,
  default: {
    getImportacaoStatus: jest.fn(),
    getImportacaoResult: jest.fn(),
  },
}));

function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

async function renderAndFlush(ui) {
  let view;
  await act(async () => {
    view = renderWithQueryClient(ui);
    await Promise.resolve();
    await Promise.resolve();
  });
  return view;
}

describe('common ImportProgress', () => {
  let consoleErrorSpy;

  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(async () => {
    await act(async () => {
      await jest.runOnlyPendingTimersAsync();
    });
    consoleErrorSpy.mockRestore();
    jest.useRealTimers();
  });

  test('shows initial state and does not poll without file id', () => {
    renderWithQueryClient(<ImportProgress fileId={null} onDone={jest.fn()} />);

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
    await renderAndFlush(<ImportProgress fileId={55} onDone={onDone} />);

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
    await renderAndFlush(<ImportProgress fileId={77} onDone={onDone} />);

    for (let index = 0; index < 19; index += 1) {
      await act(async () => {
        await jest.runOnlyPendingTimersAsync();
      });
    }

    expect(
      await screen.findByText(/resultado final ainda n(a|ã)o foi consolidado/i)
    ).toBeInTheDocument();
    expect(onDone).toHaveBeenCalledWith(null);
    expect(fornecedorService.getImportacaoResult).not.toHaveBeenCalled();
  });

  test('shows fetch error and resolves with null when status polling fails', async () => {
    fornecedorService.getImportacaoStatus.mockRejectedValue(new Error('Falha de rede'));

    const onDone = jest.fn();
    await renderAndFlush(<ImportProgress fileId={12} onDone={onDone} />);

    expect(await screen.findByText('Falha de rede')).toBeInTheDocument();
    expect(onDone).toHaveBeenCalledWith(null);
  });

  test('renders non-terminal progress information while import is still running', async () => {
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'PROCESSING',
      pages_processed: 2,
      total_pages: 5,
    });

    const { unmount } = await renderAndFlush(<ImportProgress fileId={91} onDone={jest.fn()} />);

    expect(await screen.findByText(/Processando 2 de 5 p(a|á)ginas/i)).toBeInTheDocument();
    expect(fornecedorService.getImportacaoResult).not.toHaveBeenCalled();

    unmount();
    await act(async () => {
      await Promise.resolve();
    });
  });

  test('falls back to sparse payload defaults while still rendering progress', async () => {
    fornecedorService.getImportacaoStatus.mockResolvedValueOnce({
      status: null,
      pages_total: 7,
    });

    await renderAndFlush(<ImportProgress fileId={97} />);

    expect(await screen.findByText(/Processando 0 de 7 p(a|á)ginas/i)).toBeInTheDocument();
    expect(fornecedorService.getImportacaoResult).not.toHaveBeenCalled();
  });

  test('falls back to zero total pages when the sparse payload has no counters at all', async () => {
    fornecedorService.getImportacaoStatus.mockResolvedValueOnce({
      status: 'PROCESSING',
    });

    await renderAndFlush(<ImportProgress fileId={101} />);

    expect(await screen.findByText(/Processando 0 de 0 p(a|á)ginas/i)).toBeInTheDocument();
  });

  test('keeps polling when the final result is not ready yet and then resolves', async () => {
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'DONE',
      pages_processed: 4,
      total_pages: 4,
      result_ready: true,
    });
    fornecedorService.getImportacaoResult
      .mockResolvedValueOnce({ ready: false })
      .mockResolvedValueOnce({ ready: true, created: 3 });

    const onDone = jest.fn();
    await renderAndFlush(<ImportProgress fileId={92} onDone={onDone} />);

    await act(async () => {
      await jest.runOnlyPendingTimersAsync();
    });

    await waitFor(() => {
      expect(fornecedorService.getImportacaoResult).toHaveBeenCalledTimes(2);
    });
    expect(onDone).toHaveBeenCalledWith({ ready: true, created: 3 });
  });

  test('shows a timeout when the final result stays pending after repeated ready checks', async () => {
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'DONE',
      pages_processed: 4,
      total_pages: 4,
      result_ready: true,
    });
    fornecedorService.getImportacaoResult.mockResolvedValue({ ready: false });

    const onDone = jest.fn();
    await renderAndFlush(<ImportProgress fileId={93} onDone={onDone} />);

    for (let index = 0; index < 19; index += 1) {
      await act(async () => {
        await jest.runOnlyPendingTimersAsync();
      });
    }

    expect(
      await screen.findByText(/Resultado final ainda pendente ap(o|ó)s o tempo limite de espera/i)
    ).toBeInTheDocument();
    expect(onDone).toHaveBeenCalledWith(null);
  });

  test('resolves with null when the final result fetch throws', async () => {
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'DONE',
      pages_processed: 1,
      total_pages: 1,
      result_ready: true,
    });
    fornecedorService.getImportacaoResult.mockRejectedValue(new Error('falha final'));

    const onDone = jest.fn();
    await renderAndFlush(<ImportProgress fileId={94} onDone={onDone} />);

    await waitFor(() => {
      expect(onDone).toHaveBeenCalledWith(null);
    });
  });

  test('supports timeout and polling error flows without an onDone callback', async () => {
    fornecedorService.getImportacaoStatus.mockResolvedValue({
      status: 'DONE',
      pages_processed: 1,
      total_pages: 1,
      result_ready: true,
    });
    fornecedorService.getImportacaoResult.mockResolvedValue({ ready: false });

    const { unmount } = await renderAndFlush(<ImportProgress fileId={98} />);

    for (let index = 0; index < 19; index += 1) {
      await act(async () => {
        await jest.runOnlyPendingTimersAsync();
      });
    }

    expect(
      await screen.findByText(/Resultado final ainda pendente ap(o|ó)s o tempo limite de espera/i)
    ).toBeInTheDocument();

    unmount();
    fornecedorService.getImportacaoStatus.mockRejectedValueOnce({});
    await renderAndFlush(<ImportProgress fileId={99} />);

    expect(await screen.findByText('Erro ao consultar status')).toBeInTheDocument();
  });

  test('ignores stale status responses after the component unmounts', async () => {
    const pendingStatus = createDeferred();
    fornecedorService.getImportacaoStatus.mockImplementationOnce(() => pendingStatus.promise);

    const onDone = jest.fn();
    const { unmount } = await renderAndFlush(<ImportProgress fileId={95} onDone={onDone} />);

    unmount();

    await act(async () => {
      pendingStatus.resolve({
        status: 'DONE',
        pages_processed: 1,
        total_pages: 1,
        result_ready: true,
      });
      await Promise.resolve();
    });

    expect(onDone).not.toHaveBeenCalled();
  });

  test('ignores stale final result responses after the component unmounts', async () => {
    const pendingResult = createDeferred();
    fornecedorService.getImportacaoStatus.mockResolvedValueOnce({
      status: 'DONE',
      pages_processed: 1,
      total_pages: 1,
      result_ready: true,
    });
    fornecedorService.getImportacaoResult.mockImplementationOnce(() => pendingResult.promise);

    const onDone = jest.fn();
    const { unmount } = await renderAndFlush(<ImportProgress fileId={96} onDone={onDone} />);

    await waitFor(() => {
      expect(fornecedorService.getImportacaoResult).toHaveBeenCalledWith(96);
    });

    unmount();

    await act(async () => {
      pendingResult.resolve({ ready: true, created: 2 });
      await Promise.resolve();
    });

    expect(onDone).not.toHaveBeenCalled();
  });

  test('ignores stale final result failures after the component unmounts', async () => {
    const pendingResult = createDeferred();
    fornecedorService.getImportacaoStatus.mockResolvedValueOnce({
      status: 'DONE',
      pages_processed: 1,
      total_pages: 1,
      result_ready: true,
    });
    fornecedorService.getImportacaoResult.mockImplementationOnce(() => pendingResult.promise);

    const onDone = jest.fn();
    const { unmount } = await renderAndFlush(<ImportProgress fileId={102} onDone={onDone} />);

    await waitFor(() => {
      expect(fornecedorService.getImportacaoResult).toHaveBeenCalledWith(102);
    });

    unmount();

    await act(async () => {
      pendingResult.reject(new Error('falha final tardia'));
      await Promise.resolve();
    });

    expect(onDone).not.toHaveBeenCalled();
  });

  test('ignores stale polling failures after the component unmounts', async () => {
    const pendingStatus = createDeferred();
    fornecedorService.getImportacaoStatus.mockImplementationOnce(() => pendingStatus.promise);

    const onDone = jest.fn();
    const { unmount } = await renderAndFlush(<ImportProgress fileId={103} onDone={onDone} />);

    unmount();

    await act(async () => {
      pendingStatus.reject(new Error('falha polling tardia'));
      await Promise.resolve();
    });

    expect(onDone).not.toHaveBeenCalled();
  });
});


