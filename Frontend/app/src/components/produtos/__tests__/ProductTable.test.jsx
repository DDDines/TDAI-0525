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
    log_enriquecimento_web: {
      historico_mensagens: ['Busca realizada com sucesso.'],
    },
    log_processamento: [
      {
        action: 'IA Descricao: Falha (422) - Template invalido para o produto.',
      },
    ],
    data_atualizacao: '2026-03-07T14:30:00',
  },
  {
    id: 2,
    nome_base: '',
    sku: '',
    fornecedor_id: null,
    status_enriquecimento_web: 'FALHA_API_EXTERNA',
    status_titulo_ia: 'NAO_INICIADO',
    status_descricao_ia: 'NAO_APLICAVEL',
    log_enriquecimento_web: {
      historico_mensagens: ['Falha ao consultar fonte do fornecedor: timeout da API externa.'],
    },
    log_processamento: [],
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
    expect(screen.getByLabelText(/Selecionar pagina atual/i)).toBeDisabled();
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

  test('treats malformed collections as empty and keeps the header checkbox disabled', () => {
    render(
      <ProductTable
        produtos={null}
        onEdit={() => {}}
        onSort={() => {}}
        onSelectProduto={() => {}}
        selectedProdutos={[]}
        onSelectAllProdutos={() => {}}
      />
    );

    expect(screen.getByText('Nenhum produto encontrado.')).toBeInTheDocument();
    expect(screen.getByLabelText(/Selecionar pagina atual/i)).toBeDisabled();
  });

  test('falls back to unknown when status objects do not expose a value field', () => {
    render(
      <ProductTable
        produtos={[
          {
            ...produtos[0],
            id: 3,
            nome_base: 'Produto C',
            status_enriquecimento_web: { value: null },
          },
        ]}
        onEdit={() => {}}
        onSort={() => {}}
        onSelectProduto={() => {}}
        selectedProdutos={new Set()}
        onSelectAllProdutos={() => {}}
      />
    );

    expect(screen.getByLabelText(/Enriquecimento web: Desconhecido/i)).toBeInTheDocument();
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
    expect(screen.queryByText('Web')).not.toBeInTheDocument();
    expect(screen.queryByText('Tit')).not.toBeInTheDocument();
    expect(screen.queryByText('Desc')).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Enriquecimento web: Concluido/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Descricao: Falha\. Template invalido para o produto/i)).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Enriquecimento web: Falha de API externa\. Tempo limite excedido ao consultar a fonte/i)
    ).toBeInTheDocument();
    expect(screen.getAllByText('--').length).toBeGreaterThan(1);
    expect(screen.getByRole('columnheader', { name: 'Nome Base' })).toHaveAttribute(
      'data-sort-direction',
      'ascending'
    );

    expect(screen.getByLabelText(/Selecionar pagina atual/i)).not.toBeChecked();
    const rowCheckboxes = screen.getAllByRole('checkbox', { hidden: false }).filter((checkbox) =>
      checkbox.getAttribute('aria-label') !== 'Selecionar pagina atual'
    );
    expect(rowCheckboxes[0]).toBeChecked();

    fireEvent.click(rowCheckboxes[1]);
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
    expect(within(row).getByLabelText(/Enriquecimento web: Concluido/i)).toBeInTheDocument();
    expect(within(row).queryByLabelText(/Titulos:/i)).not.toBeInTheDocument();
    expect(within(row).queryByLabelText(/Descricao:/i)).not.toBeInTheDocument();
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

    const headerCheckbox = screen.getByLabelText(/Selecionar pagina atual/i);
    expect(headerCheckbox).toBeChecked();

    fireEvent.click(headerCheckbox);

    expect(onSelectAllProdutos).toHaveBeenCalledWith(false);
  });

  test('renders only the page selection checkbox in the table header', () => {
    render(
      <ProductTable
        produtos={produtos}
        onEdit={() => {}}
        onSort={() => {}}
        onSelectProduto={() => {}}
        selectedProdutos={new Set()}
        onSelectAllProdutos={() => {}}
      />
    );

    expect(screen.getByLabelText(/Selecionar pagina atual/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Selecionar todos os resultados/i)).not.toBeInTheDocument();
  });

  test('renders a compact selection menu when selection actions are provided', () => {
    const handleSelectPage = jest.fn();
    const handleSelectAll = jest.fn();

    render(
      <ProductTable
        produtos={produtos}
        onEdit={() => {}}
        onSort={() => {}}
        onSelectProduto={() => {}}
        selectedProdutos={new Set()}
        onSelectAllProdutos={() => {}}
        selectionMenuItems={[
          { key: 'page', label: 'Selecionar pagina atual', onClick: handleSelectPage },
          { key: 'all', label: 'Selecionar todos os resultados da pesquisa', onClick: handleSelectAll },
        ]}
      />
    );

    fireEvent.click(screen.getByLabelText(/Opcoes de selecao/i));

    fireEvent.click(screen.getByRole('menuitem', { name: 'Selecionar todos os resultados da pesquisa' }));

    expect(handleSelectAll).toHaveBeenCalledTimes(1);
    expect(handleSelectPage).not.toHaveBeenCalled();
    expect(screen.queryByRole('menuitem', { name: 'Selecionar pagina atual' })).not.toBeInTheDocument();
  });

  test('sanitizes tracebacks and internal backend details from failure tooltips', () => {
    render(
      <ProductTable
        produtos={[
          {
            ...produtos[0],
            id: 99,
            nome_base: 'Produto com erro interno',
            status_enriquecimento_web: 'FALHOU',
            log_enriquecimento_web: {
              historico_mensagens: [
                "Enriquecimento web: Falhou. ERRO CRITICO INESPERADO NO PROCESSO: WebDataExtractorOrchestratorService.buscar_urls_google() got an unexpected keyword argument 'api_key'. Trace: Traceback (most recent call last): File \"C:/Users/Julio/Desktop/TDAI 2025/Project/Backend/application/services/web_enrichment_task_service.py\", line 1367",
              ],
            },
          },
        ]}
        onEdit={() => {}}
        onSort={() => {}}
        onSelectProduto={() => {}}
        selectedProdutos={new Set()}
        onSelectAllProdutos={() => {}}
      />
    );

    const indicator = screen.getByLabelText(
      /Enriquecimento web: Falhou\. Falha interna na integracao de busca Google\./i
    );
    expect(indicator).toBeInTheDocument();
    expect(indicator).not.toHaveAttribute('aria-label', expect.stringMatching(/Traceback|web_enrichment_task_service\.py/i));
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

    const skuHeader = screen.getByRole('columnheader', { name: 'SKU' });
    expect(skuHeader).toHaveAttribute('data-sort-direction', 'descending');
    fireEvent.click(skuHeader);

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

    const statusHeader = screen.getByRole('columnheader', { name: 'Status' });
    expect(statusHeader).toHaveAttribute('data-sort-direction', 'ascending');
    fireEvent.click(statusHeader);

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

    const updatedAtHeader = screen.getByRole('columnheader', { name: 'Atualizado Em' });
    expect(updatedAtHeader).toHaveAttribute('data-sort-direction', 'descending');
    fireEvent.click(updatedAtHeader);
    expect(onSort).toHaveBeenNthCalledWith(1, 'sku');
    expect(onSort).toHaveBeenNthCalledWith(2, 'status_enriquecimento_web');
    expect(onSort).toHaveBeenNthCalledWith(3, 'data_atualizacao');
  });
});
