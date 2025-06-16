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
    />,
  );

  await userEvent.selectOptions(
    screen.getAllByRole('combobox')[0],
    'nome_produto',
  );
  await userEvent.selectOptions(screen.getAllByRole('combobox')[1], 'preco');

  await userEvent.click(screen.getByText('Confirmar mapeamento'));

  expect(onConfirm).toHaveBeenCalledWith({
    'Coluna A': 'nome_produto',
    'Coluna B': 'preco',
  });
});
