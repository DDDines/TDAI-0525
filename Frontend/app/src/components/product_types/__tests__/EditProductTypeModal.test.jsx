import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import EditProductTypeModal from '../EditProductTypeModal.jsx';

test('prefills form with product type data', () => {
  const type = { friendly_name: 'Eletrônicos', key_name: 'eletronicos', description: 'Desc' };
  render(
    <EditProductTypeModal isOpen={true} onClose={() => {}} onSave={() => {}} type={type} isSubmitting={false} />
  );
  expect(screen.getByLabelText(/Nome Amig/i)).toHaveValue('Eletrônicos');
  expect(screen.getByLabelText(/Chave/i)).toHaveValue('eletronicos');
  expect(screen.getByLabelText(/Descri/i)).toHaveValue('Desc');
});

test('calls onSave with updated values', async () => {
  const type = { friendly_name: 'Eletrônicos', key_name: 'eletronicos', description: 'Desc' };
  const onSave = jest.fn();
  render(
    <EditProductTypeModal isOpen={true} onClose={() => {}} onSave={onSave} type={type} isSubmitting={false} />
  );

  await userEvent.clear(screen.getByLabelText(/Nome Amig/i));
  await userEvent.type(screen.getByLabelText(/Nome Amig/i), 'Novo Nome');
  await userEvent.clear(screen.getByLabelText(/Descri/i));
  await userEvent.type(screen.getByLabelText(/Descri/i), 'Nova desc');
  await userEvent.click(screen.getByRole('button', { name: /Salvar/i }));

  expect(onSave).toHaveBeenCalledWith({
    friendly_name: 'Novo Nome',
    description: 'Nova desc',
    key_name: 'eletronicos',
  });
});

test('does not render when closed and disables actions while submitting', () => {
  const onClose = jest.fn();
  const { rerender } = render(
    <EditProductTypeModal
      isOpen={false}
      onClose={onClose}
      onSave={jest.fn()}
      type={null}
      isSubmitting={true}
    />
  );

  expect(screen.queryByText(/Editar Tipo de Produto/i)).not.toBeInTheDocument();

  rerender(
    <EditProductTypeModal
      isOpen={true}
      onClose={onClose}
      onSave={jest.fn()}
      type={null}
      isSubmitting={true}
    />
  );

  expect(screen.getByLabelText(/Nome Amig/i)).toHaveValue('');
  expect(screen.getByLabelText(/Chave/i)).toHaveValue('');
  expect(screen.getByLabelText(/Descri/i)).toHaveValue('');
  expect(screen.getByRole('button', { name: /Cancelar/i })).toBeDisabled();
  expect(screen.getByRole('button', { name: /Salvando/i })).toBeDisabled();
});

test('resets fallback values when the edited type changes and calls onClose', async () => {
  const onClose = jest.fn();
  const { rerender } = render(
    <EditProductTypeModal
      isOpen={true}
      onClose={onClose}
      onSave={jest.fn()}
      type={{ friendly_name: 'Primeiro', key_name: 'primeiro', description: 'Desc 1' }}
      isSubmitting={false}
    />
  );

  expect(screen.getByLabelText(/Nome Amig/i)).toHaveValue('Primeiro');

  rerender(
    <EditProductTypeModal
      isOpen={true}
      onClose={onClose}
      onSave={jest.fn()}
      type={{ friendly_name: '', key_name: null, description: undefined }}
      isSubmitting={false}
    />
  );

  expect(screen.getByLabelText(/Nome Amig/i)).toHaveValue('');
  expect(screen.getByLabelText(/Chave/i)).toHaveValue('');
  expect(screen.getByLabelText(/Descri/i)).toHaveValue('');

  await userEvent.click(screen.getByRole('button', { name: /Cancelar/i }));
  expect(onClose).toHaveBeenCalled();
});
