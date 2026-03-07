import { fireEvent, render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import AttributeField from '../AttributeField.jsx';

describe('AttributeField', () => {
  let consoleErrorSpy;

  beforeEach(() => {
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  test('renders text field using template default value and emits updates', () => {
    const onChange = jest.fn();
    render(
      <AttributeField
        attributeTemplate={{
          attribute_key: 'marca',
          label: 'Marca',
          field_type: 'text',
          default_value: 'Randon',
          is_required: true,
          tooltip_text: 'Marca do produto',
        }}
        value={undefined}
        onChange={onChange}
      />,
    );

    expect(screen.getByLabelText(/Marca/i)).toHaveValue('Randon');
    expect(screen.getByTitle('Marca do produto')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Marca/i), {
      target: { value: 'Meritor' },
    });

    expect(onChange).toHaveBeenCalledWith('marca', 'Meritor');
  });

  test('renders textarea, number and date fields with direct values', () => {
    const onChange = jest.fn();
    const { rerender } = render(
      <AttributeField
        attributeTemplate={{
          attribute_key: 'descricao',
          label: 'Descricao',
          field_type: 'textarea',
        }}
        value="Texto base"
        onChange={onChange}
      />,
    );

    expect(screen.getByLabelText(/Descricao/i)).toHaveValue('Texto base');
    fireEvent.change(screen.getByLabelText(/Descricao/i), {
      target: { value: 'Texto base novo' },
    });
    expect(onChange).toHaveBeenCalledWith('descricao', 'Texto base novo');

    rerender(
      <AttributeField
        attributeTemplate={{
          attribute_key: 'peso',
          label: 'Peso',
          field_type: 'number',
        }}
        value={42}
        onChange={onChange}
      />,
    );
    expect(screen.getByLabelText(/Peso/i)).toHaveValue(42);

    rerender(
      <AttributeField
        attributeTemplate={{
          attribute_key: 'fabricacao',
          label: 'Fabricacao',
          field_type: 'date',
        }}
        value="2026-03-07"
        onChange={onChange}
      />,
    );
    expect(screen.getByLabelText(/Fabricacao/i)).toHaveValue('2026-03-07');
  });

  test('renders boolean field and maps change to checked boolean', async () => {
    const onChange = jest.fn();
    render(
      <AttributeField
        attributeTemplate={{
          attribute_key: 'ativo',
          label: 'Ativo',
          field_type: 'boolean',
          default_value: '1',
        }}
        value={undefined}
        onChange={onChange}
      />,
    );

    const checkbox = screen.getByRole('checkbox', { name: /Ativo/i });
    expect(checkbox).toBeChecked();

    await userEvent.click(checkbox);
    expect(onChange).toHaveBeenCalledWith('ativo', false);
  });

  test('renders select field from JSON string options', async () => {
    const onChange = jest.fn();
    render(
      <AttributeField
        attributeTemplate={{
          attribute_key: 'cor',
          label: 'Cor',
          field_type: 'select',
          options: '["Preto","Branco"]',
        }}
        value="Preto"
        onChange={onChange}
      />,
    );

    expect(screen.getByRole('option', { name: 'Preto' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Branco' })).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText(/Cor/i), 'Branco');
    expect(onChange).toHaveBeenCalledWith('cor', 'Branco');
  });

  test('handles invalid select JSON and unsupported field types', () => {
    const { rerender } = render(
      <AttributeField
        attributeTemplate={{
          attribute_key: 'acabamento',
          label: 'Acabamento',
          field_type: 'select',
          options: '{invalid}',
        }}
        value=""
        onChange={jest.fn()}
      />,
    );

    expect(consoleErrorSpy).toHaveBeenCalled();
    expect(screen.getByRole('option', { name: /Selecione acabamento/i })).toBeInTheDocument();

    rerender(
      <AttributeField
        attributeTemplate={{
          attribute_key: 'cores',
          label: 'Cores',
          field_type: 'multiselect',
        }}
        value={[]}
        onChange={jest.fn()}
        disabled={true}
      />,
    );

    expect(screen.getByText(/suportado por AttributeField/i)).toBeInTheDocument();
  });
});
