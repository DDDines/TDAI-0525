import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
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
      <button onClick={() => onSelectAllRows({ target: { checked: true } })}>select-all</button>
      <button onClick={() => onSelectAllRows({ target: { checked: false } })}>clear-all</button>
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
  total_items: 2,
};

describe('FornecedoresPage', () => {
  let consoleErrorSpy;
  let consoleWarnSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    fornecedorService.getFornecedores.mockResolvedValue(fornecedoresPayload);
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
    render(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument();
    });
    expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
      'Fornecedor A,Fornecedor B'
    );

    fireEvent.change(screen.getByPlaceholderText('Nome do fornecedor...'), {
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
    render(<FornecedoresPage />);

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

    render(<FornecedoresPage />);

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao buscar fornecedores.');
    });

    fireEvent.change(screen.getByPlaceholderText('Nome do fornecedor...'), {
      target: { value: 'recarregar' },
    });

    await screen.findByTestId('fornecedor-table-names');
    fireEvent.click(screen.getByText('toggle-first'));
    fireEvent.click(screen.getByText('Deletar Selecionado(s)'));

    await waitFor(() => {
      expect(fornecedorService.deleteFornecedor).toHaveBeenCalledWith(1);
    });

    expect(showSuccessToast).toHaveBeenCalledWith('1 fornecedor(es) deletado(s) com sucesso!');
    expect(window.confirm).toHaveBeenCalledWith(
      'Tem certeza que deseja deletar 1 fornecedor(es) selecionado(s)?'
    );
    expect(showWarningToast).not.toHaveBeenCalled();
  });

  test('uses the generic fetch error fallback and avoids success toasts when every deletion fails', async () => {
    fornecedorService.getFornecedores.mockRejectedValueOnce({});
    fornecedorService.deleteFornecedor.mockRejectedValue(new Error('falha delete'));

    render(<FornecedoresPage />);

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao buscar fornecedores.');
    });

    fornecedorService.getFornecedores.mockResolvedValueOnce(fornecedoresPayload);
    fireEvent.change(screen.getByPlaceholderText('Nome do fornecedor...'), {
      target: { value: 'recarregar' },
    });

    await screen.findByTestId('fornecedor-table-names');
    fireEvent.click(screen.getByText('toggle-first'));
    fireEvent.click(screen.getByText('Deletar Selecionado(s)'));

    await waitFor(() => {
      expect(fornecedorService.deleteFornecedor).toHaveBeenCalledWith(1);
    });

    expect(showSuccessToast).not.toHaveBeenCalledWith('1 fornecedor(es) deletado(s) com sucesso!');
    expect(showErrorToast).toHaveBeenCalledWith(
      expect.stringMatching(/Alguns fornecedores.*puderam ser deletados/i)
    );
  });

  test('warns when trying to delete without a selection', async () => {
    render(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });
    const deleteButton = screen.getByRole('button', { name: /Deletar Selecionado/i });
    expect(deleteButton).toBeDisabled();
    expect(showWarningToast).not.toHaveBeenCalled();
  });

  test('formats create and update errors from backend detail payloads', async () => {
    fornecedorService.createFornecedor.mockRejectedValueOnce({
      detail: [{ loc: ['body', 'nome'], msg: 'obrigatorio' }],
    });
    fornecedorService.updateFornecedor.mockRejectedValueOnce({
      message: 'falha na atualizacao',
    });

    render(<FornecedoresPage />);

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

    render(<FornecedoresPage />);

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

    render(<FornecedoresPage />);

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
    fireEvent.click(screen.getByText('Deletar Selecionado(s)'));

    await waitFor(() => {
      expect(fornecedorService.deleteFornecedor).toHaveBeenCalledTimes(2);
    });
    expect(showSuccessToast).toHaveBeenCalledWith('1 fornecedor(es) deletado(s) com sucesso!');
    expect(showErrorToast).toHaveBeenCalledWith(
      'Alguns fornecedores não puderam ser deletados. Verifique o console.'
    );
  });

  test('handles pagination and unexpected payload formats', async () => {
    fornecedorService.getFornecedores.mockImplementation(({ skip }) =>
      Promise.resolve(skip === 10 ? { invalid: true } : { items: [], total_items: 11 })
    );

    render(<FornecedoresPage />);

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
    render(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });

    fireEvent.click(screen.getByText('select-all'));
    expect(screen.getByTestId('selected-ids')).toHaveTextContent('1,2');

    fireEvent.click(screen.getByText('clear-all'));
    expect(screen.getByTestId('selected-ids')).toHaveTextContent('');

    fireEvent.click(screen.getByText('toggle-first'));
    window.confirm = jest.fn(() => false);
    fireEvent.click(screen.getByText('Deletar Selecionado(s)'));

    expect(fornecedorService.deleteFornecedor).not.toHaveBeenCalled();
  });

  test('closes new and edit modals through page callbacks', async () => {
    render(<FornecedoresPage />);

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

    render(<FornecedoresPage />);

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

    render(<FornecedoresPage />);

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

    render(<FornecedoresPage />);

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
    render(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
        'Fornecedor A,Fornecedor B'
      );
    });

    fireEvent.change(screen.getByPlaceholderText('Nome do fornecedor...'), {
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

    render(<FornecedoresPage />);

    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('toggle-first'));
    fireEvent.click(screen.getByText('Deletar Selecionado(s)'));

    await waitFor(() => {
      expect(showSuccessToast).toHaveBeenCalledWith('1 fornecedor(es) deletado(s) com sucesso!');
    });
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent('');
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

    render(<FornecedoresPage />);

    fireEvent.click(await screen.findByText('next-page'));

    await waitFor(() => {
      expect(fornecedorService.getFornecedores).toHaveBeenLastCalledWith({
        skip: 10,
        limit: 10,
        termo_busca: undefined,
      });
    });
    expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent('Fornecedor Z');

    fireEvent.click(screen.getByText('toggle-first'));
    fireEvent.click(screen.getByText('Deletar Selecionado(s)'));

    await waitFor(() => {
      expect(fornecedorService.deleteFornecedor).toHaveBeenCalledWith(11);
    });
    await waitFor(() => {
      expect(fornecedorService.getFornecedores).toHaveBeenLastCalledWith({
        skip: 0,
        limit: 10,
        termo_busca: undefined,
      });
    });
    expect(screen.getByTestId('fornecedor-table-names')).toHaveTextContent(
      'Fornecedor A,Fornecedor B'
    );
  });
});
