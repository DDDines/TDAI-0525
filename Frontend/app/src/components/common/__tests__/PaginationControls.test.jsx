import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import PaginationControls from '../PaginationControls.jsx';

test('returns null when there is only one page and no page-size selector', () => {
  const { container } = render(
    <PaginationControls currentPage={0} totalPages={1} onPageChange={() => {}} isLoading={false} />
  );

  expect(container).toBeEmptyDOMElement();
});

test('shows current page information', () => {
  render(<PaginationControls currentPage={0} totalPages={3} onPageChange={() => {}} isLoading={false} />);
  expect(
    screen.getByText((_, element) => element?.textContent === 'Página 1 de 3')
  ).toBeInTheDocument();
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

test('navigates between pages only when movement is allowed', () => {
  const onPageChange = jest.fn();

  render(
    <PaginationControls currentPage={1} totalPages={3} onPageChange={onPageChange} isLoading={false} />
  );

  fireEvent.click(screen.getByRole('button', { name: /Anterior/i }));
  fireEvent.click(screen.getByRole('button', { name: /Próxima/i }));

  expect(onPageChange).toHaveBeenNthCalledWith(1, 0);
  expect(onPageChange).toHaveBeenNthCalledWith(2, 2);
});

test('disables navigation at boundaries or while loading', () => {
  const onPageChange = jest.fn();
  const { rerender } = render(
    <PaginationControls currentPage={0} totalPages={3} onPageChange={onPageChange} isLoading={false} />
  );

  expect(screen.getByRole('button', { name: /Anterior/i })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: /Anterior/i }));
  expect(onPageChange).not.toHaveBeenCalled();

  rerender(
    <PaginationControls currentPage={2} totalPages={3} onPageChange={onPageChange} isLoading={true} />
  );

  expect(screen.getByRole('button', { name: /Anterior/i })).toBeDisabled();
  expect(screen.getByRole('button', { name: /Próxima/i })).toBeDisabled();
});

test('emits page-size changes using the component payload', () => {
  const onItemsPerPageChange = jest.fn();

  render(
    <PaginationControls
      currentPage={0}
      totalPages={5}
      onPageChange={() => {}}
      isLoading={false}
      itemsPerPage={10}
      onItemsPerPageChange={onItemsPerPageChange}
    />
  );

  fireEvent.change(screen.getByRole('combobox'), { target: { value: '25' } });

  expect(onItemsPerPageChange).toHaveBeenCalledWith('25');
});
