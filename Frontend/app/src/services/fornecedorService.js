// Frontend/app/src/services/fornecedorService.js
import logger from '../utils/logger';
import apiClient from './apiClient';

export const getFornecedores = async (params = {}) => { // params pode incluir skip, limit, termo_busca
  try {
    // O backend agora deve retornar { items: [], total_items: X, limit: Y, skip: Z }
    const response = await apiClient.get('/fornecedores/', { params });
    logger.log('API Response in fornecedorService (getFornecedores):', response.data); // Para depuração
    return response.data; // Retorna o objeto completo
  } catch (error) {
    console.error('Error fetching fornecedores (SERVICE LEVEL):', JSON.stringify(error.response?.data || error.message || error));
    if (error.response && error.response.data) {
      throw error.response.data;
    } else if (error.request) {
      throw new Error('Nenhuma resposta do servidor ao buscar fornecedores.');
    } else {
      throw new Error(error.message || 'Erro ao configurar requisição para buscar fornecedores.');
    }
  }
};

export const getFornecedorById = async (fornecedorId) => {
  try {
    const response = await apiClient.get(`/fornecedores/${fornecedorId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching fornecedor ${fornecedorId} (SERVICE LEVEL):`, JSON.stringify(error.response?.data || error.message || error));
    if (error.response && error.response.data) {
      throw error.response.data;
    } else if (error.request) {
      throw new Error(`Nenhuma resposta do servidor ao buscar fornecedor ${fornecedorId}.`);
    } else {
      throw new Error(error.message || `Erro ao configurar requisição para buscar fornecedor ${fornecedorId}.`);
    }
  }
};

export const createFornecedor = async (fornecedorData) => {
  try {
    const response = await apiClient.post('/fornecedores/', fornecedorData);
    return response.data;
  } catch (error) {
    console.error('Axios error object in createFornecedor (SERVICE LEVEL):', error);
    if (error.response) {
        console.error('Axios error.response.data:', error.response.data);
    }
    if (error.response && error.response.data) {
        throw error.response.data;
    } else {
        throw new Error(error.message || 'Erro ao tentar criar fornecedor. Verifique o console do serviço.');
    }
  }
};

export const updateFornecedor = async (fornecedorId, fornecedorUpdateData) => {
  try {
    const response = await apiClient.put(`/fornecedores/${fornecedorId}`, fornecedorUpdateData);
    return response.data;
  } catch (error) {
    console.error(`Error updating fornecedor ${fornecedorId} (SERVICE LEVEL):`, JSON.stringify(error.response?.data || error.message || error));
    if (error.response && error.response.data) {
      throw error.response.data;
    } else if (error.request) {
      throw new Error(`Nenhuma resposta do servidor ao tentar atualizar fornecedor ${fornecedorId}.`);
    } else {
      throw new Error(error.message || `Erro ao configurar requisição para atualizar fornecedor ${fornecedorId}.`);
    }
  }
};

export const deleteFornecedor = async (fornecedorId) => {
  try {
    const response = await apiClient.delete(`/fornecedores/${fornecedorId}`);
    return response.data;
  } catch (error) {
    console.error(`Error deleting fornecedor ${fornecedorId} (SERVICE LEVEL):`, JSON.stringify(error.response?.data || error.message || error));
    if (error.response && error.response.data) {
      throw error.response.data;
    } else if (error.request) {
      throw new Error(`Nenhuma resposta do servidor ao tentar deletar fornecedor ${fornecedorId}.`);
    } else {
      throw new Error(error.message || `Erro ao configurar requisição para deletar fornecedor ${fornecedorId}.`);
    }
  }
};

export const previewCatalogo = async (file, pageCount = 5) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post(`/produtos/importar-catalogo-preview/?page_count=${pageCount}`, formData);
    const { file_id, headers, sample_rows, preview_images } = response.data;
export const previewCatalogo = async (file, pageCount = 1) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post('/produtos/importar-catalogo-preview/', formData, { params: { page_count: pageCount } });
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
    console.error('Erro ao gerar preview do catálogo:', JSON.stringify(error.response?.data || error.message || error));
    if (error.response && error.response.data) {
      throw error.response.data;
    }
    throw new Error(error.message || 'Falha ao solicitar preview do catálogo');
  }
};

export const importCatalogo = async (fornecedorId, file, mapping = null) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    if (mapping) {
      formData.append('mapeamento_colunas_usuario', JSON.stringify(mapping));
    }
    const response = await apiClient.post(`/produtos/importar-catalogo/${fornecedorId}/`, formData);
    return response.data;
  } catch (error) {
    console.error(`Erro ao importar catálogo para fornecedor ${fornecedorId}:`, JSON.stringify(error.response?.data || error.message || error));
    if (error.response && error.response.data) {
      throw error.response.data;
    } else if (error.request) {
      throw new Error('Nenhuma resposta do servidor ao tentar importar catálogo.');
    } else {
      throw new Error(error.message || 'Erro ao configurar requisição de importação de catálogo.');
    }
  }
};

export const finalizarImportacaoCatalogo = async (
  fileId,
  fornecedorId,
  mapping = null,
  rows = null,
  productTypeId = null,
) => {
  try {
    const payload = { file_id: fileId, fornecedor_id: fornecedorId };
    if (productTypeId) payload.product_type_id = productTypeId;
    if (mapping) {
      payload.mapping = mapping;
    }
    if (rows) {
      payload.rows = rows;
    }
    const response = await apiClient.post(
      `/produtos/importar-catalogo-finalizar/${fileId}/`,
      payload
    );
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao finalizar importação do catálogo ${fileId}:`,
      JSON.stringify(error.response?.data || error.message || error),
    );
    if (error.response && error.response.data) {
      throw error.response.data;
    }
    throw new Error(error.message || 'Falha ao confirmar importação do catálogo');
  }
};

export const getCatalogImportFiles = async (params = {}) => {
  try {
    const response = await apiClient.get('/catalog-import-files/', { params });
    return response.data;
  } catch (error) {
    console.error('Erro ao buscar arquivos de importação:', JSON.stringify(error.response?.data || error.message || error));
    if (error.response && error.response.data) {
      throw error.response.data;
    } else if (error.request) {
      throw new Error('Nenhuma resposta do servidor ao buscar arquivos de importação.');
    } else {
      throw new Error(error.message || 'Erro ao configurar requisição para buscar arquivos de importação.');
    }
export const getImportacaoStatus = async (fileId) => {
  try {
    const response = await apiClient.get(`/produtos/importar-catalogo-status/${fileId}/`);
    return response.data;
  } catch (error) {
    console.error(`Erro ao consultar status do arquivo ${fileId}:`, JSON.stringify(error.response?.data || error.message || error));
    if (error.response && error.response.data) {
      throw error.response.data;
    }
    throw new Error(error.message || 'Falha ao consultar status da importação');
  }
};

export default {
  getFornecedores,
  getFornecedorById,
  createFornecedor,
  updateFornecedor,
  deleteFornecedor,
  previewCatalogo,
  importCatalogo,
  finalizarImportacaoCatalogo,
  getCatalogImportFiles,
  getImportacaoStatus,
};
