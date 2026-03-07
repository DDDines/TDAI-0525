import { act, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ProductEditModal from '../ProductEditModal.jsx';
import productService from '../../services/productService';
import { useProductTypes } from '../../contexts/ProductTypeContext';
import {
  showInfoToast,
  showSuccessToast,
  showWarningToast,
} from '../../utils/notifications';

const mockProductTypes = [
  {
    id: 1,
    friendly_name: 'Automotivo',
    attribute_templates: [
      { attribute_key: 'titulo_auto', label: 'Titulo', field_type: 'text', is_required: false },
      { attribute_key: 'id_auto', label: 'ID', field_type: 'text', is_required: false },
      { attribute_key: 'Desc_Auto', label: 'Descricao', field_type: 'textarea', is_required: false },
      { attribute_key: 'cor', label: 'Cor', field_type: 'text', is_required: false, default_value: 'Preta' },
      { attribute_key: 'voltagem', label: 'Voltagem', field_type: 'number', is_required: false, default_value: null },
    ],
  },
  {
    id: 2,
    friendly_name: 'Acessorios',
    attribute_templates: [
      { attribute_key: 'material', label: 'Material', field_type: 'text', is_required: false, default_value: 'Aco' },
    ],
  },
];

const fornecedores = [
  { id: 1, nome: 'Fornecedor 1', site_url: 'https://fornecedor-1.example' },
  { id: 2, nome: 'Fornecedor 2', site_url: 'https://fornecedor-2.example' },
];

jest.mock('../../services/productService', () => ({
  __esModule: true,
  default: {
    getProdutoById: jest.fn(),
    getAtributoSuggestions: jest.fn(() => Promise.resolve({})),
    gerarTitulosProdutoModoBasico: jest.fn(() => Promise.resolve({})),
    gerarDescricaoProdutoModoBasico: jest.fn(() => Promise.resolve({})),
    gerarTitulosProduto: jest.fn(() => Promise.resolve({})),
    gerarDescricaoProduto: jest.fn(() => Promise.resolve({})),
    iniciarEnriquecimentoWebProduto: jest.fn(() => Promise.resolve({})),
    createProduto: jest.fn(),
    updateProduto: jest.fn(),
  },
}));

jest.mock('../../services/fornecedorService', () => ({
  __esModule: true,
  default: {
    getFornecedores: jest.fn(() => Promise.resolve({ items: fornecedores })),
    getFornecedorById: jest.fn(() => Promise.resolve(fornecedores[0])),
  },
}));

jest.mock('../../contexts/ProductTypeContext', () => ({
  useProductTypes: jest.fn(),
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: true, user: { id: 7 } }),
}));

jest.mock('../../contexts/AppExperienceContext', () => ({
  useAppExperience: () => ({ effectiveMode: 'basic' }),
}));

jest.mock('../../utils/notifications', () => ({
  showSuccessToast: jest.fn(),
  showErrorToast: jest.fn(),
  showInfoToast: jest.fn(),
  showWarningToast: jest.fn(),
}));

jest.mock('../produtos/shared/AttributeField', () => ({
  __esModule: true,
  default: ({ attributeTemplate, value, onChange }) => (
    <label htmlFor={`attr-${attributeTemplate.attribute_key}`}>
      {attributeTemplate.label}
      <input
        id={`attr-${attributeTemplate.attribute_key}`}
        value={String(value ?? '')}
        onChange={(event) => onChange(attributeTemplate.attribute_key, event.target.value)}
      />
    </label>
  ),
}));

jest.mock('../product_types/NewProductTypeModal.jsx', () => ({
  __esModule: true,
  default: ({ isOpen, onCreated, onClose }) =>
    isOpen ? (
      <div data-testid="new-product-type-modal">
        <button
          type="button"
          onClick={() => {
            onCreated({ id: 2, friendly_name: 'Acessorios' });
            onClose();
          }}
        >
          complete-new-type
        </button>
      </div>
    ) : null,
}));

jest.mock('../common/LoadingOverlay.jsx', () => ({
  __esModule: true,
  default: ({ isOpen, message }) => (isOpen ? <div>{message}</div> : null),
}));

function flushAsync() {
  return act(async () => {
    await Promise.resolve();
  });
}

async function advance(ms) {
  await act(async () => {
    jest.advanceTimersByTime(ms);
  });
  await flushAsync();
}

async function waitForFornecedorOptions() {
  await screen.findByRole('option', { name: 'Fornecedor 1' });
}

describe('ProductEditModal', () => {
  const onClose = jest.fn();
  const onProductUpdated = jest.fn();
  const onOpenContentView = jest.fn();
  let user;

  const baseProduct = {
    id: 10,
    nome_base: 'Produto Base',
    fornecedor_id: 1,
    product_type_id: 1,
    product_type: { id: 1 },
    nome_chat_api: '',
    descricao_chat_api: '',
    descricao_original: '',
    dynamic_attributes: {
      titulo: 'Titulo extraido',
      id: 'SP1081',
      descricao: 'Descricao extraida',
      cor: 'Azul',
    },
    dados_brutos_web: {},
    titulos_sugeridos: [],
    log_enriquecimento_web: { historico_mensagens: [] },
    status_enriquecimento_web: 'NAO_INICIADO',
    status_titulo_ia: 'NAO_INICIADO',
    status_descricao_ia: 'NAO_INICIADO',
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    useProductTypes.mockReturnValue({
      productTypes: mockProductTypes,
      addProductType: jest.fn(),
    });

    productService.getProdutoById.mockResolvedValue(baseProduct);
    productService.createProduto.mockResolvedValue({
      ...baseProduct,
      id: 101,
      nome_base: 'Produto novo',
    });
    productService.updateProduto.mockResolvedValue(baseProduct);
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  function renderModal(props = {}) {
    return render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        showAiFeatures={false}
        {...props}
      />
    );
  }

  async function proceedToCreateForm() {
    await waitForFornecedorOptions();
    await user.selectOptions(screen.getByRole('combobox', { name: /Fornecedor/i }), '1');
    await user.selectOptions(screen.getByRole('combobox', { name: /Tipo de Produto/i }), '1');
    await screen.findByLabelText(/Nome Base/i);
  }

  test('initializes template attributes once supplier and type are selected in create mode', async () => {
    renderModal({ product: null });

    expect(screen.queryByLabelText(/Nome Base/i)).not.toBeInTheDocument();

    await proceedToCreateForm();
    await user.click(screen.getByRole('button', { name: /Atributos/i }));

    expect(screen.getByLabelText(/^Cor/i)).toHaveValue('Preta');
    expect(screen.getByLabelText(/^Voltagem/i)).toHaveValue('');
  });

  test('opens the new type modal and applies the created type in the stage flow', async () => {
    renderModal({ product: null });

    await waitForFornecedorOptions();
    await user.selectOptions(screen.getByRole('combobox', { name: /Fornecedor/i }), '1');

    await user.click(screen.getByRole('button', { name: /\+ Novo Tipo/i }));
    expect(screen.getByTestId('new-product-type-modal')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /complete-new-type/i }));

    expect(screen.getByRole('combobox', { name: /Tipo de Produto/i })).toHaveValue('2');

    expect(await screen.findByLabelText(/Nome Base/i)).toBeInTheDocument();
  });

  test('creates a product with normalized ids and template data', async () => {
    renderModal({ product: null });

    await proceedToCreateForm();

    await user.clear(screen.getByLabelText(/Nome Base/i));
    await user.type(screen.getByLabelText(/Nome Base/i), 'Produto novo');
    await user.type(screen.getByLabelText(/Marca/i), 'Marca X');
    await user.type(screen.getByLabelText(/SKU/i), 'SKU-900');

    await user.click(screen.getByRole('button', { name: /Salvar Produto/i }));

    await waitFor(() => {
      expect(productService.createProduto).toHaveBeenCalledWith(
        expect.objectContaining({
          nome_base: 'Produto novo',
          marca: 'Marca X',
          sku: 'SKU-900',
          fornecedor_id: 1,
          product_type_id: 1,
          dynamic_attributes: expect.objectContaining({
            cor: 'Preta',
            voltagem: '',
          }),
        })
      );
    });

    expect(onProductUpdated).toHaveBeenCalledWith(
      expect.objectContaining({ id: 101, nome_base: 'Produto novo' })
    );
    expect(onClose).toHaveBeenCalled();
  });

  test('maps alias dynamic attributes to template keys when product payload lacks templates', async () => {
    renderModal({ product: { id: 10 } });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(await screen.findByRole('button', { name: /Atributos/i }));
    await flushAsync();

    expect(await screen.findByLabelText(/^Titulo/i)).toHaveValue('Titulo extraido');
    expect(screen.getByLabelText(/^ID/i)).toHaveValue('SP1081');
    expect(screen.getByLabelText(/^Descricao/i)).toHaveValue('Descricao extraida');
  });

  test('opens the dedicated content view from an existing product', async () => {
    renderModal({ product: { id: 10 } });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(
      screen.getByRole('button', { name: /Tela Dedicada/i })
    );

    expect(onClose).toHaveBeenCalled();
    expect(onOpenContentView).toHaveBeenCalledWith(10);
  });

  test('refreshes generated titles and descriptions without mixing both outputs', async () => {
    productService.getProdutoById
      .mockResolvedValueOnce(baseProduct)
      .mockResolvedValueOnce({
        ...baseProduct,
        titulos_sugeridos: ['Titulo 1', 'Titulo 2'],
        nome_chat_api: 'Nome IA',
      })
      .mockResolvedValueOnce({
        ...baseProduct,
        titulos_sugeridos: ['Titulo 1', 'Titulo 2'],
        descricao_chat_api: 'Descricao limpa gerada',
      });

    renderModal({ product: { id: 10 } });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));

    await user.click(screen.getByRole('button', { name: /Gerar T/i }));
    await waitFor(() => {
      expect(productService.gerarTitulosProdutoModoBasico).toHaveBeenCalledWith(10);
    });
    await advance(7000);

    expect(await screen.findByText('Titulo 1')).toBeInTheDocument();
    expect(screen.getByText('Titulo 2')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Gerar D/i }));
    await waitFor(() => {
      expect(productService.gerarDescricaoProdutoModoBasico).toHaveBeenCalledWith(10);
    });
    await advance(7000);

    expect(await screen.findByDisplayValue('Descricao limpa gerada')).toBeInTheDocument();
    expect(screen.getByText('Titulo 1')).toBeInTheDocument();
    expect(screen.getByText('Titulo 2')).toBeInTheDocument();
    expect(showInfoToast.mock.calls.map((call) => call[0]).join(' ')).toMatch(/modo b.sico/i);
  });

  test('polls web enrichment until terminal status and updates product data', async () => {
    productService.getProdutoById
      .mockResolvedValueOnce(baseProduct)
      .mockResolvedValueOnce({
        ...baseProduct,
        status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
        descricao_original: 'Ficha limpa do produto',
        log_enriquecimento_web: {
          historico_mensagens: ['Fonte aplicada com sucesso'],
          resumo_aplicacao: { aplicados_total: 2, ignorados_total: 1 },
        },
      });

    renderModal({ product: { id: 10 } });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(10);
    });

    await flushAsync();

    await waitFor(() => {
      expect(onProductUpdated).toHaveBeenCalledWith(
        expect.objectContaining({
          status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
          descricao_original: 'Ficha limpa do produto',
        })
      );
    });

    await user.click(screen.getByRole('button', { name: /^Log$/i }));
    expect(await screen.findByText(/Fonte aplicada com sucesso/i)).toBeInTheDocument();
    expect(showSuccessToast).toHaveBeenCalledWith(
      'Enriquecimento finalizado (CONCLUIDO_SUCESSO). Aplicados: 2. Ignorados: 1.'
    );
  });

  test('fetchGeminiSuggestions does not crash when API returns empty object', async () => {
    render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        product={{ id: 10 }}
        showAiFeatures={true}
      />
    );

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Sugest/i }));
    const button = screen.getByRole('button', { name: /Buscar Sugest/i });
    await user.click(button);

    await waitFor(() => {
      expect(productService.getAtributoSuggestions).toHaveBeenCalledWith(10);
    });
    await waitFor(() => {
      expect(button).not.toBeDisabled();
    });
  });

  test('warns when trying to add a duplicated manual attribute key', async () => {
    renderModal({ product: null });

    await proceedToCreateForm();
    await user.click(screen.getByRole('button', { name: /Atributos/i }));

    await user.type(screen.getByPlaceholderText(/Nova chave/i), 'cor');
    await user.click(screen.getByRole('button', { name: /Adicionar Atributo Manual/i }));

    expect(showWarningToast).toHaveBeenCalled();
    expect(showWarningToast.mock.calls.at(-1)[0]).toMatch(/Atributo com esta chave/i);
  });
});
