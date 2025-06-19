import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ImportReview from '../ImportReview.jsx';

jest.mock('../../../services/fornecedorService', () => ({
  __esModule: true,
  default: {
    getReviewData: jest.fn(() => Promise.resolve({ items: [{ nome: 'Prod1' }], total_items: 1 })),
    commitImport: jest.fn(() => Promise.resolve({})),
  }
}));

import fornecedorService from '../../../services/fornecedorService';

test('fetches review data and commits on confirm', async () => {
  render(<ImportReview jobId={5} isOpen={true} onClose={() => {}} />);
  await waitFor(() => expect(fornecedorService.getReviewData).toHaveBeenCalledWith(5, { skip: 0, limit: 10 }));
  expect(await screen.findByText('Prod1')).toBeInTheDocument();
  await userEvent.click(screen.getByText('Confirmar e Salvar Tudo'));
  expect(fornecedorService.commitImport).toHaveBeenCalledWith(5);
});
