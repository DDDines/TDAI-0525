import { fireEvent, render, screen, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import ProductTable from '../ProductTable.jsx';

jest.mock('../../../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
  },
}));

const produtos = [
  {
    id: 1,
    nome_base: 'Produto A',
    sku: 'SKU-A',
    fornecedor_id: 99,
    status_enriquecimento_web: { value: 'pipeline.CONCLUIDO_SUCESSO' },
    status_titulo_ia: 'EM_PROGRESSO',
    status_descricao_ia: 'FALHA',
    data_atualizacao: '2026-03-07T14:30:00',
  },
  {
    id: 2,
    nome_base: '',
    sku: '',
    fornecedor_id: null,
    status_enriquecimento_web: 'DESCONHECIDO',
    status_titulo_ia: 'NAO_INICIADO',
    status_descricao_ia: 'NAO_APLICAVEL',
    data_atualizacao: null,
  },
];

describe('ProductTable', () => {
  test('shows loading state when table is empty and loading', () => {
    render(
      <ProductTable
        produtos={[]}
        onEdit={() => {}}
        onSort={() => {}}
        onSelectProduto={() => {}}
        selectedProdutos={new Set()}
        onSelectAllProdutos={() => {}}
        loading={true}
      />
    );

    expect(screen.getByText('Carregando produtos...')).toBeInTheDocument();
    expect(screen.getByRole('checkbox')).toBeDisabled();
  });

  test('shows empty state when there are no products', () => {
    render(
      <ProductTable
        produtos={[]}
        onEdit={() => {}}
        onSort={() => {}}
        onSelectProduto={() => {}}
        selectedProdutos={new Set()}
        onSelectAllProdutos={() => {}}
      />
    );

    expect(screen.getByText('Nenhum produto encontrado.')).toBeInTheDocument();
  });

  test('renders rows, process chips and all row actions', () => {
    const onEdit = jest.fn();
    const onSort = jest.fn();
    const onViewContent = jest.fn();
    const onSelectProduto = jest.fn();
    const onSelectAllProdutos = jest.fn();

    render(
      <ProductTable
        produtos={produtos}
        onEdit={onEdit}
        onSort={onSort}
        sortConfig={{ key: 'nome_base', direction: 'ascending' }}
        onViewContent={onViewContent}
        onSelectProduto={onSelectProduto}
        selectedProdutos={new Set([1])}
        onSelectAllProdutos={onSelectAllProdutos}
        showAiColumns={true}
      />
    );

    expect(screen.getByText('Produto A')).toBeInTheDocument();
    expect(screen.getByText('SKU-A')).toBeInTheDocument();
    expect(screen.getByText('ID: 99')).toBeInTheDocument();
    expect(screen.getAllByText('Web')).toHaveLength(2);
    expect(screen.getAllByText('Tit')).toHaveLength(2);
    expect(screen.getAllByText('Desc')).toHaveLength(2);
    expect(screen.getByTitle('Concluido')).toBeInTheDocument();
    expect(screen.getByTitle('Falha')).toBeInTheDocument();
    expect(screen.getByTitle('Desconhecido')).toBeInTheDocument();
    expect(screen.getAllByText('--').length).toBeGreaterThan(1);
    expect(screen.getByText(/Nome Base \^/)).toBeInTheDocument();

    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes[0]).not.toBeChecked();
    expect(checkboxes[1]).toBeChecked();

    fireEvent.click(checkboxes[2]);
    expect(onSelectProduto).toHaveBeenCalledWith(2);

    fireEvent.click(screen.getAllByTitle('Ver conteúdo gerado')[0]);
    expect(onViewContent).toHaveBeenCalledWith(produtos[0]);

    fireEvent.doubleClick(screen.getByText('Produto A').closest('tr'));
    expect(onViewContent).toHaveBeenCalledWith(produtos[0]);

    fireEvent.click(screen.getAllByTitle('Editar produto')[0]);
    expect(onEdit).toHaveBeenCalledWith(produtos[0]);

    fireEvent.click(screen.getByText('ID'));
    fireEvent.click(screen.getByText(/Fornecedor/));
    expect(onSort).toHaveBeenCalledWith('id');
    expect(onSort).toHaveBeenCalledWith('fornecedor_id');
  });

  test('limits status summary to web process when AI columns are hidden', () => {
    render(
      <ProductTable
        produtos={[produtos[0]]}
        onEdit={() => {}}
        onSort={() => {}}
        onSelectProduto={() => {}}
        selectedProdutos={new Set()}
        onSelectAllProdutos={() => {}}
        showAiColumns={false}
      />
    );

    const row = screen.getByText('Produto A').closest('tr');
    expect(within(row).getByText('Web')).toBeInTheDocument();
    expect(within(row).queryByText('Tit')).not.toBeInTheDocument();
    expect(within(row).queryByText('Desc')).not.toBeInTheDocument();
    expect(screen.queryByTitle('Ver conteúdo gerado')).not.toBeInTheDocument();
  });

  test('uses the header checkbox to clear the current selection when all products are selected', () => {
    const onSelectAllProdutos = jest.fn();

    render(
      <ProductTable
        produtos={produtos}
        onEdit={() => {}}
        onSort={() => {}}
        onSelectProduto={() => {}}
        selectedProdutos={new Set([1, 2])}
        onSelectAllProdutos={onSelectAllProdutos}
      />
    );

    const headerCheckbox = screen.getAllByRole('checkbox')[0];
    expect(headerCheckbox).toBeChecked();

    fireEvent.click(headerCheckbox);

    expect(onSelectAllProdutos).toHaveBeenCalledWith(false);
  });

  test('renders sort indicators for SKU, status and update date columns', () => {
    const onSort = jest.fn();
    const { rerender } = render(
      <ProductTable
        produtos={produtos}
        onEdit={() => {}}
        onSort={onSort}
        onSelectProduto={() => {}}
        selectedProdutos={new Set()}
        onSelectAllProdutos={() => {}}
        sortConfig={{ key: 'sku', direction: 'descending' }}
      />
    );

    expect(screen.getByText(/SKU v/)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/SKU v/));

    rerender(
      <ProductTable
        produtos={produtos}
        onEdit={() => {}}
        onSort={onSort}
        onSelectProduto={() => {}}
        selectedProdutos={new Set()}
        onSelectAllProdutos={() => {}}
        sortConfig={{ key: 'status_enriquecimento_web', direction: 'ascending' }}
      />
    );

    expect(screen.getByText(/Status \^/)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Status \^/));

    rerender(
      <ProductTable
        produtos={produtos}
        onEdit={() => {}}
        onSort={onSort}
        onSelectProduto={() => {}}
        selectedProdutos={new Set()}
        onSelectAllProdutos={() => {}}
        sortConfig={{ key: 'data_atualizacao', direction: 'descending' }}
      />
    );

    expect(screen.getByText(/Atualizado Em v/)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Atualizado Em v/));
    expect(onSort).toHaveBeenNthCalledWith(1, 'sku');
    expect(onSort).toHaveBeenNthCalledWith(2, 'status_enriquecimento_web');
    expect(onSort).toHaveBeenNthCalledWith(3, 'data_atualizacao');
  });
});
