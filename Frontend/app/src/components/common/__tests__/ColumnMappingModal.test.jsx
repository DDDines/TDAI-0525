import { fireEvent, render, screen } from '@testing-library/react';
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

test('keeps local mapping edits when the same initial mapping is provided again', async () => {
  const headers = ['Coluna A'];
  const options = [
    { value: 'nome_produto', label: 'Nome Produto' },
    { value: 'sku_original', label: 'SKU' },
  ];

  const { rerender } = render(
    <ColumnMappingModal
      isOpen={true}
      onClose={() => {}}
      headers={headers}
      rows={[]}
      fieldOptions={options}
      initialMapping={{ 'Coluna A': 'nome_produto' }}
      onConfirm={() => {}}
    />
  );

  const select = screen.getByRole('combobox', { name: /campo para coluna coluna a/i });
  expect(select).toHaveValue('nome_produto');

  await userEvent.selectOptions(select, 'sku_original');
  expect(select).toHaveValue('sku_original');

  rerender(
    <ColumnMappingModal
      isOpen={true}
      onClose={() => {}}
      headers={headers}
      rows={[]}
      fieldOptions={options}
      initialMapping={{ 'Coluna A': 'nome_produto' }}
      onConfirm={() => {}}
    />
  );

  expect(screen.getByRole('combobox', { name: /campo para coluna coluna a/i })).toHaveValue(
    'sku_original'
  );
});

test('does not render when closed', () => {
  render(
    <ColumnMappingModal
      isOpen={false}
      onClose={() => {}}
      headers={['Coluna A']}
      rows={[]}
      fieldOptions={[]}
    />
  );

  expect(screen.queryByText('Mapear Colunas')).not.toBeInTheDocument();
});

test('keeps unique base fields exclusive across headers and clears the mapping', async () => {
  const user = userEvent.setup();
  const options = [
    { value: 'sku_original', label: 'SKU' },
    { value: 'descricao_original', label: 'Descrição' },
  ];

  render(
    <ColumnMappingModal
      isOpen={true}
      onClose={() => {}}
      headers={['Coluna A', 'Coluna B']}
      rows={[]}
      fieldOptions={options}
      onConfirm={() => {}}
    />
  );

  const firstSelect = screen.getByRole('combobox', { name: /campo para coluna coluna a/i });
  const secondSelect = screen.getByRole('combobox', { name: /campo para coluna coluna b/i });

  await user.selectOptions(firstSelect, 'sku_original');

  const secondSkuOption = screen.getAllByRole('option', { name: 'SKU' })[1];
  expect(secondSkuOption).toBeDisabled();

  await user.click(screen.getByRole('button', { name: /Limpar mapeamento/i }));

  expect(firstSelect).toHaveValue('');
  expect(secondSelect).toHaveValue('');
});

test('clears the previous header when the same unique base field is forced into another column', async () => {
  render(
    <ColumnMappingModal
      isOpen={true}
      onClose={() => {}}
      headers={['Coluna A', 'Coluna B']}
      rows={[]}
      fieldOptions={[
        { value: 'sku_original', label: 'SKU' },
        { value: 'descricao_original', label: 'DescriÃ§Ã£o' },
      ]}
      onConfirm={() => {}}
    />
  );

  const firstSelect = screen.getByRole('combobox', { name: /campo para coluna coluna a/i });
  const secondSelect = screen.getByRole('combobox', { name: /campo para coluna coluna b/i });

  await userEvent.selectOptions(firstSelect, 'sku_original');
  fireEvent.change(secondSelect, { target: { value: 'sku_original' } });

  expect(firstSelect).toHaveValue('');
  expect(secondSelect).toHaveValue('sku_original');
});

test('renders product type choices, preview object cells and syncs a new initial mapping', async () => {
  const user = userEvent.setup();
  const onProductTypeChange = jest.fn();
  const { rerender } = render(
    <ColumnMappingModal
      isOpen={true}
      onClose={() => {}}
      headers={['Coluna A']}
      rows={[{ 'Coluna A': { codigo: 'ABC-1' } }]}
      fieldOptions={[{ value: 'descricao_original', label: 'Descrição' }]}
      productTypes={[
        { id: 5, friendly_name: 'Automotivo' },
        { id: 6, nome: 'Industrial' },
        { id: null, friendly_name: 'Ignorar' },
      ]}
      productTypeId="5"
      onProductTypeChange={onProductTypeChange}
      initialMapping={{ 'Coluna A': 'descricao_original' }}
      onConfirm={() => {}}
    />
  );

  expect(screen.getByText('{"codigo":"ABC-1"}')).toBeInTheDocument();
  await user.selectOptions(screen.getByRole('combobox', { name: /Tipo de Produto/i }), '6');
  expect(onProductTypeChange).toHaveBeenCalledWith('6');
  expect(screen.getByRole('combobox', { name: /campo para coluna coluna a/i })).toHaveValue(
    'descricao_original'
  );

  rerender(
    <ColumnMappingModal
      isOpen={true}
      onClose={() => {}}
      headers={['Coluna A']}
      rows={[{ 'Coluna A': null }]}
      fieldOptions={[{ value: 'sku_original', label: 'SKU' }]}
      productTypes={[{ id: 5, friendly_name: 'Automotivo' }]}
      productTypeId="5"
      onProductTypeChange={onProductTypeChange}
      initialMapping={{ 'Coluna A': 'sku_original' }}
      onConfirm={() => {}}
    />
  );

  expect(screen.getByRole('combobox', { name: /campo para coluna coluna a/i })).toHaveValue(
    'sku_original'
  );
});
