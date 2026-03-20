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
  const selectionMenuItems = [
    {
      key: 'page',
      label: 'Selecionar pagina atual',
      onClick: jest.fn(),
      disabled: false,
    },
    {
      key: 'all',
      label: 'Selecionar todos os resultados da pesquisa',
      onClick: jest.fn(),
      disabled: false,
    },
    {
      key: 'clear',
      label: 'Limpar selecao',
      onClick: jest.fn(),
      disabled: false,
    },
  ];

  const fornecedores = [
    {
      id: 1,
      nome: 'Fornecedor 1',
      site_url: 'https://fornecedor-1.example',
      logo_url: 'https://cdn.example.com/logo-1.png',
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
    selectionMenuItems.forEach((item) => item.onClick.mockClear());
  });

  test('shows the loading state before the first page arrives', () => {
    render(
      <FornecedorTable
        fornecedores={[]}
        onRowClick={onRowClick}
        onSelectRow={onSelectRow}
        selectedIds={[]}
        onSelectAllRows={onSelectAllRows}
        selectionMenuItems={selectionMenuItems}
        isLoading={true}
      />
    );

    expect(screen.getByText(/Carregando fornecedores/i)).toBeInTheDocument();
  });

  test('shows the empty state and keeps the select-all checkbox disabled', () => {
    render(
      <FornecedorTable
        fornecedores={[]}
        onRowClick={onRowClick}
        onSelectRow={onSelectRow}
        selectedIds={[]}
        onSelectAllRows={onSelectAllRows}
        selectionMenuItems={selectionMenuItems}
        isLoading={false}
      />
    );

    expect(screen.getByText(/Nenhum fornecedor encontrado/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Opcoes de selecao/i)).toBeDisabled();
  });

  test('supports row selection, selection menu and isolates row click from link/checkbox clicks', async () => {
    const user = userEvent.setup();
    render(
      <FornecedorTable
        fornecedores={fornecedores}
        onRowClick={onRowClick}
        onSelectRow={onSelectRow}
        selectedIds={[1, 2]}
        onSelectAllRows={onSelectAllRows}
        selectionMenuItems={selectionMenuItems}
        isLoading={false}
      />
    );

    const selectAll = screen.getByLabelText(/Opcoes de selecao/i);
    const rowCheckboxes = screen
      .getAllByRole('checkbox')
      .filter(
        (checkbox) =>
          checkbox.getAttribute('aria-label') !== 'Opcoes de selecao'
      );
    const [firstRowCheckbox, secondRowCheckbox] = rowCheckboxes;
    expect(screen.queryByRole('menuitem', { name: /Selecionar pagina atual/i })).not.toBeInTheDocument();

    await user.click(selectAll);
    expect(screen.getByRole('menuitem', { name: /Selecionar pagina atual/i })).toBeInTheDocument();

    await user.click(screen.getByRole('menuitem', { name: /Selecionar pagina atual/i }));
    expect(selectionMenuItems[0].onClick).toHaveBeenCalledTimes(1);

    await user.click(firstRowCheckbox);
    expect(onSelectRow).toHaveBeenCalledWith(1);
    expect(onRowClick).not.toHaveBeenCalled();

    await user.click(firstRowCheckbox.closest('td'));
    expect(onRowClick).not.toHaveBeenCalled();

    await user.click(screen.getByRole('link', { name: /fornecedor-1\.example/i }));
    expect(onRowClick).not.toHaveBeenCalled();

    await user.click(screen.getByText('Fornecedor 2'));
    expect(onRowClick).toHaveBeenCalledWith(expect.objectContaining({ id: 2 }));

    expect(secondRowCheckbox).toBeChecked();
    expect(screen.getByAltText(/Logo de Fornecedor 1/i)).toBeInTheDocument();
  });
});
