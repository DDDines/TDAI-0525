import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import AttributeTemplateModal from '../AttributeTemplateModal.jsx';
import { showErrorToast } from '../../../utils/notifications';

jest.mock('../../../utils/notifications', () => ({
  showErrorToast: jest.fn(),
}));

describe('AttributeTemplateModal', () => {
  const onClose = jest.fn();
  const onSave = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  function renderModal(props = {}) {
    return render(
      <AttributeTemplateModal
        isOpen={true}
        onClose={onClose}
        onSave={onSave}
        isSubmitting={false}
        {...props}
      />
    );
  }

  test('does not render when closed', () => {
    render(
      <AttributeTemplateModal
        isOpen={false}
        onClose={onClose}
        onSave={onSave}
        isSubmitting={false}
      />
    );

    expect(screen.queryByText(/Novo Atributo/i)).not.toBeInTheDocument();
  });

  test('validates required fields before saving', async () => {
    renderModal();

    fireEvent.submit(screen.getByRole('button', { name: /Salvar Atributo/i }).closest('form'));

    expect(showErrorToast.mock.calls[0][0]).toMatch(/obrigat/i);
    expect(onSave).not.toHaveBeenCalled();
  });

  test('validates JSON array options for select fields', async () => {
    const user = userEvent.setup();
    renderModal();

    await user.type(screen.getByLabelText(/R.tulo/i), 'Cor');
    await user.type(screen.getByLabelText(/Chave do Atributo/i), 'cor');
    await user.selectOptions(screen.getByLabelText(/Tipo do Campo/i), 'SELECT');
    fireEvent.change(screen.getByLabelText(/Op..es/i), { target: { value: '{"a":1}' } });
    await user.click(screen.getByRole('button', { name: /Salvar Atributo/i }));

    expect(showErrorToast.mock.calls.at(-1)[0]).toMatch(/array json/i);
    expect(onSave).not.toHaveBeenCalled();
  });

  test('rejects malformed select options JSON', async () => {
    const user = userEvent.setup();
    renderModal();

    await user.type(screen.getByLabelText(/R.tulo/i), 'Cor');
    await user.type(screen.getByLabelText(/Chave do Atributo/i), 'cor');
    await user.selectOptions(screen.getByLabelText(/Tipo do Campo/i), 'SELECT');
    fireEvent.change(screen.getByLabelText(/Op..es/i), { target: { value: '["Preto"' } });
    await user.click(screen.getByRole('button', { name: /Salvar Atributo/i }));

    expect(showErrorToast.mock.calls.at(-1)[0]).toMatch(/formato das op/i);
    expect(onSave).not.toHaveBeenCalled();
  });

  test('normalizes field type to lowercase and keeps JSON options for select', async () => {
    const user = userEvent.setup();
    renderModal();

    await user.type(screen.getByLabelText(/R.tulo/i), 'Cor');
    await user.type(screen.getByLabelText(/Chave do Atributo/i), 'cor');
    await user.selectOptions(screen.getByLabelText(/Tipo do Campo/i), 'SELECT');
    fireEvent.change(screen.getByLabelText(/Op..es/i), { target: { value: '["Preto","Branco"]' } });
    await user.click(screen.getByRole('button', { name: /Salvar Atributo/i }));

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        label: 'Cor',
        attribute_key: 'cor',
        field_type: 'select',
        options: '["Preto","Branco"]',
      })
    );
  });

  test('sends options as null for non-select field types', async () => {
    const user = userEvent.setup();
    renderModal();

    await user.type(screen.getByLabelText(/R.tulo/i), 'Peso');
    await user.type(screen.getByLabelText(/Chave do Atributo/i), 'peso');
    await user.selectOptions(screen.getByLabelText(/Tipo do Campo/i), 'NUMBER');
    await user.click(screen.getByRole('button', { name: /Salvar Atributo/i }));

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        label: 'Peso',
        attribute_key: 'peso',
        field_type: 'number',
        options: null,
      })
    );
  });

  test('loads edit mode data and locks the attribute key', () => {
    renderModal({
      attribute: {
        id: 9,
        label: 'Memoria RAM',
        attribute_key: 'memoria_ram',
        field_type: 'MULTISELECT',
        options: ['8GB', '16GB'],
      },
    });

    expect(screen.getByText(/Editar Atributo/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/R.tulo/i)).toHaveValue('Memoria RAM');
    expect(screen.getByLabelText(/Chave do Atributo/i)).toHaveValue('memoria_ram');
    expect(screen.getByLabelText(/Chave do Atributo/i)).toBeDisabled();
    expect(screen.getByLabelText(/Tipo do Campo/i)).toHaveValue('MULTISELECT');
    expect(screen.getByLabelText(/Op..es/i)).toHaveValue('[\n  "8GB",\n  "16GB"\n]');
  });
});
