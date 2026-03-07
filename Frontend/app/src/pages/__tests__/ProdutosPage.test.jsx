import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import ProdutosPage from '../ProdutosPage.jsx';
import productService from '../../services/productService';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

jest.mock('../../services/productService', () => ({
  __esModule: true,
  default: {
    getProdutos: jest.fn(),
  },
}));

jest.mock('../../contexts/AppExperienceContext', () => ({
  useAppExperience: () => ({
    effectiveMode: 'basic',
  }),
}));

jest.mock('../../contexts/ProductTypeContext', () => ({
  useProductTypes: () => ({
    productTypes: [],
    isLoading: false,
    error: null,
  }),
}));

jest.mock('../../utils/notifications', () => ({
  showErrorToast: jest.fn(),
  showSuccessToast: jest.fn(),
  showInfoToast: jest.fn(),
  showWarningToast: jest.fn(),
}));

describe('ProdutosPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    productService.getProdutos.mockResolvedValue({
      items: [
        {
          id: 2558,
          nome_base: 'Reservatório de AR 20 Litros',
          sku: '987 308 430 7005',
          fornecedor_id: 3,
          status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
          status_titulo_ia: 'CONCLUIDO',
          status_descricao_ia: 'CONCLUIDO',
          data_atualizacao: '2026-03-07T12:00:00Z',
        },
      ],
      total_items: 1,
    });
  });

  test('mantem chips de status de titulo e descricao visiveis mesmo no modo basico', async () => {
    render(
      <MemoryRouter initialEntries={['/produtos']}>
        <ProdutosPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenCalled();
    });

    expect(await screen.findByText('Reservatório de AR 20 Litros')).toBeInTheDocument();
    expect(screen.getByText('Web')).toBeInTheDocument();
    expect(screen.getByText('Tit')).toBeInTheDocument();
    expect(screen.getByText('Desc')).toBeInTheDocument();
  });
});

