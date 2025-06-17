import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ProductEditModal from '../ProductEditModal.jsx';

jest.mock('../../services/productService', () => ({
  __esModule: true,
  default: {
    getProdutoById: jest.fn(() => Promise.resolve({
      id: 1,
      nome_base: 'Produto',
      fornecedor_id: 1,
      product_type_id: 1,
    })),
    getAtributoSuggestions: jest.fn(() => Promise.resolve({})),
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
  useProductTypes: () => ({ productTypes: [], addProductType: jest.fn() }),
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: true }),
}));

// Simple render helper
const renderModal = () =>
  render(<ProductEditModal isOpen={true} onClose={() => {}} product={{ id: 1 }} />);

test('fetchGeminiSuggestions does not crash when API returns empty object', async () => {
  renderModal();
  // Switch to suggestions tab
  await userEvent.click(screen.getByRole('button', { name: /sugestões ia/i }));
  const btn = screen.getByRole('button', { name: /buscar sugestões \(gemini\)/i });
  await userEvent.click(btn);
  expect(btn).not.toBeDisabled();
});
