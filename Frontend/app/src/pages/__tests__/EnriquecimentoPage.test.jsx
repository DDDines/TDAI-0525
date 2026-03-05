import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

import EnriquecimentoPage from '../EnriquecimentoPage.jsx';
import productService from '../../services/productService';

jest.mock('../../services/productService', () => ({
  __esModule: true,
  default: {
    getProdutos: jest.fn(),
    iniciarEnriquecimentoWebProduto: jest.fn(),
    getProdutoById: jest.fn(),
  },
}));

jest.mock('../../services/usoIAService', () => ({
  __esModule: true,
  default: {
    getHistoricoUsoIAPorProduto: jest.fn(() => Promise.resolve([])),
  },
}));

jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
    error: jest.fn(),
  },
}));

describe('EnriquecimentoPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    productService.getProdutos.mockResolvedValue({
      items: [
        {
          id: 1,
          nome_base: 'Produto Teste',
          sku: 'SKU-1',
          fornecedor_id: 10,
          status_enriquecimento_web: 'NAO_INICIADO',
          status_titulo_ia: 'NAO_INICIADO',
          status_descricao_ia: 'NAO_INICIADO',
          data_atualizacao: null,
        },
      ],
      total_items: 1,
    });
    productService.iniciarEnriquecimentoWebProduto.mockResolvedValue({
      msg: 'ok',
    });
    productService.getProdutoById.mockResolvedValue({
      id: 1,
      status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
    });
  });

  test('calls enrichment endpoint when clicking Enriquecer Web with selected product', async () => {
    render(<EnriquecimentoPage />);

    await waitFor(() => expect(productService.getProdutos).toHaveBeenCalled());

    const checkboxes = screen.getAllByRole('checkbox');
    await userEvent.click(checkboxes[0]);

    const enrichButton = screen.getByRole('button', { name: /Enriquecer Web/i });
    expect(enrichButton).toBeEnabled();

    await userEvent.click(enrichButton);

    await waitFor(() =>
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(1)
    );
  });
});

