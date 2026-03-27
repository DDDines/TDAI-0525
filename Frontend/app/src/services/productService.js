/**
 * Module product service.
 *
 * Defines responsibilities and integration points for services.
 */

import logger from '../utils/logger';
import apiClient from './apiClient';
import basicTemplateService from './basicTemplateService';

async function getProdutos(params = {}) {
  try {
    const response = await apiClient.get('/produtos/', { params });
    logger.log('API Response in productService (getProdutos):', response.data);
    return response.data;
  } catch (error) {
    console.error('Erro ao buscar produtos:', error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao buscar produtos');
  }
}

async function getProdutosIds(params = {}) {
  try {
    const response = await apiClient.get('/produtos/ids', { params });
    return response.data;
  } catch (error) {
    console.error('Erro ao buscar IDs de produtos:', error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao buscar IDs de produtos');
  }
}

async function getProdutoById(produtoId) {
  try {
    const response = await apiClient.get(`/produtos/${produtoId}/`);
    logger.log('API Response in productService (getProdutoById):', response.data);
    return response.data;
  } catch (error) {
    console.error(`Erro ao buscar produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error(`Falha ao buscar produto ${produtoId}`);
  }
}

async function createProduto(produtoData) {
  try {
    const response = await apiClient.post('/produtos/', produtoData);
    return response.data;
  } catch (error) {
    console.error('Erro ao criar produto:', error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao criar produto');
  }
}

async function updateProduto(produtoId, produtoUpdateData) {
  try {
    const response = await apiClient.put(`/produtos/${produtoId}/`, produtoUpdateData);
    return response.data;
  } catch (error) {
    console.error(`Erro ao atualizar produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error(`Falha ao atualizar produto ${produtoId}`);
  }
}

async function deleteProduto(produtoId) {
  try {
    const response = await apiClient.delete(`/produtos/${produtoId}/`);
    return response.data;
  } catch (error) {
    console.error(`Erro ao apagar produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error(`Falha ao apagar produto ${produtoId}`);
  }
}

async function gerarTitulosProduto(produtoId) {
  try {
    const response = await apiClient.post(`/geracao/titulos/openai/${produtoId}`);
    return response.data;
  } catch (error) {
    console.error(`Erro ao gerar titulos para produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao gerar titulos');
  }
}

async function gerarDescricaoProduto(produtoId) {
  try {
    const response = await apiClient.post(`/geracao/descricao/openai/${produtoId}`);
    return response.data;
  } catch (error) {
    console.error(`Erro ao gerar descricao para produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao gerar descricao');
  }
}

async function gerarTitulosGemini(produtoId) {
  try {
    const response = await apiClient.post(`/geracao/titulos/gemini/${produtoId}`);
    return response.data;
  } catch (error) {
    console.error(`Erro ao gerar titulos com Gemini para produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao gerar titulos com Gemini');
  }
}

async function gerarDescricaoGemini(produtoId) {
  try {
    const response = await apiClient.post(`/geracao/descricao/gemini/${produtoId}`);
    return response.data;
  } catch (error) {
    console.error(`Erro ao gerar descricao com Gemini para produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao gerar descricao com Gemini');
  }
}

async function gerarTitulosProdutoModoBasico(produtoId, options = {}) {
  try {
    const customTemplate = await basicTemplateService.resolveCustomTemplateForRequest(
      'title',
      options?.template
    );
    if (customTemplate) {
      const response = await apiClient.post(
        `/geracao/titulos/basico/${produtoId}`,
        null,
        {
          params: {
            template: customTemplate,
          },
        }
      );
      return response.data;
    }
    const response = await apiClient.post(`/geracao/titulos/basico/${produtoId}`);
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao gerar titulos no modo basico para produto ${produtoId}:`,
      error.response?.data || error.message
    );
    throw error.response?.data || new Error('Falha ao gerar titulos no modo basico');
  }
}

async function gerarDescricaoProdutoModoBasico(produtoId, options = {}) {
  try {
    const customTemplate = await basicTemplateService.resolveCustomTemplateForRequest(
      'description',
      options?.template
    );
    if (customTemplate) {
      const response = await apiClient.post(
        `/geracao/descricao/basico/${produtoId}`,
        null,
        {
          params: {
            template: customTemplate,
          },
        }
      );
      return response.data;
    }
    const response = await apiClient.post(`/geracao/descricao/basico/${produtoId}`);
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao gerar descricao no modo basico para produto ${produtoId}:`,
      error.response?.data || error.message
    );
    throw error.response?.data || new Error('Falha ao gerar descricao no modo basico');
  }
}

async function iniciarEnriquecimentoWebProduto(produtoId, options = null) {
  try {
    let endpoint = `/enriquecimento-web/produto/${produtoId}`;
    const normalizedOptions =
      typeof options === 'string'
        ? { termosBuscaOverride: options, usarIA: false }
        : (options && typeof options === 'object' ? options : {});
    const termosBuscaOverride = normalizedOptions.termosBuscaOverride || null;
    const usarIA = Boolean(normalizedOptions.usarIA);
    const queryParams = [];
    if (termosBuscaOverride) {
      queryParams.push(`termos_busca_override=${encodeURIComponent(termosBuscaOverride)}`);
    }
    if (usarIA) {
      queryParams.push('usar_ia=true');
    }
    if (queryParams.length > 0) {
      endpoint += `?${queryParams.join('&')}`;
    }
    const response = await apiClient.post(endpoint);
    return response.data;
  } catch (error) {
    const statusCode = error?.response?.status;
    const detail =
      error?.response?.data?.detail ||
      error?.response?.data?.msg ||
      error?.response?.data?.message ||
      error?.message;

    console.error(`Erro ao iniciar enriquecimento web do produto ${produtoId}:`, error.response?.data || error.message);

    if (statusCode === 401) {
      throw new Error('Sessao expirada. Faca login novamente para iniciar o enriquecimento.');
    }
    if (statusCode === 409) {
      throw new Error(detail || 'Ja existe enriquecimento em andamento para este produto.');
    }

    throw new Error(detail || 'Falha ao iniciar processo de enriquecimento web');
  }
}

async function batchGeneration({ produtoIds, tipo, provider, numTitulos = 3, tamanhoPalavras = 150 }) {
  try {
    const response = await apiClient.post('/geracao/batch', {
      produto_ids: produtoIds,
      tipo,
      provider,
      num_titulos: numTitulos,
      tamanho_palavras: tamanhoPalavras,
    });
    return response.data; // { agendados, ignorados, detalhes }
  } catch (error) {
    console.error('Erro no batch generation:', error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao agendar geração em lote.');
  }
}

async function atualizarWorkflowStatus(produtoId, workflowStatus) {
  try {
    const response = await apiClient.patch(`/produtos/${produtoId}/workflow-status`, { workflow_status: workflowStatus });
    return response.data;
  } catch (error) {
    console.error(`Erro ao atualizar workflow_status do produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao atualizar status do workflow.');
  }
}

async function batchDeleteProdutos(produtoIds) {
  try {
    const response = await apiClient.post('/produtos/batch-delete/', produtoIds);
    return response.data;
  } catch (error) {
    console.error('Erro ao apagar produtos em lote:', error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao apagar produtos em lote');
  }
}

async function getAtributoSuggestions(produtoId) {
  try {
    const response = await apiClient.post(`/geracao/sugerir-atributos-gemini/${produtoId}/`);
    return response.data;
  } catch (error) {
    console.error(`Erro ao buscar sugestoes de atributos para produto ${produtoId}:`, error.response?.data || error.message);
    throw error.response?.data || new Error('Falha ao buscar sugestoes de atributos da IA.');
  }
}

const sugerirAtributosGemini = getAtributoSuggestions;

async function registrarFeedbackConteudoGerado(produtoId, feedbackPayload = {}) {
  const valor = String(feedbackPayload?.valor || '').trim().toLowerCase();
  if (!['gostei', 'nao_gostei'].includes(valor)) {
    throw new Error('Feedback invalido. Use "gostei" ou "nao_gostei".');
  }

  const comentario = String(feedbackPayload?.comentario || '').trim();
  const produtoAtual = await getProdutoById(produtoId);
  const dadosBrutos = produtoAtual?.dados_brutos_web && typeof produtoAtual.dados_brutos_web === 'object'
    ? { ...produtoAtual.dados_brutos_web }
    : {};

  const novoRegistro = {
    valor,
    comentario: comentario || null,
    origem: 'tela_conteudo',
    atualizado_em: new Date().toISOString(),
  };
  const historicoAnterior = Array.isArray(dadosBrutos.feedback_conteudo_historico)
    ? dadosBrutos.feedback_conteudo_historico
    : [];
  dadosBrutos.feedback_conteudo = novoRegistro;
  dadosBrutos.feedback_conteudo_historico = [novoRegistro, ...historicoAnterior].slice(0, 20);

  return updateProduto(produtoId, { dados_brutos_web: dadosBrutos });
}

async function exportarProdutos({ ids, search, fornecedor_id, categoria, status_enriquecimento_web, status_titulo_ia, status_descricao_ia, product_type_id, enrichment_scope, format = 'xlsx' } = {}) {
  const params = new URLSearchParams();
  if (ids && ids.length > 0) params.set('ids', ids.join(','));
  if (search) params.set('search', search);
  if (fornecedor_id) params.set('fornecedor_id', fornecedor_id);
  if (categoria) params.set('categoria', categoria);
  if (format) params.set('format', format);
  if (status_enriquecimento_web) params.set('status_enriquecimento_web', status_enriquecimento_web);
  if (status_titulo_ia) params.set('status_titulo_ia', status_titulo_ia);
  if (status_descricao_ia) params.set('status_descricao_ia', status_descricao_ia);
  if (product_type_id) params.set('product_type_id', product_type_id);
  if (enrichment_scope) params.set('enrichment_scope', enrichment_scope);

  const response = await apiClient.get(`/produtos/exportar/?${params.toString()}`, {
    responseType: 'blob',
  });

  const url = URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.download = format === 'csv' ? 'produtos.csv' : 'produtos_commercefolio.xlsx';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function getExportHistory() {
  const response = await apiClient.get('/produtos/exports/historico');
  return response.data;
}

async function gerarConteudoCanal(produtoId, canal) {
  const response = await apiClient.post(`/geracao/canal/${canal}/${produtoId}/`);
  return response.data;
}

export {
  getProdutos,
  getProdutosIds,
  getProdutoById,
  createProduto,
  updateProduto,
  deleteProduto,
  gerarTitulosProduto,
  gerarDescricaoProduto,
  gerarTitulosGemini,
  gerarDescricaoGemini,
  gerarTitulosProdutoModoBasico,
  gerarDescricaoProdutoModoBasico,
  iniciarEnriquecimentoWebProduto,
  batchDeleteProdutos,
  getAtributoSuggestions,
  sugerirAtributosGemini,
  registrarFeedbackConteudoGerado,
  exportarProdutos,
  gerarConteudoCanal,
  atualizarWorkflowStatus,
};

export default {
  getProdutos,
  getProdutosIds,
  getProdutoById,
  createProduto,
  updateProduto,
  deleteProduto,
  gerarTitulosProduto,
  gerarDescricaoProduto,
  gerarTitulosGemini,
  gerarDescricaoGemini,
  gerarTitulosProdutoModoBasico,
  gerarDescricaoProdutoModoBasico,
  iniciarEnriquecimentoWebProduto,
  batchDeleteProdutos,
  getAtributoSuggestions,
  sugerirAtributosGemini,
  registrarFeedbackConteudoGerado,
  exportarProdutos,
  gerarConteudoCanal,
  atualizarWorkflowStatus,
  batchGeneration,
  getCatalogStats,
  getExportHistory,
};

async function getCatalogStats() {
  try {
    const response = await apiClient.get('/produtos/stats');
    return response.data;
  } catch (error) {
    throw error.response?.data || new Error('Falha ao buscar estatísticas do catálogo.');
  }
}
