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
      <button onClick={() => onRowClick(fornecedores[0])}>edit-first</button>
      <button onClick={() => onSelectAllRows({ target: { checked: true } })}>select-all</button>
    </div>
  ),
}));

jest.mock('../../components/fornecedores/NewFornecedorModal', () => ({
  __esModule: true,
  default: ({ isOpen, onSave }) => (
    <div data-testid="new-modal-state" data-open={String(isOpen)}>
      <button onClick={() => onSave({ nome: 'Novo Fornecedor' })}>save-new-fornecedor</button>
    </div>
  ),
}));

jest.mock('../../components/fornecedores/EditFornecedorModal', () => ({
  __esModule: true,
  default: ({ isOpen, fornecedorData, onSave }) => (
    <div data-testid="edit-modal-state" data-open={String(isOpen)}>
      <button onClick={() => onSave(fornecedorData?.id, { nome: 'Fornecedor Editado' })}>
        save-edit-fornecedor
      </button>
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
  beforeEach(() => {
    jest.clearAllMocks();
    fornecedorService.getFornecedores.mockResolvedValue(fornecedoresPayload);
    fornecedorService.createFornecedor.mockResolvedValue({ id: 3 });
    fornecedorService.updateFornecedor.mockResolvedValue({ id: 1 });
    fornecedorService.deleteFornecedor.mockResolvedValue({ ok: true });
    window.confirm = jest.fn(() => true);
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

    await screen.findByTestId('fornecedor-table-names');

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
});
