import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import PaginationControls from '../PaginationControls.jsx';

test('shows current page information', () => {
  render(<PaginationControls currentPage={0} totalPages={3} onPageChange={() => {}} isLoading={false} />);
  expect(screen.getByText(/Página 1 de 3/)).toBeInTheDocument();
});

test('renders items per page selector and total items when props provided', () => {
  render(
    <PaginationControls
      currentPage={0}
      totalPages={1}
      onPageChange={() => {}}
      isLoading={false}
      itemsPerPage={10}
      onItemsPerPageChange={() => {}}
      totalItems={25}
    />
  );
  expect(screen.getByText(/25 itens/)).toBeInTheDocument();
  expect(screen.getByDisplayValue('10/página')).toBeInTheDocument();
});
