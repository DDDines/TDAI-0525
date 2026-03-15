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
  const labelMatcher = /R.*tulo/i;
  const optionsMatcher = /Op.*es/i;

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

    await user.type(screen.getByLabelText(labelMatcher), 'Cor');
    await user.type(screen.getByLabelText(/Chave do Atributo/i), 'cor');
    await user.selectOptions(screen.getByLabelText(/Tipo do Campo/i), 'SELECT');
    fireEvent.change(screen.getByLabelText(optionsMatcher), { target: { value: '{"a":1}' } });
    await user.click(screen.getByRole('button', { name: /Salvar Atributo/i }));

    expect(showErrorToast.mock.calls.at(-1)[0]).toMatch(/array json/i);
    expect(onSave).not.toHaveBeenCalled();
  });

  test('rejects malformed select options JSON', async () => {
    const user = userEvent.setup();
    renderModal();

    await user.type(screen.getByLabelText(labelMatcher), 'Cor');
    await user.type(screen.getByLabelText(/Chave do Atributo/i), 'cor');
    await user.selectOptions(screen.getByLabelText(/Tipo do Campo/i), 'SELECT');
    fireEvent.change(screen.getByLabelText(optionsMatcher), { target: { value: '["Preto"' } });
    await user.click(screen.getByRole('button', { name: /Salvar Atributo/i }));

    expect(showErrorToast.mock.calls.at(-1)[0]).toMatch(/formato das op/i);
    expect(onSave).not.toHaveBeenCalled();
  });

  test('normalizes field type to lowercase and keeps JSON options for select', async () => {
    const user = userEvent.setup();
    renderModal();

    await user.type(screen.getByLabelText(labelMatcher), 'Cor');
    await user.type(screen.getByLabelText(/Chave do Atributo/i), 'cor');
    await user.selectOptions(screen.getByLabelText(/Tipo do Campo/i), 'SELECT');
    fireEvent.change(screen.getByLabelText(optionsMatcher), { target: { value: '["Preto","Branco"]' } });
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

    await user.type(screen.getByLabelText(labelMatcher), 'Peso');
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

  test('keeps saving with an empty field type when the select value is manually cleared', async () => {
    const user = userEvent.setup();
    renderModal();

    await user.type(screen.getByLabelText(labelMatcher), 'Peso');
    await user.type(screen.getByLabelText(/Chave do Atributo/i), 'peso');
    fireEvent.change(screen.getByLabelText(/Tipo do Campo/i), { target: { value: '' } });
    await user.click(screen.getByRole('button', { name: /Salvar Atributo/i }));

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        field_type: '',
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
    expect(screen.getByLabelText(labelMatcher)).toHaveValue('Memoria RAM');
    expect(screen.getByLabelText(/Chave do Atributo/i)).toHaveValue('memoria_ram');
    expect(screen.getByLabelText(/Chave do Atributo/i)).toBeDisabled();
    expect(screen.getByLabelText(/Tipo do Campo/i)).toHaveValue('MULTISELECT');
    expect(screen.getByLabelText(optionsMatcher)).toHaveValue('[\n  "8GB",\n  "16GB"\n]');
  });

  test('updates checkbox fields and renders submitting controls when disabled', async () => {
    const user = userEvent.setup();
    const { rerender } = renderModal();

    await user.type(screen.getByLabelText(labelMatcher), 'Garantia');
    await user.type(screen.getByLabelText(/Chave do Atributo/i), 'garantia');
    await user.click(screen.getByLabelText(/Campo obrigatorio/i));
    await user.click(screen.getByRole('button', { name: /Salvar Atributo/i }));

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        is_required: true,
      })
    );

    rerender(
      <AttributeTemplateModal
        isOpen={true}
        onClose={onClose}
        onSave={onSave}
        isSubmitting={true}
      />
    );

    expect(screen.getByRole('button', { name: /Salvando/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Cancelar/i })).toBeDisabled();
  });

  test('keeps IA collection enabled by default for new attributes', async () => {
    const user = userEvent.setup();
    renderModal();

    expect(screen.getByLabelText(/Usar este atributo na IA/i)).toBeChecked();

    await user.type(screen.getByLabelText(labelMatcher), 'Cor');
    await user.type(screen.getByLabelText(/Chave do Atributo/i), 'cor');
    await user.click(screen.getByRole('button', { name: /Salvar Atributo/i }));

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        collect_in_ai: true,
      })
    );
  });

  test('loads and preserves collect_in_ai=false when editing an attribute', () => {
    renderModal({
      attribute: {
        id: 11,
        label: 'Aplicacao',
        attribute_key: 'aplicacao',
        field_type: 'TEXTAREA',
        collect_in_ai: false,
      },
    });

    expect(screen.getByLabelText(/Usar este atributo na IA/i)).not.toBeChecked();
  });
});
