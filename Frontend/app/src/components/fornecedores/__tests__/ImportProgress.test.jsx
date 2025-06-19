import { render, screen } from '@testing-library/react';
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

test('polls progress until pending review', async () => {
  mockedService.getImportProgress
    .mockResolvedValueOnce({ pages_processed: 1, total_pages: 5, status: 'PROCESSING' })
    .mockResolvedValueOnce({ pages_processed: 2, total_pages: 5, status: 'PENDING_REVIEW' });

  const onPendingReview = jest.fn();
  render(<ImportProgress jobId={10} onPendingReview={onPendingReview} />);

  expect(mockedService.getImportProgress).toHaveBeenCalledWith(10);
  await screen.findByText('Processando página 1 de 5');

  await jest.runOnlyPendingTimersAsync();
  await screen.findByText('Processando página 2 de 5');
  expect(onPendingReview).toHaveBeenCalled();
});
