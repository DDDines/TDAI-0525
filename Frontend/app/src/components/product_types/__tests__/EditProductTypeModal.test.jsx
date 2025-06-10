import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EditProductTypeModal from '../EditProductTypeModal.jsx';

test('prefills form with product type data', () => {
  const type = { friendly_name: 'Eletrônicos', key_name: 'eletronicos', description: 'Desc' };
  render(
    <EditProductTypeModal isOpen={true} onClose={() => {}} onSave={() => {}} type={type} isSubmitting={false} />
  );
  expect(screen.getByLabelText(/Nome Amigável/i)).toHaveValue('Eletrônicos');
  expect(screen.getByLabelText(/Chave/i)).toHaveValue('eletronicos');
  expect(screen.getByLabelText(/Descrição/i)).toHaveValue('Desc');
});

test('calls onSave with updated values', async () => {
  const type = { friendly_name: 'Eletrônicos', key_name: 'eletronicos', description: 'Desc' };
  const onSave = jest.fn();
  render(
    <EditProductTypeModal isOpen={true} onClose={() => {}} onSave={onSave} type={type} isSubmitting={false} />
  );

  await userEvent.clear(screen.getByLabelText(/Nome Amigável/i));
  await userEvent.type(screen.getByLabelText(/Nome Amigável/i), 'Novo Nome');
  await userEvent.clear(screen.getByLabelText(/Descrição/i));
  await userEvent.type(screen.getByLabelText(/Descrição/i), 'Nova desc');
  await userEvent.click(screen.getByText('Salvar'));

  expect(onSave).toHaveBeenCalledWith({ friendly_name: 'Novo Nome', description: 'Nova desc', key_name: 'eletronicos' });
});
