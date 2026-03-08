import productService from '../productService';
import apiClient from '../apiClient';
import basicTemplateService from '../basicTemplateService';

jest.mock('../apiClient', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    put: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  },
}));

jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock('../basicTemplateService', () => ({
  __esModule: true,
  default: {
    resolveCustomTemplateForRequest: jest.fn(() => null),
  },
}));

describe('productService', () => {
  let consoleErrorSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    basicTemplateService.resolveCustomTemplateForRequest.mockReturnValue(null);
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    jest.useRealTimers();
  });

  test('getProdutos returns the API payload and forwards params', async () => {
    apiClient.get.mockResolvedValueOnce({ data: { items: [{ id: 1 }], total_items: 1 } });

    const result = await productService.getProdutos({ search: 'abc', limit: 5 });

    expect(apiClient.get).toHaveBeenCalledWith('/produtos/', {
      params: { search: 'abc', limit: 5 },
    });
    expect(result).toEqual({ items: [{ id: 1 }], total_items: 1 });
  });

  test('getProdutos rethrows backend payload when available', async () => {
    apiClient.get.mockRejectedValueOnce({ response: { data: { detail: 'boom' } } });

    await expect(productService.getProdutos()).rejects.toEqual({ detail: 'boom' });
  });

  test('getProdutos throws a fallback error when request has no response payload', async () => {
    apiClient.get.mockRejectedValueOnce(new Error('network down'));

    await expect(productService.getProdutos()).rejects.toThrow('Falha ao buscar produtos');
  });

  test('getProdutoById throws a fallback error when request has no response payload', async () => {
    apiClient.get.mockRejectedValueOnce(new Error('network down'));

    await expect(productService.getProdutoById(99)).rejects.toThrow(
      'Falha ao buscar produto 99'
    );
  });

  test('getProdutoById returns data and rethrows backend payloads when available', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: { id: 12, nome_base: 'Produto X' } })
      .mockRejectedValueOnce({ response: { data: { detail: 'nao encontrado' } } });

    await expect(productService.getProdutoById(12)).resolves.toEqual({
      id: 12,
      nome_base: 'Produto X',
    });
    await expect(productService.getProdutoById(13)).rejects.toEqual({
      detail: 'nao encontrado',
    });
  });

  test('createProduto, updateProduto and deleteProduto forward payloads to the expected endpoints', async () => {
    apiClient.post.mockResolvedValueOnce({ data: { id: 10 } });
    apiClient.put.mockResolvedValueOnce({ data: { id: 10, nome_base: 'Novo' } });
    apiClient.delete.mockResolvedValueOnce({ data: { deleted: true } });

    await expect(productService.createProduto({ nome_base: 'Teste' })).resolves.toEqual({ id: 10 });
    await expect(productService.updateProduto(10, { nome_base: 'Novo' })).resolves.toEqual({
      id: 10,
      nome_base: 'Novo',
    });
    await expect(productService.deleteProduto(10)).resolves.toEqual({ deleted: true });

    expect(apiClient.post).toHaveBeenCalledWith('/produtos/', { nome_base: 'Teste' });
    expect(apiClient.put).toHaveBeenCalledWith('/produtos/10/', { nome_base: 'Novo' });
    expect(apiClient.delete).toHaveBeenCalledWith('/produtos/10/');
  });

  test.each([
    ['createProduto', () => productService.createProduto({ nome_base: 'Teste' }), 'post', 'Falha ao criar produto'],
    ['updateProduto', () => productService.updateProduto(10, { nome_base: 'Novo' }), 'put', 'Falha ao atualizar produto 10'],
    ['deleteProduto', () => productService.deleteProduto(10), 'delete', 'Falha ao apagar produto 10'],
    ['gerarTitulosProduto', () => productService.gerarTitulosProduto(7), 'post', 'Falha ao gerar titulos'],
    ['gerarDescricaoProduto', () => productService.gerarDescricaoProduto(7), 'post', 'Falha ao gerar descricao'],
    ['gerarTitulosGemini', () => productService.gerarTitulosGemini(7), 'post', 'Falha ao gerar titulos com Gemini'],
    ['gerarDescricaoGemini', () => productService.gerarDescricaoGemini(7), 'post', 'Falha ao gerar descricao com Gemini'],
    ['gerarTitulosProdutoModoBasico', () => productService.gerarTitulosProdutoModoBasico(7), 'post', 'Falha ao gerar titulos no modo basico'],
    ['gerarDescricaoProdutoModoBasico', () => productService.gerarDescricaoProdutoModoBasico(7), 'post', 'Falha ao gerar descricao no modo basico'],
    ['batchDeleteProdutos', () => productService.batchDeleteProdutos([1, 2]), 'post', 'Falha ao apagar produtos em lote'],
    ['getAtributoSuggestions', () => productService.getAtributoSuggestions(7), 'post', 'Falha ao buscar sugestoes de atributos da IA.'],
  ])('%s throws a fallback error when the request has no response payload', async (_, call, method, expectedMessage) => {
    apiClient[method].mockRejectedValueOnce(new Error('network down'));

    await expect(call()).rejects.toThrow(expectedMessage);
  });

  test('OpenAI and Gemini generation methods call their respective endpoints', async () => {
    apiClient.post
      .mockResolvedValueOnce({ data: { ok: 'titulo-openai' } })
      .mockResolvedValueOnce({ data: { ok: 'descricao-openai' } })
      .mockResolvedValueOnce({ data: { ok: 'titulo-gemini' } })
      .mockResolvedValueOnce({ data: { ok: 'descricao-gemini' } });

    await expect(productService.gerarTitulosProduto(7)).resolves.toEqual({ ok: 'titulo-openai' });
    await expect(productService.gerarDescricaoProduto(7)).resolves.toEqual({ ok: 'descricao-openai' });
    await expect(productService.gerarTitulosGemini(7)).resolves.toEqual({ ok: 'titulo-gemini' });
    await expect(productService.gerarDescricaoGemini(7)).resolves.toEqual({ ok: 'descricao-gemini' });

    expect(apiClient.post).toHaveBeenNthCalledWith(1, '/geracao/titulos/openai/7');
    expect(apiClient.post).toHaveBeenNthCalledWith(2, '/geracao/descricao/openai/7');
    expect(apiClient.post).toHaveBeenNthCalledWith(3, '/geracao/titulos/gemini/7');
    expect(apiClient.post).toHaveBeenNthCalledWith(4, '/geracao/descricao/gemini/7');
  });

  test('gerarTitulosProdutoModoBasico calls backend basic generation endpoint', async () => {
    apiClient.post.mockResolvedValueOnce({ data: { msg: 'ok' } });

    await productService.gerarTitulosProdutoModoBasico(10);

    expect(apiClient.post).toHaveBeenCalledWith('/geracao/titulos/basico/10');
  });

  test('gerarDescricaoProdutoModoBasico calls backend basic generation endpoint', async () => {
    apiClient.post.mockResolvedValueOnce({ data: { msg: 'ok' } });

    await productService.gerarDescricaoProdutoModoBasico(22);

    expect(apiClient.post).toHaveBeenCalledWith('/geracao/descricao/basico/22');
  });

  test('gerarTitulosProdutoModoBasico sends custom template when available', async () => {
    apiClient.post.mockResolvedValueOnce({ data: { msg: 'ok' } });
    basicTemplateService.resolveCustomTemplateForRequest.mockReturnValueOnce(
      '{nome_base} {sku}'
    );

    await productService.gerarTitulosProdutoModoBasico(33);

    expect(apiClient.post).toHaveBeenCalledWith('/geracao/titulos/basico/33', null, {
      params: {
        template: '{nome_base} {sku}',
      },
    });
  });

  test('gerarDescricaoProdutoModoBasico sends custom template when available', async () => {
    apiClient.post.mockResolvedValueOnce({ data: { msg: 'ok' } });
    basicTemplateService.resolveCustomTemplateForRequest.mockReturnValueOnce(
      '{nome_base}: {descricao_original}'
    );

    await productService.gerarDescricaoProdutoModoBasico(44);

    expect(apiClient.post).toHaveBeenCalledWith('/geracao/descricao/basico/44', null, {
      params: {
        template: '{nome_base}: {descricao_original}',
      },
    });
  });

  test('iniciarEnriquecimentoWebProduto encodes termos_busca_override when provided', async () => {
    apiClient.post.mockResolvedValueOnce({ data: { ok: true } });

    const result = await productService.iniciarEnriquecimentoWebProduto(
      55,
      'ar 60 litros/mercedes'
    );

    expect(apiClient.post).toHaveBeenCalledWith(
      '/enriquecimento-web/produto/55?termos_busca_override=ar%2060%20litros%2Fmercedes'
    );
    expect(result).toEqual({ ok: true });
  });

  test('iniciarEnriquecimentoWebProduto maps 401 and 409 to user-facing errors', async () => {
    apiClient.post
      .mockRejectedValueOnce({ response: { status: 401, data: {} } })
      .mockRejectedValueOnce({
        response: { status: 409, data: { detail: 'ja existe' } },
      });

    await expect(productService.iniciarEnriquecimentoWebProduto(10)).rejects.toThrow(
      'Sessao expirada. Faca login novamente para iniciar o enriquecimento.'
    );
    await expect(productService.iniciarEnriquecimentoWebProduto(10)).rejects.toThrow(
      'ja existe'
    );
  });

  test('iniciarEnriquecimentoWebProduto uses the generic 409 fallback when detail is missing', async () => {
    apiClient.post.mockRejectedValueOnce({
      response: { status: 409, data: {} },
    });

    await expect(productService.iniciarEnriquecimentoWebProduto(10)).rejects.toThrow(
      'Ja existe enriquecimento em andamento para este produto.'
    );
  });

  test('iniciarEnriquecimentoWebProduto falls back to a generic error detail', async () => {
    apiClient.post.mockRejectedValueOnce({
      response: {
        status: 500,
        data: { message: 'falhou geral' },
      },
    });

    await expect(productService.iniciarEnriquecimentoWebProduto(10)).rejects.toThrow(
      'falhou geral'
    );
  });

  test('iniciarEnriquecimentoWebProduto uses msg or a generic fallback when response data is sparse', async () => {
    apiClient.post
      .mockRejectedValueOnce({
        response: {
          status: 500,
          data: { msg: 'provedor fora' },
        },
      })
      .mockRejectedValueOnce({});

    await expect(productService.iniciarEnriquecimentoWebProduto(10)).rejects.toThrow(
      'provedor fora'
    );
    await expect(productService.iniciarEnriquecimentoWebProduto(10)).rejects.toThrow(
      'Falha ao iniciar processo de enriquecimento web'
    );
  });

  test('batchDeleteProdutos posts the selected ids', async () => {
    apiClient.post.mockResolvedValueOnce({ data: { deleted: 2 } });

    const result = await productService.batchDeleteProdutos([1, 2]);

    expect(apiClient.post).toHaveBeenCalledWith('/produtos/batch-delete/', [1, 2]);
    expect(result).toEqual({ deleted: 2 });
  });

  test('getAtributoSuggestions and alias call the Gemini suggestion endpoint', async () => {
    apiClient.post
      .mockResolvedValueOnce({ data: { sugestoes: ['a'] } })
      .mockResolvedValueOnce({ data: { sugestoes: ['b'] } });

    await expect(productService.getAtributoSuggestions(20)).resolves.toEqual({
      sugestoes: ['a'],
    });
    await expect(productService.sugerirAtributosGemini(21)).resolves.toEqual({
      sugestoes: ['b'],
    });

    expect(apiClient.post).toHaveBeenNthCalledWith(1, '/geracao/sugerir-atributos-gemini/20/');
    expect(apiClient.post).toHaveBeenNthCalledWith(2, '/geracao/sugerir-atributos-gemini/21/');
  });

  test('registrarFeedbackConteudoGerado creates feedback storage when product has no prior web data', async () => {
    jest.useFakeTimers().setSystemTime(new Date('2026-03-07T18:00:00.000Z'));

    apiClient.get.mockResolvedValueOnce({
      data: {
        id: 14,
        dados_brutos_web: null,
      },
    });
    apiClient.put.mockResolvedValueOnce({ data: { ok: true } });

    await expect(
      productService.registrarFeedbackConteudoGerado(14, {
        valor: 'nao_gostei',
      })
    ).resolves.toEqual({ ok: true });

    expect(apiClient.put).toHaveBeenCalledWith('/produtos/14/', {
      dados_brutos_web: {
        feedback_conteudo: {
          valor: 'nao_gostei',
          comentario: null,
          origem: 'tela_conteudo',
          atualizado_em: '2026-03-07T18:00:00.000Z',
        },
        feedback_conteudo_historico: [
          {
            valor: 'nao_gostei',
            comentario: null,
            origem: 'tela_conteudo',
            atualizado_em: '2026-03-07T18:00:00.000Z',
          },
        ],
      },
    });
  });

  test('registrarFeedbackConteudoGerado validates accepted values before any request', async () => {
    await expect(
      productService.registrarFeedbackConteudoGerado(12, { valor: 'talvez' })
    ).rejects.toThrow('Feedback invalido. Use "gostei" ou "nao_gostei".');

    expect(apiClient.get).not.toHaveBeenCalled();
    expect(apiClient.put).not.toHaveBeenCalled();
  });

  test('registrarFeedbackConteudoGerado rejects empty payloads before any request', async () => {
    await expect(productService.registrarFeedbackConteudoGerado(12)).rejects.toThrow(
      'Feedback invalido. Use "gostei" ou "nao_gostei".'
    );

    expect(apiClient.get).not.toHaveBeenCalled();
    expect(apiClient.put).not.toHaveBeenCalled();
  });

  test('registrarFeedbackConteudoGerado stores the current feedback and trims history to 20 items', async () => {
    jest.useFakeTimers().setSystemTime(new Date('2026-03-07T15:00:00.000Z'));

    apiClient.get.mockResolvedValueOnce({
      data: {
        id: 12,
        dados_brutos_web: {
          feedback_conteudo_historico: Array.from({ length: 20 }, (_, index) => ({
            valor: 'gostei',
            atualizado_em: `2026-03-${String(index + 1).padStart(2, '0')}T00:00:00.000Z`,
          })),
        },
      },
    });
    apiClient.put.mockResolvedValueOnce({ data: { ok: true } });

    const result = await productService.registrarFeedbackConteudoGerado(12, {
      valor: 'Gostei',
      comentario: '  Texto aprovado  ',
    });

    expect(apiClient.get).toHaveBeenCalledWith('/produtos/12/');
    expect(apiClient.put).toHaveBeenCalledTimes(1);
    expect(apiClient.put.mock.calls[0][0]).toBe('/produtos/12/');
    expect(apiClient.put.mock.calls[0][1]).toMatchObject({
      dados_brutos_web: {
        feedback_conteudo: {
          valor: 'gostei',
          comentario: 'Texto aprovado',
          origem: 'tela_conteudo',
          atualizado_em: '2026-03-07T15:00:00.000Z',
        },
      },
    });
    expect(
      apiClient.put.mock.calls[0][1].dados_brutos_web.feedback_conteudo_historico
    ).toHaveLength(20);
    expect(result).toEqual({ ok: true });
  });
});
