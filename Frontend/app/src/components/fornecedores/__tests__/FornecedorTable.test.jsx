import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import FornecedorTable from '../FornecedorTable.jsx';

jest.mock('../../common/LoadingPopup.jsx', () => ({
  __esModule: true,
  default: ({ message }) => <div>{message}</div>,
}));

describe('FornecedorTable', () => {
  const onRowClick = jest.fn();
  const onSelectRow = jest.fn();
  const onSelectAllRows = jest.fn();

  const fornecedores = [
    {
      id: 1,
      nome: 'Fornecedor 1',
      site_url: 'https://fornecedor-1.example',
      created_at: '2026-01-10T00:00:00Z',
    },
    {
      id: 2,
      nome: 'Fornecedor 2',
      site_url: null,
      created_at: '2026-01-11T00:00:00Z',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('shows the loading state before the first page arrives', () => {
    render(
      <FornecedorTable
        fornecedores={[]}
        onRowClick={onRowClick}
        onSelectRow={onSelectRow}
        selectedIds={[]}
        onSelectAllRows={onSelectAllRows}
        isLoading={true}
      />
    );

    expect(
      screen.getByText(/Carregando tabela de fornecedores/i)
    ).toBeInTheDocument();
  });

  test('shows the empty state and keeps the select-all checkbox disabled', () => {
    render(
      <FornecedorTable
        fornecedores={[]}
        onRowClick={onRowClick}
        onSelectRow={onSelectRow}
        selectedIds={[]}
        onSelectAllRows={onSelectAllRows}
        isLoading={false}
      />
    );

    expect(screen.getByText(/Nenhum fornecedor encontrado/i)).toBeInTheDocument();
    expect(screen.getByRole('checkbox')).toBeDisabled();
  });

  test('supports row selection, select-all and isolates row click from link/checkbox clicks', async () => {
    const user = userEvent.setup();
    render(
      <FornecedorTable
        fornecedores={fornecedores}
        onRowClick={onRowClick}
        onSelectRow={onSelectRow}
        selectedIds={[1, 2]}
        onSelectAllRows={onSelectAllRows}
        isLoading={false}
      />
    );

    const [selectAll, firstRowCheckbox, secondRowCheckbox] = screen.getAllByRole('checkbox');
    expect(selectAll).toBeChecked();

    await user.click(selectAll);
    expect(onSelectAllRows).toHaveBeenCalledTimes(1);

    await user.click(firstRowCheckbox);
    expect(onSelectRow).toHaveBeenCalledWith(1);
    expect(onRowClick).not.toHaveBeenCalled();

    await user.click(firstRowCheckbox.closest('td'));
    expect(onRowClick).not.toHaveBeenCalled();

    await user.click(screen.getByRole('link', { name: /https:\/\/fornecedor-1\.example/i }));
    expect(onRowClick).not.toHaveBeenCalled();

    await user.click(screen.getByText('Fornecedor 2'));
    expect(onRowClick).toHaveBeenCalledWith(expect.objectContaining({ id: 2 }));

    expect(secondRowCheckbox).toBeChecked();
  });
});
