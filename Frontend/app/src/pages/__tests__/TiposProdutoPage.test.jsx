import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import TiposProdutoPage from '../TiposProdutoPage.jsx';
import { useProductTypes } from '../../contexts/ProductTypeContext';
import productTypeService from '../../services/productTypeService';
import { showErrorToast, showSuccessToast } from '../../utils/notifications';

jest.mock('../../contexts/ProductTypeContext', () => ({
  useProductTypes: jest.fn(),
}));

jest.mock('../../services/productTypeService', () => ({
  __esModule: true,
  default: {
    deleteProductType: jest.fn(),
    addAttributeToType: jest.fn(),
    updateAttributeInType: jest.fn(),
    removeAttributeFromType: jest.fn(),
    reorderAttributeInType: jest.fn(),
  },
}));

jest.mock('../../utils/notifications', () => ({
  showSuccessToast: jest.fn(),
  showErrorToast: jest.fn(),
}));

jest.mock('../../components/product_types/EditProductTypeModal.jsx', () => ({
  __esModule: true,
  default: ({ isOpen, onSave, onClose }) =>
    isOpen ? (
      <div data-testid="edit-type-modal">
        <button
          onClick={() =>
            onSave({
              friendly_name: 'Tipo Editado',
              description: 'Descricao atualizada',
              key_name: 'pecas',
            })
          }
        >
          save-edit-type
        </button>
        <button onClick={onClose}>close-edit-type</button>
      </div>
    ) : null,
}));

jest.mock('../../components/product_types/NewProductTypeModal.jsx', () => ({
  __esModule: true,
  default: ({ isOpen, onCreated, onClose }) =>
    isOpen ? (
      <div data-testid="new-type-modal">
        <button
          onClick={() => {
            onCreated({ id: 99, friendly_name: 'Novo Tipo' });
            onClose();
          }}
        >
          complete-new-type
        </button>
      </div>
    ) : null,
}));

jest.mock('../../components/product_types/AttributeTemplateList', () => ({
  __esModule: true,
  default: ({ attributes = [], onEdit, onDelete, onReorder }) => (
    <div data-testid="attribute-list">
      <span>{attributes.map((attribute) => attribute.label).join(',')}</span>
      <button onClick={() => onEdit(attributes[0])}>edit-attribute</button>
      <button onClick={() => onDelete(attributes[0].id)}>delete-attribute</button>
      <button onClick={() => onReorder(attributes[0].id, 'up')}>reorder-attribute</button>
    </div>
  ),
}));

jest.mock('../../components/product_types/AttributeTemplateModal', () => ({
  __esModule: true,
  default: ({ isOpen, attribute, onSave, onClose }) =>
    isOpen ? (
      <div data-testid="attribute-modal">
        <button
          onClick={() =>
            onSave(
              attribute
                ? { label: 'Cor editada', field_type: 'text' }
                : { label: 'Peso', field_type: 'number' }
            )
          }
        >
          {attribute ? 'save-edit-attribute' : 'save-new-attribute'}
        </button>
        <button onClick={onClose}>close-attribute-modal</button>
      </div>
    ) : null,
}));

jest.mock('../../components/common/LoadingOverlay.jsx', () => ({
  __esModule: true,
  default: ({ message }) => <div>{message}</div>,
}));

describe('TiposProdutoPage', () => {
  const refreshProductTypes = jest.fn();
  const updateProductType = jest.fn();
  const baseProductTypes = [
    {
      id: 1,
      key_name: 'pecas',
      friendly_name: 'Pecas',
      attribute_templates: [
        {
          id: 11,
          label: 'Cor',
          attribute_key: 'cor',
          field_type: 'TEXT',
          display_order: 0,
        },
      ],
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
    window.confirm = jest.fn(() => true);
    useProductTypes.mockReturnValue({
      productTypes: baseProductTypes,
      isLoading: false,
      error: null,
      refreshProductTypes,
      updateProductType,
    });
    productTypeService.deleteProductType.mockResolvedValue({ ok: true });
    productTypeService.addAttributeToType.mockResolvedValue({ ok: true });
    productTypeService.updateAttributeInType.mockResolvedValue({ ok: true });
    productTypeService.removeAttributeFromType.mockResolvedValue({ ok: true });
    productTypeService.reorderAttributeInType.mockResolvedValue({ ok: true });
    updateProductType.mockResolvedValue({ ok: true });
  });

  test('renders loading and error states from the context', () => {
    useProductTypes
      .mockReturnValueOnce({
        productTypes: [],
        isLoading: true,
        error: null,
        refreshProductTypes,
        updateProductType,
      })
      .mockReturnValueOnce({
        productTypes: [],
        isLoading: false,
        error: 'erro interno',
        refreshProductTypes,
        updateProductType,
      });

    const { rerender } = render(<TiposProdutoPage />);
    expect(screen.getByText('Carregando tipos de produto...')).toBeInTheDocument();

    rerender(<TiposProdutoPage />);
    expect(screen.getByText(/Erro ao carregar tipos de produto/)).toBeInTheDocument();
  });

  test('creates and updates product types through the page handlers', async () => {
    render(<TiposProdutoPage />);

    fireEvent.click(screen.getByText('+ Novo Tipo de Produto'));
    expect(screen.getByTestId('new-type-modal')).toBeInTheDocument();
    fireEvent.click(screen.getByText('complete-new-type'));

    expect(refreshProductTypes).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTitle('Editar tipo'));
    expect(screen.getByTestId('edit-type-modal')).toBeInTheDocument();
    fireEvent.click(screen.getByText('save-edit-type'));

    await waitFor(() => {
      expect(updateProductType).toHaveBeenCalledWith(1, {
        friendly_name: 'Tipo Editado',
        description: 'Descricao atualizada',
        key_name: 'pecas',
      });
    });
    expect(refreshProductTypes).toHaveBeenCalledTimes(2);
  });

  test('deletes product types and manages attributes for the selected type', async () => {
    render(<TiposProdutoPage />);

    fireEvent.click(screen.getByText('Pecas'));
    expect(screen.getByTestId('attribute-list')).toBeInTheDocument();

    fireEvent.click(screen.getByText('+ Novo Atributo'));
    fireEvent.click(screen.getByText('save-new-attribute'));
    await waitFor(() => {
      expect(productTypeService.addAttributeToType).toHaveBeenCalledWith(1, {
        label: 'Peso',
        field_type: 'number',
      });
    });

    fireEvent.click(screen.getByText('edit-attribute'));
    fireEvent.click(screen.getByText('save-edit-attribute'));
    await waitFor(() => {
      expect(productTypeService.updateAttributeInType).toHaveBeenCalledWith(1, 11, {
        label: 'Cor editada',
        field_type: 'text',
      });
    });

    fireEvent.click(screen.getByText('delete-attribute'));
    await waitFor(() => {
      expect(productTypeService.removeAttributeFromType).toHaveBeenCalledWith(1, 11);
    });

    fireEvent.click(screen.getByText('reorder-attribute'));
    await waitFor(() => {
      expect(productTypeService.reorderAttributeInType).toHaveBeenCalledWith(1, 11, 'up');
    });

    fireEvent.click(screen.getByTitle('Deletar tipo'));
    await waitFor(() => {
      expect(productTypeService.deleteProductType).toHaveBeenCalledWith(1);
    });
    expect(showSuccessToast).toHaveBeenCalledWith(
      'Tipo de produto "Pecas" deletado com sucesso.'
    );
  });

  test('shows an error toast when deleting a type fails', async () => {
    productTypeService.deleteProductType.mockRejectedValueOnce({
      response: { data: { detail: 'tipo em uso' } },
    });

    render(<TiposProdutoPage />);

    fireEvent.click(screen.getByTitle('Deletar tipo'));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('tipo em uso');
    });
  });
});
