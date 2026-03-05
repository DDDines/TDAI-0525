import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ProductEditModal from '../ProductEditModal.jsx';

const mockProductTypes = [
  {
    id: 1,
    friendly_name: 'Automotivo',
    attribute_templates: [
      { attribute_key: 'titulo_auto', label: 'Titulo', field_type: 'text', is_required: false },
      { attribute_key: 'id_auto', label: 'ID', field_type: 'text', is_required: false },
      { attribute_key: 'Desc_Auto', label: 'Descricao', field_type: 'textarea', is_required: false },
    ],
  },
];

jest.mock('../../services/productService', () => ({
  __esModule: true,
  default: {
    getProdutoById: jest.fn(() =>
      Promise.resolve({
        id: 1,
        nome_base: 'Produto',
        fornecedor_id: 1,
        product_type_id: 1,
        product_type: { id: 1 },
        dynamic_attributes: {
          titulo: 'Titulo extraido',
          id: 'SP1081',
          descricao: 'Descricao extraida',
        },
      })
    ),
    getAtributoSuggestions: jest.fn(() => Promise.resolve({})),
    gerarTitulosProdutoModoBasico: jest.fn(() => Promise.resolve({})),
    gerarDescricaoProdutoModoBasico: jest.fn(() => Promise.resolve({})),
  },
}));

jest.mock('../../services/fornecedorService', () => ({
  __esModule: true,
  default: {
    getFornecedores: jest.fn(() => Promise.resolve({ items: [] })),
    getFornecedorById: jest.fn(() => Promise.resolve({ id: 1, nome: 'F' })),
  },
}));

jest.mock('../../contexts/ProductTypeContext', () => ({
  useProductTypes: () => ({ productTypes: mockProductTypes, addProductType: jest.fn() }),
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: true }),
}));

function renderModal() {
  return render(
    <ProductEditModal
      isOpen={true}
      onClose={() => {}}
      product={{ id: 1 }}
      showAiFeatures={true}
    />
  );
}

test('fetchGeminiSuggestions does not crash when API returns empty object', async () => {
  renderModal();
  await userEvent.click(screen.getByRole('button', { name: /sugest/i }));
  const btn = screen.getByRole('button', { name: /buscar sugest/i });
  await userEvent.click(btn);
  expect(btn).not.toBeDisabled();
});

test('maps alias dynamic attributes to template keys when product payload lacks templates', async () => {
  renderModal();
  await userEvent.click(screen.getByRole('button', { name: /atributos/i }));

  expect(await screen.findByLabelText(/^titulo/i)).toHaveValue('Titulo extraido');
  expect(screen.getByLabelText(/^id/i)).toHaveValue('SP1081');
  expect(screen.getByLabelText(/^descricao/i)).toHaveValue('Descricao extraida');
});

test('shows basic generation actions when ai features are disabled', async () => {
  render(
    <ProductEditModal
      isOpen={true}
      onClose={() => {}}
      product={{ id: 1 }}
      showAiFeatures={false}
    />
  );

  await userEvent.click(screen.getByRole('button', { name: /conte[uú]do/i }));

  expect(screen.getByRole('button', { name: /gerar t[ií]tulos \(b[aá]sico\)/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /gerar descri[cç][aã]o \(b[aá]sico\)/i })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /sugest[oõ]es ia/i })).not.toBeInTheDocument();
});
