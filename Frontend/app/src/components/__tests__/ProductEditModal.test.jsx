import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ProductEditModal from '../ProductEditModal.jsx';
import {
  coerceFormFieldValue,
  extractGeneratedTitles,
  normalizeDynamicAttrsToTemplateKeys,
} from '../ProductEditModal.helpers.js';
import productService from '../../services/productService';
import fornecedorService from '../../services/fornecedorService';
import { useProductTypes } from '../../contexts/ProductTypeContext';
import {
  showErrorToast,
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

function createDeferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
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

test('coerceFormFieldValue normalizes comma separated urls, checkboxes and plain values', () => {
  expect(
    coerceFormFieldValue(
      'imagens_secundarias_urls',
      ' https://a.example , , https://b.example ',
      'text',
      false
    )
  ).toEqual(['https://a.example', 'https://b.example']);
  expect(coerceFormFieldValue('ativo_marketplace', 'ignored', 'checkbox', true)).toBe(true);
  expect(coerceFormFieldValue('nome_base', 'Produto X', 'text', false)).toBe('Produto X');
});

test('extractGeneratedTitles and normalizeDynamicAttrsToTemplateKeys sanitize helper data', () => {
  expect(
    extractGeneratedTitles({
      titulos_sugeridos: ['Titulo A', 'Titulo B'],
      dados_brutos_web: { titulos_sugeridos_gerados: ['titulo a', 'Titulo C', ''] },
    })
  ).toEqual(['Titulo A', 'Titulo B', 'Titulo C']);

  expect(
    normalizeDynamicAttrsToTemplateKeys(
      {
        Titulo: 'Titulo bruto',
        Codigo_original: 'REF-100',
        desc_auto: 'Descricao limpa',
      },
      [
        { attribute_key: 'titulo_auto', label: 'Titulo SEO' },
        { attribute_key: 'referencia', label: 'Codigo' },
        { attribute_key: 'descricao_longa', label: 'Descricao' },
      ]
    )
  ).toEqual(
    expect.objectContaining({
      titulo_auto: 'Titulo bruto',
      referencia: 'REF-100',
      descricao_longa: 'Descricao limpa',
    })
  );

  expect(
    normalizeDynamicAttrsToTemplateKeys(
      { referencia: 'REF-200', inutil: 'valor' },
      [
        { attribute_key: 'referencia', label: 'Codigo' },
        { attribute_key: null, label: 'Ignorar' },
      ]
    )
  ).toEqual(
    expect.objectContaining({
      referencia: 'REF-200',
      inutil: 'valor',
    })
  );

  expect(
    extractGeneratedTitles({
      titulos_sugeridos: Array.from({ length: 12 }, (_, index) => `Titulo ${index}`),
      dados_brutos_web: {},
    })
  ).toHaveLength(10);

  expect(
    normalizeDynamicAttrsToTemplateKeys(
      {
        descricao_longa: 'Ja preenchido',
        descricao_bruta: '   ',
        codigo_original: '-',
      },
      [{ attribute_key: 'descricao_longa', label: '' }]
    )
  ).toEqual(
    expect.objectContaining({
      descricao_longa: 'Ja preenchido',
      descricao_bruta: '   ',
      codigo_original: '-',
    })
  );
});

describe('ProductEditModal', () => {
  const onClose = jest.fn();
  const onProductUpdated = jest.fn();
  const onOpenContentView = jest.fn();
  let user;
  let consoleErrorSpy;
  let consoleWarnSpy;

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
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});

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
    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();
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
    renderModal({ product: baseProduct });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(await screen.findByRole('button', { name: /Atributos/i }));
    await flushAsync();

    expect(await screen.findByLabelText(/^Titulo/i)).toHaveValue('Titulo extraido');
    expect(screen.getByLabelText(/^ID/i)).toHaveValue('SP1081');
    expect(screen.getByLabelText(/^Descricao/i)).toHaveValue('Descricao extraida');
  });

  test('falls back to partial product data when full product loading fails', async () => {
    productService.getProdutoById.mockRejectedValueOnce(new Error('falha no carregamento'));

    renderModal({
      product: {
        id: 10,
        nome_base: 'Parcial',
        fornecedor_id: 1,
        product_type_id: 1,
        dynamic_attributes: {},
      },
    });

    expect(await screen.findByDisplayValue('Parcial')).toBeInTheDocument();
    expect(showErrorToast).toHaveBeenCalledWith('Erro ao carregar dados completos do produto.');
    expect(showWarningToast).toHaveBeenCalledWith('Dados carregados parcialmente.');
  });

  test('keeps the form usable when the backend returns an empty full-product payload', async () => {
    productService.getProdutoById.mockResolvedValueOnce(null);

    renderModal({ product: { id: 10 } });

    expect(await screen.findByLabelText(/Fornecedor/i)).toHaveValue('');
    expect(screen.getByRole('button', { name: /Salvar Produto/i })).toBeInTheDocument();
  });

  test('fetches the supplier by id when it is missing from the initial dependency list', async () => {
    fornecedorService.getFornecedores.mockResolvedValueOnce({ items: [fornecedores[1]] });
    fornecedorService.getFornecedorById.mockResolvedValueOnce({
      id: 1,
      nome: 'Fornecedor 1 (fallback)',
      site_url: 'https://fornecedor-1.example',
    });

    renderModal({
      product: {
        id: 10,
        nome_base: 'Produto Base',
        fornecedor_id: 1,
        product_type_id: 1,
      },
    });

    await screen.findByDisplayValue('Produto Base');
    expect(fornecedorService.getFornecedorById).toHaveBeenCalledWith(1);
    expect(screen.getAllByRole('option', { name: /Fornecedor 1/i }).length).toBeGreaterThan(0);
  });

  test('logs supplier fallback lookup errors without breaking the modal', async () => {
    fornecedorService.getFornecedores.mockResolvedValueOnce({ items: [fornecedores[1]] });
    fornecedorService.getFornecedorById.mockRejectedValueOnce(new Error('falha fornecedor fallback'));

    renderModal({
      product: {
        id: 10,
        nome_base: 'Produto Base',
        fornecedor_id: 1,
        product_type_id: 1,
      },
    });

    expect(await screen.findByDisplayValue('Produto Base')).toBeInTheDocument();
    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Erro ao buscar fornecedor pelo ID:',
      expect.any(Error)
    );
  });

  test('shows an error toast when supplier dependencies cannot be loaded', async () => {
    fornecedorService.getFornecedores.mockRejectedValueOnce(new Error('falha fornecedores'));

    renderModal({ product: null });

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro ao carregar lista de fornecedores para o modal.'
      );
    });
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

  test('keeps generation and content actions disabled until the product is saved', async () => {
    renderModal({ product: null });

    await proceedToCreateForm();
    await user.click(screen.getByRole('button', { name: /^Conteúdo$/i }));

    const contentViewButton = screen.getByRole('button', { name: /Tela Dedicada/i });
    const enrichButton = screen.getByRole('button', { name: /Enriquecer Web/i });
    const titlesButton = screen.getByRole('button', { name: /Gerar Títulos/i });
    const descriptionButton = screen.getByRole('button', { name: /Gerar Descrição/i });

    expect(contentViewButton).toBeDisabled();
    expect(enrichButton).toBeDisabled();
    expect(titlesButton).toBeDisabled();
    expect(descriptionButton).toBeDisabled();
  });

  test('falls back to window navigation when no dedicated content handler is provided', async () => {
    render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Tela Dedicada/i }));

    expect(onClose).toHaveBeenCalled();
    expect(
      consoleErrorSpy.mock.calls.some((call) =>
        call.some((item) => String(item).includes('Not implemented: navigation'))
      )
    ).toBe(true);
  });

  test('shows validation and persistence errors when saving fails', async () => {
    productService.updateProduto.mockRejectedValueOnce({
      response: { data: { detail: 'falha ao salvar' } },
    });

    renderModal({ product: { id: 10 } });

    const nameInput = await screen.findByLabelText(/Nome Base/i);
    await user.clear(nameInput);
    fireEvent.submit(screen.getByRole('button', { name: /Salvar Produto/i }).closest('form'));

    expect(showErrorToast).toHaveBeenCalledWith('O nome base do produto é obrigatório.');

    await user.type(nameInput, 'Produto Atualizado');
    await user.click(screen.getByRole('button', { name: /Salvar Produto/i }));

    await waitFor(() => {
      expect(productService.updateProduto).toHaveBeenCalledWith(
        10,
        expect.objectContaining({ nome_base: 'Produto Atualizado' })
      );
    });
    expect(showErrorToast).toHaveBeenCalledWith('falha ao salvar');
  });

  test('updates an existing product successfully and closes the modal', async () => {
    productService.updateProduto.mockResolvedValueOnce({
      ...baseProduct,
      nome_base: 'Produto Atualizado',
      marca: 'Marca Final',
    });

    renderModal({ product: { id: 10 } });

    const nameInput = await screen.findByLabelText(/Nome Base/i);
    await user.clear(nameInput);
    await user.type(nameInput, 'Produto Atualizado');
    await user.type(screen.getByLabelText(/Marca/i), 'Marca Final');

    await user.click(screen.getByRole('button', { name: /Salvar Produto/i }));

    await waitFor(() => {
      expect(productService.updateProduto).toHaveBeenCalledWith(
        10,
        expect.objectContaining({
          nome_base: 'Produto Atualizado',
          marca: 'Marca Final',
        })
      );
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Produto atualizado com sucesso!');
    expect(onProductUpdated).toHaveBeenCalledWith(
      expect.objectContaining({
        nome_base: 'Produto Atualizado',
        marca: 'Marca Final',
      })
    );
    expect(onClose).toHaveBeenCalled();
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

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Gerar Descri/i })).toBeEnabled();
    });
    await user.click(screen.getByRole('button', { name: /Gerar Descri/i }));
    await waitFor(() => {
      expect(productService.gerarDescricaoProdutoModoBasico).toHaveBeenCalledWith(10);
    });
    await advance(7000);

    expect(await screen.findByDisplayValue('Descricao limpa gerada')).toBeInTheDocument();
    expect(screen.getByText('Titulo 1')).toBeInTheDocument();
    expect(screen.getByText('Titulo 2')).toBeInTheDocument();
    expect(showInfoToast.mock.calls.map((call) => call[0]).join(' ')).toMatch(/modo b.sico/i);
  });

  test('uses AI generation endpoints when AI features are enabled', async () => {
    productService.getProdutoById
      .mockResolvedValueOnce(baseProduct)
      .mockResolvedValueOnce({
        ...baseProduct,
        titulos_sugeridos: ['Titulo IA'],
        nome_chat_api: 'Nome IA',
      })
      .mockResolvedValueOnce({
        ...baseProduct,
        titulos_sugeridos: ['Titulo IA'],
        descricao_chat_api: 'Descricao IA gerada',
      });

    render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={true}
      />
    );

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));

    await user.click(screen.getByRole('button', { name: /Gerar T/i }));
    await waitFor(() => {
      expect(productService.gerarTitulosProduto).toHaveBeenCalledWith(10);
    });
    await advance(7000);

    await user.click(screen.getByRole('button', { name: /Gerar D/i }));
    await waitFor(() => {
      expect(productService.gerarDescricaoProduto).toHaveBeenCalledWith(10);
    });
    await advance(7000);

    expect(await screen.findByText('Titulo IA')).toBeInTheDocument();
    expect(await screen.findByDisplayValue('Descricao IA gerada')).toBeInTheDocument();
    expect(showInfoToast).toHaveBeenCalledWith('Geração de títulos iniciada. Verifique em breve.');
    expect(showInfoToast).toHaveBeenCalledWith('Geração de descrição iniciada. Verifique em breve.');
  });

  test('shows refresh errors after generation when post-processing fetch fails', async () => {
    productService.getProdutoById
      .mockResolvedValueOnce(baseProduct)
      .mockRejectedValueOnce(new Error('falha no refresh de titulos'))
      .mockRejectedValueOnce(new Error('falha no refresh de descricao'));

    renderModal({ product: baseProduct });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));

    await user.click(screen.getByRole('button', { name: /Gerar T/i }));
    await waitFor(() => {
      expect(productService.gerarTitulosProdutoModoBasico).toHaveBeenCalledWith(10);
    });
    await advance(7000);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Gerar Descri/i })).toBeEnabled();
    });
    await user.click(screen.getByRole('button', { name: /Gerar Descri/i }));
    await waitFor(() => {
      expect(productService.gerarDescricaoProdutoModoBasico).toHaveBeenCalledWith(10);
    });
    await advance(7000);

    expect(showErrorToast).toHaveBeenCalledWith(
      'Nao foi possivel atualizar os titulos gerados.'
    );
    expect(showErrorToast).toHaveBeenCalledWith(
      'Nao foi possivel atualizar a descricao gerada.'
    );
  });

  test('shows direct generation errors for titles and descriptions', async () => {
    productService.gerarTitulosProdutoModoBasico.mockRejectedValueOnce({
      response: { data: { detail: 'erro titulos' } },
    });
    productService.gerarDescricaoProdutoModoBasico.mockRejectedValueOnce({
      response: { data: { detail: 'erro descricao' } },
    });

    renderModal({ product: baseProduct });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));

    await user.click(screen.getByRole('button', { name: /Gerar T/i }));
    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('erro titulos');
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Gerar Descrição/i })).toBeEnabled();
    });
    await user.click(screen.getByRole('button', { name: /Gerar Descrição/i }));
    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('erro descricao');
    });
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

  test('shows enrichment start errors without breaking the modal state', async () => {
    productService.iniciarEnriquecimentoWebProduto.mockRejectedValueOnce(
      new Error('servico indisponivel')
    );

    renderModal({ product: { id: 10 } });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('servico indisponivel');
    });
  });

  test('reads enrichment start errors from backend msg payloads', async () => {
    productService.iniciarEnriquecimentoWebProduto.mockRejectedValueOnce({
      response: { data: { msg: 'falha via payload msg' } },
    });

    renderModal({ product: { id: 10 } });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('falha via payload msg');
    });
  });

  test('reads enrichment start errors from backend detail payloads', async () => {
    productService.iniciarEnriquecimentoWebProduto.mockRejectedValueOnce({
      response: { data: { detail: 'falha via payload detail' } },
    });

    renderModal({ product: { id: 10 } });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('falha via payload detail');
    });
  });

  test('reads enrichment start errors from direct detail payloads', async () => {
    productService.iniciarEnriquecimentoWebProduto.mockRejectedValueOnce({
      detail: 'falha via detail direta',
    });

    renderModal({ product: { id: 10 } });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('falha via detail direta');
    });
  });

  test('uses the generic enrichment start fallback when the backend returns no detail', async () => {
    productService.iniciarEnriquecimentoWebProduto.mockRejectedValueOnce({});

    renderModal({ product: { id: 10 } });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Erro ao iniciar enriquecimento web.');
    });
  });

  test('uses the generic enrichment start fallback when the service rejects with null', async () => {
    productService.iniciarEnriquecimentoWebProduto.mockRejectedValueOnce(null);

    renderModal({ product: { id: 10 } });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Erro ao iniciar enriquecimento web.');
    });
  });

  test('warns when web enrichment keeps running after the polling window', async () => {
    productService.getProdutoById
      .mockResolvedValueOnce(baseProduct)
      .mockImplementation(() =>
        Promise.resolve({
          ...baseProduct,
          status_enriquecimento_web: 'EM_PROGRESSO',
        })
      );

    renderModal({ product: { id: 10 } });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(10);
    });

    for (let i = 0; i < 40; i += 1) {
      await advance(3000);
    }

    await waitFor(() => {
      expect(showWarningToast).toHaveBeenCalledWith(
        'O enriquecimento continua em segundo plano. Reabra o produto em instantes para ver o resultado final.'
      );
    });
  }, 15000);

  test('stops the next enrichment polling iteration when the modal closes', async () => {
    const { rerender } = render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(10);
    });
    await waitFor(() => {
      expect(productService.getProdutoById).toHaveBeenCalledTimes(2);
    });

    rerender(
      <ProductEditModal
        isOpen={false}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await advance(3000);

    expect(productService.getProdutoById).toHaveBeenCalledTimes(2);
  });

  test('aborts enrichment completion updates when the modal closes before polling resolves', async () => {
    const pollingRequest = createDeferred();
    productService.getProdutoById
      .mockResolvedValueOnce(baseProduct)
      .mockImplementationOnce(() => pollingRequest.promise);

    const { rerender } = render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(10);
    });

    rerender(
      <ProductEditModal
        isOpen={false}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await act(async () => {
      pollingRequest.resolve({
        ...baseProduct,
        status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
        descricao_original: 'Descricao tardia de enrichment',
      });
      await Promise.resolve();
    });

    expect(onProductUpdated).not.toHaveBeenCalledWith(
      expect.objectContaining({ descricao_original: 'Descricao tardia de enrichment' })
    );
    expect(showSuccessToast).not.toHaveBeenCalledWith(
      'Enriquecimento finalizado (CONCLUIDO_SUCESSO). Aplicados: 0. Ignorados: 0.'
    );
  });

  test('ignores enrichment polling errors that arrive after the modal closes', async () => {
    const pollingRequest = createDeferred();
    productService.getProdutoById
      .mockResolvedValueOnce(baseProduct)
      .mockImplementationOnce(() => pollingRequest.promise);

    const { rerender } = render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(10);
    });

    rerender(
      <ProductEditModal
        isOpen={false}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await act(async () => {
      pollingRequest.reject(new Error('falha tardia enrichment'));
      await Promise.resolve();
    });

    expect(consoleWarnSpy).not.toHaveBeenCalledWith(
      'Falha ao consultar status de enriquecimento web:',
      expect.any(Error)
    );
  });

  test('abandons the enrichment workflow when the start command resolves after the modal closes', async () => {
    const startRequest = createDeferred();
    productService.iniciarEnriquecimentoWebProduto.mockImplementationOnce(() => startRequest.promise);

    const { rerender } = render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(10);
    });

    rerender(
      <ProductEditModal
        isOpen={false}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await act(async () => {
      startRequest.resolve({});
      await Promise.resolve();
    });

    expect(showSuccessToast).not.toHaveBeenCalledWith(
      'Comando de enriquecimento enviado. Atualizando status do produto em segundo plano.'
    );
  });

  test('recovers from transient polling errors while tracking web enrichment', async () => {
    productService.getProdutoById
      .mockResolvedValueOnce(baseProduct)
      .mockRejectedValueOnce(new Error('falha temporaria no polling'))
      .mockResolvedValueOnce({
        ...baseProduct,
        status_enriquecimento_web: 'CONCLUIDO_COM_DADOS_PARCIAIS',
        log_enriquecimento_web: {
          historico_mensagens: ['Retomado com sucesso'],
          resumo_aplicacao: { aplicados_total: 1, ignorados_total: 2 },
        },
      });

    renderModal({ product: { id: 10 } });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(10);
    });

    await advance(3000);

    await waitFor(() => {
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Falha ao consultar status de enriquecimento web:',
        expect.any(Error)
      );
    });
    await waitFor(() => {
      expect(showSuccessToast).toHaveBeenCalledWith(
        'Enriquecimento finalizado (CONCLUIDO_COM_DADOS_PARCIAIS). Aplicados: 1. Ignorados: 2.'
      );
    });
  });

  test('warns when web enrichment finishes with a non-success terminal status', async () => {
    productService.getProdutoById
      .mockResolvedValueOnce(baseProduct)
      .mockResolvedValueOnce({
        ...baseProduct,
        status_enriquecimento_web: 'FALHA',
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
      expect(showWarningToast).toHaveBeenCalledWith(
        'Enriquecimento finalizado com status FALHA.'
      );
    });
  });

  test('logs unexpected enrichment completion errors without breaking the modal', async () => {
    productService.getProdutoById
      .mockResolvedValueOnce(baseProduct)
      .mockResolvedValueOnce({
        ...baseProduct,
        status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
      });
    showSuccessToast.mockImplementationOnce(() => {});
    showSuccessToast.mockImplementationOnce(() => {
      throw new Error('falha no toast final');
    });

    render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(10);
    });

    await flushAsync();

    expect(consoleWarnSpy).toHaveBeenCalledWith(
      'Falha ao acompanhar status de enriquecimento web:',
      expect.any(Error)
    );
  });

  test('clears pending title and description refreshes when the modal closes', async () => {
    const { rerender } = render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));

    await user.click(screen.getByRole('button', { name: /Gerar T/i }));
    await waitFor(() => {
      expect(productService.gerarTitulosProdutoModoBasico).toHaveBeenCalledWith(10);
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Gerar Descri/i })).toBeEnabled();
    });
    await user.click(screen.getByRole('button', { name: /Gerar Descri/i }));
    await waitFor(() => {
      expect(productService.gerarDescricaoProdutoModoBasico).toHaveBeenCalledWith(10);
    });

    rerender(
      <ProductEditModal
        isOpen={false}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await advance(8000);

    expect(productService.getProdutoById).toHaveBeenCalledTimes(1);
  });

  test('fetchGeminiSuggestions does not crash when API returns empty object', async () => {
    productService.getAtributoSuggestions.mockResolvedValueOnce({});

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
    expect(showInfoToast).toHaveBeenCalledWith(
      'Nenhuma sugestão de atributo específica retornada pela IA (Gemini).'
    );
  });

  test('hydrates IA suggestions from raw specs and returns to info when AI suggestions are hidden', async () => {
    productService.getProdutoById.mockResolvedValueOnce({
      ...baseProduct,
      dados_brutos_web: {
        especificacoes_tecnicas_dict: {
          Potencia: '200W',
          Voltagem: '220V',
        },
      },
    });

    const { rerender } = render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={true}
      />
    );

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Sugest/i }));

    expect(await screen.findByText(/Potencia:/i)).toBeInTheDocument();
    expect(screen.getByText(/Voltagem:/i)).toBeInTheDocument();
    expect(screen.getAllByRole('checkbox')[0]).not.toBeChecked();

    rerender(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /Buscar Sugest/i })).not.toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /Info Principais/i })).toHaveClass('active');
  });

  test('loads Gemini suggestions, warns when none are selected and applies selected values', async () => {
    productService.getAtributoSuggestions.mockResolvedValueOnce({
      sugestoes_atributos: [
        { chave_atributo: 'material', valor_sugerido: 'Aluminio' },
        { chave_atributo: 'acabamento', valor_sugerido: 'Escovado' },
      ],
    });

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
    await user.click(screen.getByRole('button', { name: /Buscar Sugest/i }));

    expect(await screen.findByText(/material:/i)).toBeInTheDocument();
    expect(showSuccessToast).toHaveBeenCalledWith('Sugestões da IA (Gemini) carregadas!');

    await user.click(screen.getByRole('button', { name: /Aplicar Selecionados/i }));
    expect(showWarningToast).toHaveBeenCalledWith('Nenhuma sugestão selecionada para aplicar.');

    await user.click(screen.getAllByRole('checkbox')[0]);
    await user.click(screen.getByRole('button', { name: /Aplicar Selecionados/i }));

    expect(showSuccessToast).toHaveBeenCalledWith(
      '1 sugestão aplicada aos atributos dinâmicos!'
    );
    expect(await screen.findByDisplayValue('material')).toBeInTheDocument();
  });

  test('handles Gemini suggestion errors and clears stale suggestions', async () => {
    productService.getAtributoSuggestions.mockRejectedValueOnce(
      new Error('falha gemini')
    );

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
    await user.click(screen.getByRole('button', { name: /Buscar Sugest/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('falha gemini');
    });
  });

  test('keeps Gemini suggestions disabled until the product is saved', async () => {
    render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        product={null}
        showAiFeatures={true}
      />
    );

    await proceedToCreateForm();
    await user.click(screen.getByRole('button', { name: /Sugestões IA/i }));

    const fetchSuggestionsButton = screen.getByRole('button', { name: /Buscar Sugestões/i });
    expect(fetchSuggestionsButton).toBeDisabled();
  });

  test('renders normalized log summaries and the empty log state', async () => {
    productService.getProdutoById.mockResolvedValueOnce({
      ...baseProduct,
      log_enriquecimento_web: {
        historico_mensagens: [],
        resumo_aplicacao: {
          aplicados: ['marca'],
          ignorados: ['sku'],
          campos_alterados_detalhe: ['Descri??o atualizada'],
        },
      },
    });

    renderModal({ product: { id: 10 } });

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /^Log$/i }));

    expect(screen.getByText(/Campos aplicados:/i).parentElement).toHaveTextContent('marca');
    expect(screen.getByText(/Campos ignorados:/i).parentElement).toHaveTextContent('sku');
    expect(screen.getByText('Descrição atualizada')).toBeInTheDocument();
    expect(screen.getByText('Nenhum log disponível.')).toBeInTheDocument();
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

  test('adds and removes a manual attribute while keeping the form in sync', async () => {
    renderModal({ product: null });

    await proceedToCreateForm();
    await user.click(screen.getByRole('button', { name: /Atributos/i }));

    await user.type(screen.getByPlaceholderText(/Nova chave/i), 'acabamento_manual');
    await user.click(screen.getByRole('button', { name: /Adicionar Atributo Manual/i }));

    expect(await screen.findByDisplayValue('acabamento_manual')).toBeInTheDocument();

    await user.click(screen.getByTitle(/Remover este atributo manual/i));

    expect(showInfoToast).toHaveBeenCalledWith(
      'Atributo manual "acabamento_manual" removido.'
    );
    expect(screen.queryByDisplayValue('acabamento_manual')).not.toBeInTheDocument();
  });

  test('updates manual attribute values and switches between media and info tabs', async () => {
    renderModal({ product: null });

    await proceedToCreateForm();
    await user.click(screen.getByRole('button', { name: /Atributos/i }));
    await user.type(screen.getByPlaceholderText(/Nova chave/i), 'acabamento_manual');
    await user.click(screen.getByRole('button', { name: /Adicionar Atributo Manual/i }));

    const manualKeyInput = await screen.findByDisplayValue('acabamento_manual');
    const manualValueInput = manualKeyInput.closest('div').querySelectorAll('input')[1];
    await user.type(manualValueInput, 'Escovado');
    expect(screen.getByDisplayValue('Escovado')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /M.dia/i }));
    const imageInput = screen.getByLabelText(/URL Imagem Principal/i);
    await user.type(imageInput, 'https://cdn.example/imagem-principal.png');
    expect(await screen.findByAltText(/Principal/i)).toHaveAttribute(
      'src',
      'https://cdn.example/imagem-principal.png'
    );

    await user.click(screen.getByRole('button', { name: /Info Principais/i }));
    expect(screen.getByRole('button', { name: /Info Principais/i })).toHaveClass('active');
  });

  test('ignores a successful late title refresh after the modal closes', async () => {
    const titleRefresh = createDeferred();
    productService.getProdutoById
      .mockResolvedValueOnce(baseProduct)
      .mockImplementationOnce(() => titleRefresh.promise);

    const { rerender } = render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Gerar T/i }));
    await waitFor(() => {
      expect(productService.gerarTitulosProdutoModoBasico).toHaveBeenCalledWith(10);
    });
    await advance(7000);

    rerender(
      <ProductEditModal
        isOpen={false}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await act(async () => {
      titleRefresh.resolve({
        ...baseProduct,
        titulos_sugeridos: ['Titulo tardio'],
      });
      await Promise.resolve();
    });

    expect(onProductUpdated).not.toHaveBeenCalledWith(
      expect.objectContaining({ titulos_sugeridos: ['Titulo tardio'] })
    );
    expect(showErrorToast).not.toHaveBeenCalledWith(
      'Nao foi possivel atualizar os titulos gerados.'
    );
  });

  test('ignores a failed late title refresh after the modal closes', async () => {
    const titleRefresh = createDeferred();
    productService.getProdutoById
      .mockResolvedValueOnce(baseProduct)
      .mockImplementationOnce(() => titleRefresh.promise);

    const { rerender } = render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Gerar T/i }));
    await waitFor(() => {
      expect(productService.gerarTitulosProdutoModoBasico).toHaveBeenCalledWith(10);
    });
    await advance(7000);

    rerender(
      <ProductEditModal
        isOpen={false}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await act(async () => {
      titleRefresh.reject(new Error('falha tardia titulos'));
      await Promise.resolve();
    });

    expect(showErrorToast).not.toHaveBeenCalledWith(
      'Nao foi possivel atualizar os titulos gerados.'
    );
  });

  test('ignores a successful late description refresh after the modal closes', async () => {
    const descriptionRefresh = createDeferred();
    productService.getProdutoById
      .mockResolvedValueOnce(baseProduct)
      .mockImplementationOnce(() => descriptionRefresh.promise);

    const { rerender } = render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Gerar Descri/i }));
    await waitFor(() => {
      expect(productService.gerarDescricaoProdutoModoBasico).toHaveBeenCalledWith(10);
    });
    await advance(7000);

    rerender(
      <ProductEditModal
        isOpen={false}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await act(async () => {
      descriptionRefresh.resolve({
        ...baseProduct,
        descricao_chat_api: 'Descricao tardia',
      });
      await Promise.resolve();
    });

    expect(onProductUpdated).not.toHaveBeenCalledWith(
      expect.objectContaining({ descricao_chat_api: 'Descricao tardia' })
    );
    expect(showErrorToast).not.toHaveBeenCalledWith(
      'Nao foi possivel atualizar a descricao gerada.'
    );
  });

  test('ignores a failed late description refresh after the modal closes', async () => {
    const descriptionRefresh = createDeferred();
    productService.getProdutoById
      .mockResolvedValueOnce(baseProduct)
      .mockImplementationOnce(() => descriptionRefresh.promise);

    const { rerender } = render(
      <ProductEditModal
        isOpen={true}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await screen.findByLabelText(/Nome Base/i);
    await user.click(screen.getByRole('button', { name: /Conte/i }));
    await user.click(screen.getByRole('button', { name: /Gerar Descri/i }));
    await waitFor(() => {
      expect(productService.gerarDescricaoProdutoModoBasico).toHaveBeenCalledWith(10);
    });
    await advance(7000);

    rerender(
      <ProductEditModal
        isOpen={false}
        onClose={onClose}
        onProductUpdated={onProductUpdated}
        onOpenContentView={onOpenContentView}
        product={{ id: 10 }}
        showAiFeatures={false}
      />
    );

    await act(async () => {
      descriptionRefresh.reject(new Error('falha tardia descricao'));
      await Promise.resolve();
    });

    expect(showErrorToast).not.toHaveBeenCalledWith(
      'Nao foi possivel atualizar a descricao gerada.'
    );
  });
});
