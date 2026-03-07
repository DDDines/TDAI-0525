import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import AttributeTemplateList from '../AttributeTemplateList.jsx';

describe('AttributeTemplateList', () => {
  const onEdit = jest.fn();
  const onDelete = jest.fn();
  const onReorder = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders the empty state when there are no attributes', () => {
    render(
      <AttributeTemplateList
        attributes={[]}
        onEdit={onEdit}
        onDelete={onDelete}
        onReorder={onReorder}
      />
    );

    expect(
      screen.getByText(/Nenhum atributo definido para este tipo de produto/i)
    ).toBeInTheDocument();
  });

  test('sorts attributes by display order and wires edit/delete handlers', async () => {
    const user = userEvent.setup();
    const attributes = [
      {
        id: 2,
        label: 'Material',
        attribute_key: 'material',
        field_type: 'TEXT',
        display_order: 1,
      },
      {
        id: 1,
        label: 'Cor',
        attribute_key: 'cor',
        field_type: 'SELECT',
        options: ['Preto', 'Branco'],
        display_order: 0,
      },
    ];

    render(
      <AttributeTemplateList
        attributes={attributes}
        onEdit={onEdit}
        onDelete={onDelete}
        onReorder={onReorder}
      />
    );

    const titles = screen.getAllByText(/Cor|Material/);
    expect(titles[0]).toHaveTextContent('Cor');
    expect(titles[1]).toHaveTextContent('Material');
    expect(screen.getByText(/Preto, Branco/i)).toBeInTheDocument();

    await user.click(screen.getAllByRole('button', { name: /Editar/i })[0]);
    expect(onEdit).toHaveBeenCalledWith(expect.objectContaining({ id: 1 }));

    await user.click(screen.getAllByRole('button', { name: /Excluir/i })[1]);
    expect(onDelete).toHaveBeenCalledWith(2);
  });

  test('enables reorder controls only where movement is possible', async () => {
    const user = userEvent.setup();
    const attributes = [
      { id: 1, label: 'Cor', attribute_key: 'cor', field_type: 'TEXT', display_order: 0 },
      { id: 2, label: 'Peso', attribute_key: 'peso', field_type: 'NUMBER', display_order: 1 },
      { id: 3, label: 'Modelo', attribute_key: 'modelo', field_type: 'TEXT', display_order: 2 },
    ];

    render(
      <AttributeTemplateList
        attributes={attributes}
        onEdit={onEdit}
        onDelete={onDelete}
        onReorder={onReorder}
      />
    );

    const moveUpButtons = screen.getAllByTitle(/Mover para Cima/i);
    const moveDownButtons = screen.getAllByTitle(/Mover para Baixo/i);

    expect(moveUpButtons[0]).toBeDisabled();
    expect(moveDownButtons[2]).toBeDisabled();

    await user.click(moveUpButtons[1]);
    await user.click(moveDownButtons[1]);

    expect(onReorder).toHaveBeenNthCalledWith(1, 2, 'up');
    expect(onReorder).toHaveBeenNthCalledWith(2, 2, 'down');
  });
});
