import { render, screen } from '@testing-library/react';
import PaginationControls from '../PaginationControls.jsx';

test('shows current page information', () => {
  render(<PaginationControls currentPage={0} totalPages={3} onPageChange={() => {}} isLoading={false} />);
  expect(screen.getByText(/Página 1 de 3/)).toBeInTheDocument();
});
