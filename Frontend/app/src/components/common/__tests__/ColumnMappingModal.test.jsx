import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import ColumnMappingModal from '../ColumnMappingModal.jsx';

test('calls onConfirm with mapping object', async () => {
  const headers = ['Coluna A', 'Coluna B'];
  const rows = [
    { 'Coluna A': 'a1', 'Coluna B': 'b1' },
    { 'Coluna A': 'a2', 'Coluna B': 'b2' },
  ];
  const options = [
    { value: 'nome_produto', label: 'Nome Produto' },
    { value: 'preco', label: 'Preço' },
  ];
  const onConfirm = jest.fn();

  render(
    <ColumnMappingModal
      isOpen={true}
      onClose={() => {}}
      headers={headers}
      rows={rows}
      fieldOptions={options}
      onConfirm={onConfirm}
    />
  );

  await userEvent.selectOptions(screen.getAllByRole('combobox')[0], 'nome_produto');
  await userEvent.selectOptions(screen.getAllByRole('combobox')[1], 'preco');

  await userEvent.click(screen.getByText('Confirmar mapeamento'));

  expect(onConfirm).toHaveBeenCalledWith({
    'Coluna A': 'nome_produto',
    'Coluna B': 'preco',
  });
});

test('does not reset selected mapping on rerender when initialMapping is omitted', async () => {
  const headers = ['Coluna A'];
  const rows = [{ 'Coluna A': 'a1' }];
  const options = [{ value: 'nome_produto', label: 'Nome Produto' }];

  const { rerender } = render(
    <ColumnMappingModal
      isOpen={true}
      onClose={() => {}}
      headers={headers}
      rows={rows}
      fieldOptions={options}
      onConfirm={() => {}}
    />
  );

  const select = screen.getByRole('combobox', { name: /campo para coluna coluna a/i });
  await userEvent.selectOptions(select, 'nome_produto');
  expect(select).toHaveValue('nome_produto');

  rerender(
    <ColumnMappingModal
      isOpen={true}
      onClose={() => {}}
      headers={headers}
      rows={[{ 'Coluna A': 'a2' }]}
      fieldOptions={options}
      onConfirm={() => {}}
    />
  );

  expect(screen.getByRole('combobox', { name: /campo para coluna coluna a/i })).toHaveValue(
    'nome_produto'
  );
});
