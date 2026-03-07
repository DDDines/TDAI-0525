import { act, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ImportProgress from '../ImportProgress.jsx';
import fornecedorService from '../../../services/fornecedorService';

jest.mock('../../../services/fornecedorService', () => ({
  __esModule: true,
  default: {
    getImportProgress: jest.fn(),
  },
}));

jest.useFakeTimers();

const mockedService = fornecedorService;

beforeEach(() => {
  jest.clearAllMocks();
});

test('polls progress until pending review', async () => {
  mockedService.getImportProgress
    .mockResolvedValueOnce({ pages_processed: 1, total_pages: 5, status: 'PROCESSING' })
    .mockResolvedValueOnce({ pages_processed: 2, total_pages: 5, status: 'PENDING_REVIEW' });

  const onPendingReview = jest.fn();
  render(<ImportProgress jobId={10} onPendingReview={onPendingReview} />);

  expect(mockedService.getImportProgress).toHaveBeenCalledWith(10);
  await screen.findByText(/Processando p.*gina 1 de 5/i);

  await act(async () => {
    await jest.runOnlyPendingTimersAsync();
  });

  await screen.findByText(/Processando p.*gina 2 de 5/i);
  expect(onPendingReview).toHaveBeenCalled();
});

test('does not start polling without a job id and falls back to the default progress state', () => {
  render(<ImportProgress jobId={null} />);

  expect(mockedService.getImportProgress).not.toHaveBeenCalled();
  expect(screen.getByText(/Processando p.*gina 0 de 0/i)).toBeInTheDocument();
});

test('logs polling errors and supports payloads that only expose progress', async () => {
  const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  mockedService.getImportProgress
    .mockResolvedValueOnce({ progress: 3, total_pages: 6, status: 'PROCESSING' })
    .mockRejectedValueOnce(new Error('falha no polling'));

  render(<ImportProgress jobId={22} />);

  await screen.findByText(/Processando p.*gina 3 de 6/i);

  await act(async () => {
    await jest.runOnlyPendingTimersAsync();
  });

  expect(consoleErrorSpy).toHaveBeenCalledWith(
    'Erro ao consultar progresso de importação:',
    expect.any(Error)
  );
  consoleErrorSpy.mockRestore();
});

test('stops polling updates after unmounting', async () => {
  let resolveRequest;
  mockedService.getImportProgress.mockImplementation(
    () => new Promise((resolve) => {
      resolveRequest = resolve;
    })
  );

  const onPendingReview = jest.fn();
  const { unmount } = render(<ImportProgress jobId={23} onPendingReview={onPendingReview} />);
  expect(mockedService.getImportProgress).toHaveBeenCalledWith(23);

  unmount();
  await act(async () => {
    resolveRequest({ pages_processed: 4, total_pages: 9, status: 'PENDING_REVIEW' });
    await Promise.resolve();
  });

  expect(onPendingReview).not.toHaveBeenCalled();
});

test('falls back to zero totals, tolerates missing callbacks and ignores rejected requests after unmount', async () => {
  let rejectRequest;
  mockedService.getImportProgress
    .mockResolvedValueOnce({ progress: 0, status: 'PROCESSING' })
    .mockImplementationOnce(
      () =>
        new Promise((_, reject) => {
          rejectRequest = reject;
        })
    );

  const { unmount } = render(<ImportProgress jobId={24} />);

  await screen.findByText(/Processando p.*gina 0 de 0/i);

  await act(async () => {
    await jest.runOnlyPendingTimersAsync();
  });

  expect(typeof rejectRequest).toBe('function');

  unmount();
  await act(async () => {
    rejectRequest(new Error('falha tardia'));
    await Promise.resolve();
  });
});
