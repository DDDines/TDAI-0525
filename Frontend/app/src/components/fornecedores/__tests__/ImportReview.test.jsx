import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ImportReview from '../ImportReview.jsx';
import { showErrorToast, showSuccessToast } from '../../../utils/notifications';

jest.mock('../../../services/fornecedorService', () => ({
  __esModule: true,
  default: {
    getReviewData: jest.fn(() => Promise.resolve({ items: [{ nome: 'Prod1' }], total_items: 1 })),
    commitImport: jest.fn(() => Promise.resolve({})),
  }
}));

jest.mock('../../../utils/notifications', () => ({
  showErrorToast: jest.fn(),
  showSuccessToast: jest.fn(),
}));

import fornecedorService from '../../../services/fornecedorService';

let consoleErrorSpy;

beforeEach(() => {
  jest.clearAllMocks();
  consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  fornecedorService.getReviewData.mockResolvedValue({ items: [{ nome: 'Prod1' }], total_items: 1 });
  fornecedorService.commitImport.mockResolvedValue({});
});

afterEach(() => {
  consoleErrorSpy.mockRestore();
});

test('fetches review data and commits on confirm', async () => {
  render(<ImportReview jobId={5} isOpen={true} onClose={() => {}} />);
  await waitFor(() => expect(fornecedorService.getReviewData).toHaveBeenCalledWith(5, { skip: 0, limit: 10 }));
  expect(await screen.findByText('Prod1')).toBeInTheDocument();
  await userEvent.click(screen.getByText('Confirmar e Salvar Tudo'));
  expect(fornecedorService.commitImport).toHaveBeenCalledWith(5);
});

test('does not render when closed', () => {
  render(<ImportReview jobId={5} isOpen={false} onClose={() => {}} />);

  expect(screen.queryByText(/Revisar Importa/i)).not.toBeInTheDocument();
});

test('renders array review payloads with object cells and paginates review data', async () => {
  fornecedorService.getReviewData
    .mockResolvedValueOnce({
      items: [
        { nome: 'Prod1', meta: { sku: 'ABC-1' }, vazio: null },
        { nome: 'Prod2', meta: { sku: 'ABC-2' }, vazio: undefined },
      ],
      total_items: 11,
    })
    .mockResolvedValueOnce({
      items: [{ nome: 'Prod3', meta: { sku: 'ABC-3' }, vazio: null }],
      total_items: 11,
    });

  render(<ImportReview jobId={7} isOpen={true} onClose={() => {}} />);

  expect(await screen.findByText('{"sku":"ABC-1"}')).toBeInTheDocument();
  expect(screen.getByText(/Serão criados 11 produtos/i)).toBeInTheDocument();

  await userEvent.click(screen.getByRole('button', { name: /Próxima/i }));

  await waitFor(() => {
    expect(fornecedorService.getReviewData).toHaveBeenLastCalledWith(7, { skip: 10, limit: 10 });
  });
  expect(await screen.findByText('{"sku":"ABC-3"}')).toBeInTheDocument();
});

test('renders raw array review payloads and formats object cells', async () => {
  fornecedorService.getReviewData.mockResolvedValueOnce([
    { nome: 'Prod1', meta: { sku: 'ABC-1' }, vazio: null },
    { nome: 'Prod2', meta: { sku: 'ABC-2' }, vazio: undefined },
  ]);

  render(<ImportReview jobId={8} isOpen={true} onClose={() => {}} />);

  expect(await screen.findByText('{"sku":"ABC-1"}')).toBeInTheDocument();
  expect(screen.getByText(/Serão criados 2 produtos/i)).toBeInTheDocument();
});

test('shows review loading errors with backend payload details', async () => {
  fornecedorService.getReviewData.mockRejectedValueOnce({ detail: 'falha revisao' });

  render(<ImportReview jobId={9} isOpen={true} onClose={() => {}} />);

  await waitFor(() => {
    expect(showErrorToast).toHaveBeenCalledWith('falha revisao');
  });
});

test('shows commit errors with structured backend payload details', async () => {
  fornecedorService.commitImport.mockRejectedValueOnce({
    detail: { motivo: 'arquivo bloqueado' },
  });

  render(<ImportReview jobId={9} isOpen={true} onClose={() => {}} />);
  await screen.findByText('Prod1');
  await userEvent.click(screen.getByText('Confirmar e Salvar Tudo'));

  await waitFor(() => {
    expect(showErrorToast).toHaveBeenCalledWith({ motivo: 'arquivo bloqueado' });
  });
});

test('shows success feedback and closes after a successful commit', async () => {
  const onClose = jest.fn();

  render(<ImportReview jobId={10} isOpen={true} onClose={onClose} />);

  await screen.findByText('Prod1');
  await userEvent.click(screen.getByText('Confirmar e Salvar Tudo'));

  await waitFor(() => {
    expect(showSuccessToast).toHaveBeenCalledWith('Importação confirmada com sucesso!');
  });
  expect(onClose).toHaveBeenCalled();
});
