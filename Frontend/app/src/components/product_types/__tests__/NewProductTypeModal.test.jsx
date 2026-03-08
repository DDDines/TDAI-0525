import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import NewProductTypeModal from '../NewProductTypeModal.jsx';
import { useProductTypes } from '../../../contexts/ProductTypeContext';
import { showErrorToast } from '../../../utils/notifications';

jest.mock('../../../contexts/ProductTypeContext', () => ({
  useProductTypes: jest.fn(),
}));

jest.mock('../../../utils/notifications', () => ({
  showErrorToast: jest.fn(),
}));

describe('NewProductTypeModal', () => {
  const addProductType = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    useProductTypes.mockReturnValue({ addProductType });
  });

  test('does not render when closed', () => {
    render(<NewProductTypeModal isOpen={false} onClose={jest.fn()} onCreated={jest.fn()} />);

    expect(screen.queryByText(/Criar Novo Tipo de Produto/i)).not.toBeInTheDocument();
  });

  test('validates required friendly name', async () => {
    render(<NewProductTypeModal isOpen={true} onClose={jest.fn()} onCreated={jest.fn()} />);

    await userEvent.click(screen.getByRole('button', { name: /Salvar Tipo/i }));

    expect(showErrorToast).toHaveBeenCalled();
    expect(showErrorToast.mock.calls[0][0]).toMatch(/nome amig.+obrigat/i);
    expect(addProductType).not.toHaveBeenCalled();
  });

  test('rejects a friendly name that cannot produce a valid key', async () => {
    render(<NewProductTypeModal isOpen={true} onClose={jest.fn()} onCreated={jest.fn()} />);

    await userEvent.type(screen.getByLabelText(/Nome Amig/i), '***');
    await userEvent.click(screen.getByRole('button', { name: /Salvar Tipo/i }));

    expect(showErrorToast).toHaveBeenCalled();
    expect(showErrorToast.mock.calls[0][0]).toMatch(/chave v.+lida/i);
    expect(addProductType).not.toHaveBeenCalled();
  });

  test('creates a product type with normalized key name and callbacks', async () => {
    addProductType.mockResolvedValue({
      id: 8,
      key_name: 'linha_pesada',
      friendly_name: 'Linha Pesada',
    });
    const onClose = jest.fn();
    const onCreated = jest.fn();

    render(<NewProductTypeModal isOpen={true} onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/Nome Amig/i), 'Linha Pesada');
    await userEvent.click(screen.getByRole('button', { name: /Salvar Tipo/i }));

    await waitFor(() => {
      expect(addProductType).toHaveBeenCalledWith({
        key_name: 'linha_pesada',
        friendly_name: 'Linha Pesada',
        attribute_templates: [],
      });
    });
    expect(onCreated).toHaveBeenCalledWith({
      id: 8,
      key_name: 'linha_pesada',
      friendly_name: 'Linha Pesada',
    });
    expect(onClose).toHaveBeenCalled();
  });

  test('re-enables submit button after creation failure handled by context', async () => {
    addProductType.mockRejectedValue(new Error('Falha'));
    render(<NewProductTypeModal isOpen={true} onClose={jest.fn()} onCreated={jest.fn()} />);

    await userEvent.type(screen.getByLabelText(/Nome Amig/i), 'Eletronicos');
    await userEvent.click(screen.getByRole('button', { name: /Salvar Tipo/i }));

    await waitFor(() => {
      expect(addProductType).toHaveBeenCalled();
    });
    expect(screen.getByRole('button', { name: /Salvar Tipo/i })).toBeEnabled();
  });

  test('supports creation without an onCreated callback and resets state when reopened', async () => {
    addProductType.mockResolvedValue({ id: 9, key_name: 'linha_leve', friendly_name: 'Linha Leve' });
    const onClose = jest.fn();
    const { rerender } = render(
      <NewProductTypeModal isOpen={true} onClose={onClose} onCreated={undefined} />
    );

    await userEvent.type(screen.getByLabelText(/Nome Amig/i), 'Linha Leve');
    await userEvent.click(screen.getByRole('button', { name: /Salvar Tipo/i }));

    await waitFor(() => {
      expect(addProductType).toHaveBeenCalledWith({
        key_name: 'linha_leve',
        friendly_name: 'Linha Leve',
        attribute_templates: [],
      });
    });
    expect(onClose).toHaveBeenCalled();

    rerender(<NewProductTypeModal isOpen={false} onClose={onClose} onCreated={undefined} />);
    rerender(<NewProductTypeModal isOpen={true} onClose={onClose} onCreated={undefined} />);

    expect(screen.getByLabelText(/Nome Amig/i)).toHaveValue('');
  });
});
