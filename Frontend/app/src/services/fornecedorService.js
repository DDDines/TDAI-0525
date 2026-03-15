/**
 * Module fornecedor service.
 *
 * Defines responsibilities and integration points for services.
 */

import logger from '../utils/logger';
import apiClient from './apiClient';

function extractErrorPayload(error) {
  if (error?.response && error.response.data) {
    return error.response.data;
  }
  return null;
}

function resolveErrorMessage(error, fallbackMessage) {
  if (typeof error?.message === 'string' && error.message.trim()) {
    return error.message;
  }
  return fallbackMessage;
}

function serializeServiceError(error) {
  if (error?.response?.data) {
    return JSON.stringify(error.response.data);
  }
  if (typeof error?.message === 'string' && error.message.trim()) {
    return JSON.stringify(error.message);
  }
  return JSON.stringify(error);
}

function throwFornecedorServiceError(error, requestMessage, fallbackMessage, extraPayload = null) {
  const payload = extractErrorPayload(error);
  if (payload) {
    if (extraPayload && typeof extraPayload === 'object') {
      throw { ...payload, ...extraPayload };
    }
    throw payload;
  }
  if (requestMessage && error?.request) {
    throw new Error(requestMessage);
  }
  throw new Error(resolveErrorMessage(error, fallbackMessage));
}

function mapImportResultResponse(response) {
  if (response.status === 202) {
    return {
      ready: false,
      status:
        typeof response.data?.status === 'string' && response.data.status.trim()
          ? response.data.status
          : 'PROCESSING',
      detail:
        typeof response.data?.detail === 'string' && response.data.detail.trim()
          ? response.data.detail
          : 'Resultado final ainda n\u00e3o dispon\u00edvel. Continue monitorando o status.',
    };
  }

  return {
    ready: true,
    ...response.data,
  };
}

function appendFormDataIfPresent(formData, key, value) {
  if (value !== null && value !== undefined) {
    formData.append(key, value);
  }
}

async function getFornecedores(params = {}) {
  try {
    const response = await apiClient.get('/fornecedores/', { params });
    logger.log('API Response in fornecedorService (getFornecedores):', response.data);
    return response.data;
  } catch (error) {
    console.error(
      'Error fetching fornecedores (SERVICE LEVEL):',
      serializeServiceError(error)
    );
    throwFornecedorServiceError(
      error,
        'Nenhuma resposta do servidor ao buscar fornecedores.',
        'Erro ao configurar requisi\u00e7\u00e3o para buscar fornecedores.'
    );
  }
}

async function getFornecedoresIds(params = {}) {
  try {
    const response = await apiClient.get('/fornecedores/ids', { params });
    return response.data;
  } catch (error) {
    console.error(
      'Erro ao buscar IDs de fornecedores:',
      serializeServiceError(error)
    );
    throwFornecedorServiceError(
      error,
      'Nenhuma resposta do servidor ao buscar IDs de fornecedores.',
      'Erro ao configurar requisicao para buscar IDs de fornecedores.'
    );
  }
}

async function getFornecedorById(fornecedorId) {
  try {
    const response = await apiClient.get(`/fornecedores/${fornecedorId}`);
    return response.data;
  } catch (error) {
    console.error(
      `Error fetching fornecedor ${fornecedorId} (SERVICE LEVEL):`,
      serializeServiceError(error)
    );
    throwFornecedorServiceError(
      error,
        `Nenhuma resposta do servidor ao buscar fornecedor ${fornecedorId}.`,
        `Erro ao configurar requisi\u00e7\u00e3o para buscar fornecedor ${fornecedorId}.`
    );
  }
}

async function createFornecedor(fornecedorData) {
  try {
    const response = await apiClient.post('/fornecedores/', fornecedorData);
    return response.data;
  } catch (error) {
    console.error('Axios error object in createFornecedor (SERVICE LEVEL):', error);
    if (error.response) {
      console.error('Axios error.response.data:', error.response.data);
    }
    throwFornecedorServiceError(
      error,
        null,
        'Erro ao tentar criar fornecedor. Verifique o console do servi\u00e7o.'
    );
  }
}

async function updateFornecedor(fornecedorId, fornecedorUpdateData) {
  try {
    const response = await apiClient.put(`/fornecedores/${fornecedorId}`, fornecedorUpdateData);
    return response.data;
  } catch (error) {
    console.error(
      `Error updating fornecedor ${fornecedorId} (SERVICE LEVEL):`,
      serializeServiceError(error)
    );
    throwFornecedorServiceError(
      error,
        `Nenhuma resposta do servidor ao tentar atualizar fornecedor ${fornecedorId}.`,
        `Erro ao configurar requisi\u00e7\u00e3o para atualizar fornecedor ${fornecedorId}.`
    );
  }
}

async function resolveFornecedorLogo(siteUrl) {
  try {
    const response = await apiClient.post('/fornecedores/resolve-logo', {
      site_url: siteUrl,
    });
    return response.data;
  } catch (error) {
    console.error(
      'Erro ao resolver logo do fornecedor:',
      serializeServiceError(error)
    );
    throwFornecedorServiceError(
      error,
      'Nenhuma resposta do servidor ao tentar localizar o logo do fornecedor.',
      'Erro ao configurar requisicao para localizar o logo do fornecedor.'
    );
  }
}

async function setFornecedorMapping(fornecedorId, mapping = {}) {
  try {
    const response = await apiClient.put(`/fornecedores/${fornecedorId}/mapping`, mapping);
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao salvar mapping do fornecedor ${fornecedorId}:`,
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao salvar mapeamento do fornecedor');
  }
}

async function deleteFornecedor(fornecedorId) {
  try {
    const response = await apiClient.delete(`/fornecedores/${fornecedorId}`);
    return response.data;
  } catch (error) {
    console.error(
      `Error deleting fornecedor ${fornecedorId} (SERVICE LEVEL):`,
      serializeServiceError(error)
    );
    throwFornecedorServiceError(
      error,
        `Nenhuma resposta do servidor ao tentar deletar fornecedor ${fornecedorId}.`,
        `Erro ao configurar requisi\u00e7\u00e3o para deletar fornecedor ${fornecedorId}.`
    );
  }
}

async function previewCatalogo(file, pageCount = 15, startPage = 1, fornecedorId = null) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('page_count', pageCount);
    formData.append('start_page', startPage);
    appendFormDataIfPresent(formData, 'fornecedor_id', fornecedorId);

    const response = await apiClient.post('/produtos/importar-catalogo-preview/', formData);
    const { file_id, headers, sample_rows, preview_images, num_pages, table_pages } = response.data;
    return {
      fileId: file_id,
      headers,
      sampleRows: sample_rows,
      previewImages: preview_images,
      numPages: num_pages,
      tablePages: table_pages,
    };
  } catch (error) {
    console.error(
      'Erro ao gerar preview do catalogo:',
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao solicitar preview do catalogo');
  }
}

async function importCatalogo(fornecedorId, file, mapping = null) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    if (mapping) {
      formData.append('mapeamento_colunas_usuario', JSON.stringify(mapping));
    }
    const response = await apiClient.post(`/produtos/importar-catalogo/${fornecedorId}/`, formData);
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao importar catalogo para fornecedor ${fornecedorId}:`,
      `Erro ao importar cat\u00e1logo para fornecedor ${fornecedorId}:`,
      serializeServiceError(error)
    );
    throwFornecedorServiceError(
      error,
      'Nenhuma resposta do servidor ao tentar importar cat\u00e1logo.',
      'Erro ao configurar requisi\u00e7\u00e3o de importa\u00e7\u00e3o de cat\u00e1logo.'
    );
  }
}

async function getCatalogImportFiles(params = {}) {
  try {
    const response = await apiClient.get('/produtos/catalog-import-files/', { params });
    return response.data;
  } catch (error) {
    console.error(
      'Erro ao buscar arquivos de importa\u00e7\u00e3o:',
      serializeServiceError(error)
    );
    throwFornecedorServiceError(
      error,
      'Nenhuma resposta do servidor ao buscar arquivos de importa\u00e7\u00e3o.',
      'Erro ao configurar requisi\u00e7\u00e3o para buscar arquivos de importa\u00e7\u00e3o.'
    );
  }
}

async function deleteCatalogFile(fileId) {
  try {
    const response = await apiClient.delete(`/produtos/catalog-import-files/${fileId}/`);
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao excluir arquivo ${fileId}:`,
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao excluir arquivo');
  }
}

async function reprocessCatalogFile(fileId, payload = {}) {
  try {
    const response = await apiClient.post(
      `/produtos/catalog-import-files/${fileId}/reprocess/`,
      payload
    );
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao reprocessar arquivo ${fileId}:`,
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao reprocessar arquivo');
  }
}

async function getImportacaoStatus(fileId) {
  try {
    const response = await apiClient.get(`/produtos/importar-catalogo-status/${fileId}`);
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao consultar status do arquivo ${fileId}:`,
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao consultar status da importa\u00e7\u00e3o');
  }
}

async function getImportacaoResult(fileId) {
  try {
    const response = await apiClient.get(`/produtos/importar-catalogo-result/${fileId}/`);
    return mapImportResultResponse(response);
  } catch (error) {
    console.error(
      `Erro ao obter resultado do arquivo ${fileId}:`,
      serializeServiceError(error)
    );
    throwFornecedorServiceError(
      error,
      null,
      'Falha ao obter resultado da importa\u00e7\u00e3o',
      error?.response?.status ? { http_status: error.response.status } : null
    );
  }
}

async function uploadForPagePreview(file, fornecedorId) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post(`/fornecedores/${fornecedorId}/preview-pdf`, formData);
    const { import_file_id, image_urls } = response.data;
    return { fileId: import_file_id, image_urls };
  } catch (error) {
    console.error(
      'Erro ao enviar arquivo para preview de paginas:',
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao enviar arquivo para preview');
  }
}

async function getPdfPreview(file, fornecedorId, offset = 0, limit = 5) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post(`/fornecedores/${fornecedorId}/preview-pdf`, formData, {
      params: { offset, limit },
    });
    const { image_urls, total_pages } = response.data;
    return { image_urls, total_pages };
  } catch (error) {
    console.error(
      'Erro ao obter pre-visualizacao do PDF:',
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao obter pre-visualizacao do PDF');
  }
}

async function fetchPageDataForMapping(fileId, pageNumber) {
  try {
    const response = await apiClient.get('/fornecedores/import/extract-page-data', {
      params: { file_id: fileId, page_number: pageNumber },
    });
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao obter dados da pagina ${pageNumber} do arquivo ${fileId}:`,
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao extrair dados da pagina');
  }
}

async function startFullProcess(payload) {
  try {
    const response = await apiClient.post('/fornecedores/import/process-full-catalog', payload);
    return response.data;
  } catch (error) {
    console.error(
      'Erro ao iniciar processamento completo do cat\u00e1logo:',
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao iniciar processamento do cat\u00e1logo');
  }
}

async function getImportProgress(jobId) {
  try {
    const response = await apiClient.get(`/fornecedores/import/progress/${jobId}`);
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao consultar progresso do job ${jobId}:`,
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao consultar progresso da importa\u00e7\u00e3o');
  }
}

async function selecionarRegiao({ fileId, pageNumber, bbox }) {
  try {
    const payload = {
      file_id: fileId,
      page_number: pageNumber,
      region: bbox,
    };
    const response = await apiClient.post('/fornecedores/preview-catalog-region', payload);
    return response.data;
  } catch (error) {
    console.error(
      'Erro ao pre-visualizar regiao do catalogo:',
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao pre-visualizar regiao do catalogo');
  }
}

async function extractRegionBulk({ fileId, bbox, pages = null, allPages = false }) {
  try {
    const payload = {
      file_id: fileId,
      region: bbox,
      pages,
      all_pages: allPages,
    };
    const response = await apiClient.post('/fornecedores/extract_data_from_pdf_bulk', payload);
    return response.data;
  } catch (error) {
    console.error(
      'Erro ao iniciar extracao em lote:',
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao iniciar extracao em lote');
  }
}

async function selecionarRegiaoProduto({ fileId, pageNumber, bbox, bboxNorm, canvasWidth, canvasHeight }) {
  try {
    const payload = {
      file_id: fileId,
      page: pageNumber,
      bbox,
      bbox_norm: bboxNorm,
      canvas_width: canvasWidth,
      canvas_height: canvasHeight,
    };
    const response = await apiClient.post('/produtos/selecionar-regiao/', payload);
    return response.data;
  } catch (error) {
    console.error(
      'Erro ao selecionar regiao do PDF (produtos):',
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao selecionar regiao do PDF');
  }
}

async function getReviewData(jobId, params = {}) {
  try {
    const response = await apiClient.get(`/fornecedores/import/review/${jobId}`, { params });
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao obter dados de revis\u00e3o para job ${jobId}:`,
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao buscar dados de revis\u00e3o');
  }
}

async function commitImport(jobId) {
  try {
    const response = await apiClient.post(`/fornecedores/import/commit/${jobId}`);
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao confirmar importa\u00e7\u00e3o do job ${jobId}:`,
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao confirmar importa\u00e7\u00e3o');
  }
}

async function finalizarImportacaoCatalogo({
  fileId,
  productTypeId,
  fornecedorId,
  mapping,
  pages,
  region,
  extractionMode,
}) {
  try {
    const payload = {
      product_type_id: productTypeId,
      fornecedor_id: fornecedorId,
      mapping,
      pages,
      region,
      extraction_mode: extractionMode || 'ocr',
    };
    const response = await apiClient.post(`/produtos/importar-catalogo-finalizar/${fileId}/`, payload);
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao finalizar importa\u00e7\u00e3o do cat\u00e1logo ${fileId}:`,
      serializeServiceError(error)
    );
    throwFornecedorServiceError(error, null, 'Falha ao finalizar importa\u00e7\u00e3o do cat\u00e1logo');
  }
}

export {
  getFornecedores,
  getFornecedorById,
  createFornecedor,
  updateFornecedor,
  resolveFornecedorLogo,
  setFornecedorMapping,
  deleteFornecedor,
  previewCatalogo,
  importCatalogo,
  getCatalogImportFiles,
  deleteCatalogFile,
  reprocessCatalogFile,
  getImportacaoStatus,
  getImportacaoResult,
  uploadForPagePreview,
  getPdfPreview,
  fetchPageDataForMapping,
  startFullProcess,
  getImportProgress,
  selecionarRegiao,
  extractRegionBulk,
  selecionarRegiaoProduto,
  getReviewData,
  commitImport,
  finalizarImportacaoCatalogo,
};

export default {
  getFornecedores,
  getFornecedoresIds,
  getFornecedorById,
  createFornecedor,
  updateFornecedor,
  resolveFornecedorLogo,
  setFornecedorMapping,
  deleteFornecedor,
  previewCatalogo,
  importCatalogo,
  getCatalogImportFiles,
  deleteCatalogFile,
  reprocessCatalogFile,
  getImportacaoStatus,
  getImportacaoResult,
  uploadForPagePreview,
  getPdfPreview,
  fetchPageDataForMapping,
  startFullProcess,
  getImportProgress,
  selecionarRegiao,
  extractRegionBulk,
  selecionarRegiaoProduto,
  getReviewData,
  commitImport,
  finalizarImportacaoCatalogo,
};
