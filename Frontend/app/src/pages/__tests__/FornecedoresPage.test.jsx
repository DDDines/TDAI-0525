import React from 'react';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import { renderWithQueryClient } from '../../../test-utils/renderWithQueryClient.jsx';
import '@testing-library/jest-dom';
import FornecedoresPage from '../FornecedoresPage.jsx';
import fornecedorService from '../../services/fornecedorService';
import {
  showSuccessToast,
  showErrorToast,
  showWarningToast,
} from '../../utils/notifications';

jest.mock('../../services/fornecedorService', () => ({
  __esModule: true,
  default: {
    getFornecedores: jest.fn(),
    getFornecedoresIds: jest.fn(),
    createFornecedor: jest.fn(),
    updateFornecedor: jest.fn(),
    deleteFornecedor: jest.fn(),
  },
}));

jest.mock('../../utils/notifications', () => ({
  showSuccessToast: jest.fn(),
  showErrorToast: jest.fn(),
  showWarningToast: jest.fn(),
}));

jest.mock('../../components/fornecedores/FornecedorTable', () => ({
  __esModule: true,
  default: ({
    fornecedores,
    onSelectRow,
    onSelectAllRows,
    onRowClick,
    selectedIds,
  }) => (
    <div>
      <div data-testid="fornecedor-table-names">
        {fornecedores.map((item) => item.nome).join(',')}
      </div>
      <div data-testid="selected-ids">{selectedIds.join(',')}</div>
      <button onClick={() => onSelectRow(fornecedores[0]?.id)}>toggle-first</button>
      <button onClick={() => onSelectRow(fornecedores[1]?.id)}>toggle-second</button>
      <button onClick={() => onRowClick(fornecedores[0])}>edit-first</button>
      <label htmlFor="mock-select-page-fornecedores">Selecionar pagina atual</label>
      <input
        id="mock-select-page-fornecedores"
        type="checkbox"
        aria-label="Selecionar pagina atual"
        checked={selectedIds.length === fornecedores.length && fornecedores.length > 0}
        onChange={(event) => onSelectAllRows(event.target.checked)}
      />
    </div>
  ),
}));

jest.mock('../../components/fornecedores/NewFornecedorModal', () => ({
  __esModule: true,
  default: ({ isOpen, onSave, onClose }) => (
    <div data-testid="new-modal-state" data-open={String(isOpen)}>
      <button
        onClick={() => {
          Promise.resolve(onSave({ nome: 'Novo Fornecedor' })).catch(() => {});
        }}
      >
        save-new-fornecedor
      </button>
      <button onClick={() => onClose?.()}>close-new-fornecedor</button>
    </div>
  ),
}));

jest.mock('../../components/fornecedores/EditFornecedorModal', () => ({
  __esModule: true,
  default: ({ isOpen, fornecedorData, onSave, onClose }) => (
    <div data-testid="edit-modal-state" data-open={String(isOpen)}>
      <button
        onClick={() => {
          Promise.resolve(
            onSave(fornecedorData?.id, { nome: 'Fornecedor Editado' })
          ).catch(() => {});
        }}
      >
        save-edit-fornecedor
      </button>
      <button onClick={() => onClose?.()}>close-edit-fornecedor</button>
    </div>
  ),
}));

jest.mock('../../components/common/PaginationControls', () => ({
  __esModule: true,
  default: ({ onPageChange }) => (
    <button onClick={() => onPageChange(1)}>next-page</button>
  ),
}));

const fornecedoresPayload = {
  items: [
    { id: 1, nome: 'Fornecedor A', site_url: 'https://a.example', created_at: '2026-03-07' },
    { id: 2, nome: 'Fornecedor B', site_url: 'https://b.example', created_at: '2026-03-07' },
  ],
  total_items: 3,
};

describe('FornecedoresPage', () => {
  let consoleErrorSpy;
  let consoleWarnSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    fornecedorService.getFornecedores.mockResolvedValue(fornecedoresPayload);
    fornecedorService.getFornecedoresIds.mockResolvedValue({ ids: [1, 2] });
    fornecedorService.createFornecedor.mockResolvedValue({ id: 3 });
    fornecedorService.updateFornecedor.mockResolvedValue({ id: 1 });
    fornecedorService.deleteFornecedor.mockResolvedValue({ ok: true });
    window.confirm = jest.fn(() => true);
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();
  });

  test('loads suppliers, shows the total and refetches when search changes', async () => {
    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByText('Na base')).toBeInTheDocument();
    });
    expect(screen.getByText(/Buscar fornecedores/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Novo Fornecedor/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });

    fireEvent.change(screen.getByPlaceholderText('Nome do fornecedor ou dominio do site...'), {
      target: { value: 'Fornecedor A' },
    });

    await waitFor(() => {
      expect(fornecedorService.getFornecedores).toHaveBeenLastCalledWith({
        skip: 0,
        limit: 10,
        termo_busca: 'Fornecedor A',
      });
    });
  });

  test('creates and updates a supplier through the page handlers', async () => {
    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });

    fireEvent.click(screen.getByText('Novo Fornecedor'));
    fireEvent.click(screen.getByText('save-new-fornecedor'));

    await waitFor(() => {
      expect(fornecedorService.createFornecedor).toHaveBeenCalledWith({
        nome: 'Novo Fornecedor',
      });
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Fornecedor criado com sucesso!');

    fireEvent.click(screen.getByText('edit-first'));
    fireEvent.click(screen.getByText('save-edit-fornecedor'));

    await waitFor(() => {
      expect(fornecedorService.updateFornecedor).toHaveBeenCalledWith(1, {
        nome: 'Fornecedor Editado',
      });
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Fornecedor atualizado com sucesso!');
  });

  test('deletes selected suppliers and warns on fetch failure', async () => {
    fornecedorService.getFornecedores
      .mockRejectedValueOnce(new Error('Falha ao buscar fornecedores.'))
      .mockResolvedValue(fornecedoresPayload);

    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao buscar fornecedores.');
    });

    fireEvent.change(screen.getByPlaceholderText('Nome do fornecedor ou dominio do site...'), {
      target: { value: 'recarregar' },
    });

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });
    fireEvent.click(screen.getByText('toggle-first'));
    await waitFor(() => {
      expect(screen.getByTestId('selected-ids')).toHaveTextContent('1');
    });
    fireEvent.click(screen.getByText(/Deletar selecionado\(s\)/i));

    await waitFor(() => {
      expect(fornecedorService.deleteFornecedor).toHaveBeenCalledWith(1);
    });

    expect(showSuccessToast).not.toHaveBeenCalledWith('1 fornecedor(es) deletado(s) com sucesso!');
    expect(window.confirm).toHaveBeenCalledWith(
      'Tem certeza que deseja deletar 1 fornecedor(es) selecionado(s)?'
    );
    expect(showWarningToast).not.toHaveBeenCalled();
  });

  test('uses the generic fetch error fallback and avoids success toasts when every deletion fails', async () => {
    fornecedorService.getFornecedores.mockRejectedValueOnce({});
    fornecedorService.deleteFornecedor.mockRejectedValue(new Error('falha delete'));

    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao buscar fornecedores.');
    });

    fornecedorService.getFornecedores.mockResolvedValueOnce(fornecedoresPayload);
    fireEvent.change(screen.getByPlaceholderText('Nome do fornecedor ou dominio do site...'), {
      target: { value: 'recarregar' },
    });

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });
    fireEvent.click(screen.getByText('toggle-first'));
    await waitFor(() => {
      expect(screen.getByTestId('selected-ids')).toHaveTextContent('1');
    });
    fireEvent.click(screen.getByText(/Deletar selecionado\(s\)/i));

    await waitFor(() => {
      expect(fornecedorService.deleteFornecedor).toHaveBeenCalledWith(1);
    });

    expect(showSuccessToast).not.toHaveBeenCalledWith('1 fornecedor(es) deletado(s) com sucesso!');
    expect(showErrorToast).toHaveBeenCalledWith(
      expect.stringMatching(/Alguns fornecedores.*puderam ser deletados/i)
    );
  });

  test('warns when trying to delete without a selection', async () => {
    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });
    expect(screen.queryByRole('button', { name: /Deletar selecionado/i })).not.toBeInTheDocument();
    expect(showWarningToast).not.toHaveBeenCalled();
  });

  test('supports selecting the current page and all filtered supplier results', async () => {
    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });

    fireEvent.click(screen.getByLabelText(/Selecionar pagina atual/i));
    expect(screen.getByTestId('selected-ids')).toHaveTextContent('1,2');
    expect(
      screen.getByText('2 fornecedor(es) selecionado(s) na pagina atual.')
    ).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('Nome do fornecedor ou dominio do site...'), {
      target: { value: 'Fornecedor' },
    });
    await waitFor(() => {
      expect(fornecedorService.getFornecedores).toHaveBeenLastCalledWith({
        skip: 0,
        limit: 10,
        termo_busca: 'Fornecedor',
      });
    });
    expect(screen.queryByText(/na pagina atual/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText(/Selecionar pagina atual/i));
    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: 'Selecionar todos os 3 resultados' })
      ).toBeInTheDocument();
    });

    fornecedorService.getFornecedoresIds.mockResolvedValueOnce({ ids: [1, 2, 9] });
    fireEvent.click(screen.getByRole('button', { name: 'Selecionar todos os 3 resultados' }));

    await waitFor(() => {
      expect(fornecedorService.getFornecedoresIds).toHaveBeenCalledWith({
        termo_busca: 'Fornecedor',
      });
    });
    await waitFor(() => {
      expect(screen.getByTestId('selected-ids')).toHaveTextContent('1,2,9');
    });
    await waitFor(() => {
      expect(
        screen.getByText('3 fornecedor(es) selecionado(s) em todos os resultados filtrados.')
      ).toBeInTheDocument();
    });
    expect(showSuccessToast).not.toHaveBeenCalledWith(
      '3 fornecedor(es) selecionado(s) com os filtros atuais.'
    );
  });

  test('formats create and update errors from backend detail payloads', async () => {
    fornecedorService.createFornecedor.mockRejectedValueOnce({
      detail: [{ loc: ['body', 'nome'], msg: 'obrigatorio' }],
    });
    fornecedorService.updateFornecedor.mockRejectedValueOnce({
      message: 'falha na atualizacao',
    });

    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });
    fireEvent.click(screen.getByText('Novo Fornecedor'));
    fireEvent.click(screen.getByText('save-new-fornecedor'));
    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro ao criar fornecedor: body.nome: obrigatorio'
      );
    });

    fireEvent.click(screen.getByText('edit-first'));
    fireEvent.click(screen.getByText('save-edit-fornecedor'));
    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro ao atualizar fornecedor: falha na atualizacao'
      );
    });
  });

  test('formats update detail payloads and toggles row selection off', async () => {
    fornecedorService.updateFornecedor
      .mockRejectedValueOnce({ detail: 'site duplicado' })
      .mockRejectedValueOnce({ detail: [{ loc: ['body', 'site_url'], msg: 'invalido' }] });

    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });

    fireEvent.click(screen.getByText('toggle-first'));
    expect(screen.getByTestId('selected-ids')).toHaveTextContent('1');
    fireEvent.click(screen.getByText('toggle-first'));
    expect(screen.getByTestId('selected-ids')).toHaveTextContent('');

    fireEvent.click(screen.getByText('edit-first'));
    fireEvent.click(screen.getByText('save-edit-fornecedor'));
    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro ao atualizar fornecedor: site duplicado'
      );
    });

    fireEvent.click(screen.getByText('edit-first'));
    fireEvent.click(screen.getByText('save-edit-fornecedor'));
    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro ao atualizar fornecedor: body.site_url: invalido'
      );
    });
  });

  test('shows partial delete failure and refreshes remaining rows', async () => {
    fornecedorService.deleteFornecedor
      .mockResolvedValueOnce({ ok: true })
      .mockRejectedValueOnce(new Error('nao pode deletar'));

    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });
    fireEvent.click(screen.getByText('toggle-first'));
    fireEvent.click(screen.getByText('toggle-second'));
    await waitFor(() => {
      expect(screen.getByTestId('selected-ids')).toHaveTextContent('1,2');
    });
    fireEvent.click(screen.getByText(/Deletar selecionado\(s\)/i));

    await waitFor(() => {
      expect(fornecedorService.deleteFornecedor).toHaveBeenCalledTimes(2);
    });
    expect(showSuccessToast).not.toHaveBeenCalledWith('1 fornecedor(es) deletado(s) com sucesso!');
    expect(showErrorToast).toHaveBeenCalledWith(
      'Alguns fornecedores nao puderam ser deletados. Verifique o console.'
    );
  });

  test('handles pagination and unexpected payload formats', async () => {
    fornecedorService.getFornecedores.mockImplementation(({ skip }) =>
      Promise.resolve(skip === 10 ? { invalid: true } : { items: [], total_items: 11 })
    );

    renderWithQueryClient(<FornecedoresPage />);

    await screen.findByText('next-page');
    fireEvent.click(screen.getByText('next-page'));

    await waitFor(() => {
      expect(fornecedorService.getFornecedores).toHaveBeenLastCalledWith({
        skip: 10,
        limit: 10,
        termo_busca: undefined,
      });
    });
    expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent('');
  });

  test('supports select-all clearing and canceling deletion', async () => {
    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });

    fireEvent.click(screen.getByLabelText(/Selecionar pagina atual/i));
    expect(screen.getByTestId('selected-ids')).toHaveTextContent('1,2');

    fireEvent.click(screen.getByLabelText(/Selecionar pagina atual/i));
    expect(screen.getByTestId('selected-ids')).toHaveTextContent('');

    fireEvent.click(screen.getByText('toggle-first'));
    window.confirm = jest.fn(() => false);
    fireEvent.click(screen.getByText(/Deletar selecionado\(s\)/i));

    expect(fornecedorService.deleteFornecedor).not.toHaveBeenCalled();
  });

  test('clears supplier selection when changing pages', async () => {
    fornecedorService.getFornecedores.mockImplementation(({ skip }) =>
      Promise.resolve(
        skip === 10
          ? {
              items: [
                {
                  id: 11,
                  nome: 'Fornecedor Z',
                  site_url: 'https://z.example',
                  created_at: '2026-03-07',
                },
              ],
              total_items: 11,
            }
          : {
              items: fornecedoresPayload.items,
              total_items: 11,
            }
      )
    );

    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });
    fireEvent.click(screen.getByLabelText(/Selecionar pagina atual/i));
    expect(screen.getByTestId('selected-ids')).toHaveTextContent('1,2');

    fireEvent.click(screen.getByText('next-page'));

    await waitFor(() => {
      expect(fornecedorService.getFornecedores).toHaveBeenLastCalledWith({
        skip: 10,
        limit: 10,
        termo_busca: undefined,
      });
    });
    expect(screen.getByTestId('selected-ids')).toHaveTextContent('');
    expect(screen.queryByText(/fornecedor\(es\) selecionado\(s\)/i)).not.toBeInTheDocument();
  });

  test('closes new and edit modals through page callbacks', async () => {
    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });

    fireEvent.click(screen.getByText('Novo Fornecedor'));
    await waitFor(() => {
      expect(screen.getByTestId('new-modal-state')).toHaveAttribute('data-open', 'true');
    });
    fireEvent.click(screen.getByText('close-new-fornecedor'));
    await waitFor(() => {
      expect(screen.getByTestId('new-modal-state')).toHaveAttribute('data-open', 'false');
    });

    fireEvent.click(screen.getByText('edit-first'));
    await waitFor(() => {
      expect(screen.getByTestId('edit-modal-state')).toHaveAttribute('data-open', 'true');
    });
    fireEvent.click(screen.getByText('close-edit-fornecedor'));
    await waitFor(() => {
      expect(screen.getByTestId('edit-modal-state')).toHaveAttribute('data-open', 'false');
    });
  });

  test('formats string detail and raw string errors from backend payloads', async () => {
    fornecedorService.createFornecedor.mockRejectedValueOnce({
      detail: 'nome duplicado',
    });
    fornecedorService.updateFornecedor.mockRejectedValueOnce('timeout remoto');

    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });

    fireEvent.click(screen.getByText('Novo Fornecedor'));
    fireEvent.click(screen.getByText('save-new-fornecedor'));
    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro ao criar fornecedor: nome duplicado'
      );
    });

    fireEvent.click(screen.getByText('edit-first'));
    fireEvent.click(screen.getByText('save-edit-fornecedor'));
    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro ao atualizar fornecedor: timeout remoto'
      );
    });
  });

  test('formats object detail payloads from backend on create and update', async () => {
    fornecedorService.createFornecedor.mockRejectedValueOnce({
      detail: { campo: 'nome', motivo: 'duplicado' },
    });
    fornecedorService.updateFornecedor.mockRejectedValueOnce({
      detail: { campo: 'site_url', motivo: 'invalido' },
    });

    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });

    fireEvent.click(screen.getByText('Novo Fornecedor'));
    fireEvent.click(screen.getByText('save-new-fornecedor'));
    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro ao criar fornecedor: {"campo":"nome","motivo":"duplicado"}'
      );
    });

    fireEvent.click(screen.getByText('edit-first'));
    fireEvent.click(screen.getByText('save-edit-fornecedor'));
    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro ao atualizar fornecedor: {"campo":"site_url","motivo":"invalido"}'
      );
    });
  });

  test('formats create errors from message and raw string payloads', async () => {
    fornecedorService.createFornecedor.mockRejectedValueOnce({
      message: 'falha de conectividade',
    });

    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });

    fireEvent.click(screen.getByText('Novo Fornecedor'));
    fireEvent.click(screen.getByText('save-new-fornecedor'));
    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro ao criar fornecedor: falha de conectividade'
      );
    });

    fornecedorService.createFornecedor.mockRejectedValueOnce('timeout bruto');
    fireEvent.click(screen.getByText('Novo Fornecedor'));
    fireEvent.click(screen.getByText('save-new-fornecedor'));
    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro ao criar fornecedor: timeout bruto'
      );
    });
  });

  test('keeps the active search term when creating a supplier from filtered results', async () => {
    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });

    fireEvent.change(screen.getByPlaceholderText('Nome do fornecedor ou dominio do site...'), {
      target: { value: 'Filtro ativo' },
    });
    await waitFor(() => {
      expect(fornecedorService.getFornecedores).toHaveBeenLastCalledWith({
        skip: 0,
        limit: 10,
        termo_busca: 'Filtro ativo',
      });
    });

    fireEvent.click(screen.getByText('Novo Fornecedor'));
    fireEvent.click(screen.getByText('save-new-fornecedor'));

    await waitFor(() => {
      expect(fornecedorService.createFornecedor).toHaveBeenCalledWith({
        nome: 'Novo Fornecedor',
      });
    });
    await waitFor(() => {
      expect(fornecedorService.getFornecedores).toHaveBeenLastCalledWith({
        skip: 0,
        limit: 10,
        termo_busca: 'Filtro ativo',
      });
    });
  });

  test('resets the list state when deleting the last available supplier', async () => {
    fornecedorService.getFornecedores.mockResolvedValue({
      items: [{ id: 1, nome: 'Fornecedor A', site_url: 'https://a.example', created_at: '2026-03-07' }],
      total_items: 1,
    });

    renderWithQueryClient(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByText('Na base')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('toggle-first'));
    fireEvent.click(screen.getByText(/Deletar selecionado\(s\)/i));

    await waitFor(() => {
      expect(showSuccessToast).not.toHaveBeenCalledWith('1 fornecedor(es) deletado(s) com sucesso!');
    });
    expect(screen.getAllByText('0').length).toBeGreaterThan(0);
    expect(screen.getByTestId('selected-ids')).toBeEmptyDOMElement();
  });

  test('retorna para a pagina anterior quando a ultima pagina fica vazia apos delecao', async () => {
    fornecedorService.getFornecedores.mockImplementation(({ skip }) =>
      Promise.resolve(
        skip === 10
          ? {
              items: [
                {
                  id: 11,
                  nome: 'Fornecedor Z',
                  site_url: 'https://z.example',
                  created_at: '2026-03-07',
                },
              ],
              total_items: 11,
            }
          : {
              items: fornecedoresPayload.items,
              total_items: 11,
            }
      )
    );

    renderWithQueryClient(<FornecedoresPage />);

    fireEvent.click(await screen.findByText('next-page'));

    await waitFor(() => {
      expect(fornecedorService.getFornecedores).toHaveBeenLastCalledWith({
        skip: 10,
        limit: 10,
        termo_busca: undefined,
      });
    });
    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent('Fornecedor Z');
    });

    fireEvent.click(screen.getByText('toggle-first'));
    await waitFor(() => {
      expect(screen.getByTestId('selected-ids')).toHaveTextContent('11');
    });
    fireEvent.click(screen.getByText(/Deletar selecionado\(s\)/i));

    await waitFor(() => {
      expect(fornecedorService.deleteFornecedor).toHaveBeenCalledWith(11);
    });
    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });
    expect(fornecedorService.getFornecedores).toHaveBeenCalledWith({
      skip: 0,
      limit: 10,
      termo_busca: undefined,
    });
    expect(screen.getByTestId('selected-ids')).toHaveTextContent(
      ''
    );
  });
});





