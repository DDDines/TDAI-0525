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

export const previewCatalogo = async (
  file,
  pageCount = 1,
  startPage = 1,
  fornecedorId = null,
) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('page_count', pageCount);
    formData.append('start_page', startPage);
    if (fornecedorId) {
      formData.append('fornecedor_id', fornecedorId);
    }
    const response = await apiClient.post(
      '/produtos/importar-catalogo-preview/',
      formData,
    );
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


export const getCatalogImportFiles = async (params = {}) => {
  try {
    const response = await apiClient.get('/produtos/catalog-import-files/', { params });
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
  }
};

export const deleteCatalogFile = async (fileId) => {
  try {
    const response = await apiClient.delete(
      `/produtos/catalog-import-files/${fileId}/`
    );
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao excluir arquivo ${fileId}:`,
      JSON.stringify(error.response?.data || error.message || error)
    );
    if (error.response && error.response.data) {
      throw error.response.data;
    }
    throw new Error(error.message || 'Falha ao excluir arquivo');
  }
};

export const reprocessCatalogFile = async (fileId) => {
  try {
    const response = await apiClient.post(
      `/produtos/catalog-import-files/${fileId}/reprocess/`
    );
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao reprocessar arquivo ${fileId}:`,
      JSON.stringify(error.response?.data || error.message || error)
    );
    if (error.response && error.response.data) {
      throw error.response.data;
    }
    throw new Error(error.message || 'Falha ao reprocessar arquivo');
  }
};

export const getImportacaoStatus = async (fileId) => {
  try {
    const response = await apiClient.get(
      `/produtos/importar-catalogo-status/${fileId}`
    );
    return response.data;
  } catch (error) {
    console.error(`Erro ao consultar status do arquivo ${fileId}:`, JSON.stringify(error.response?.data || error.message || error));
    if (error.response && error.response.data) {
      throw error.response.data;
    }
    throw new Error(error.message || 'Falha ao consultar status da importação');
  }
};

export const getImportacaoResult = async (fileId) => {
  try {
    const response = await apiClient.get(`/produtos/importar-catalogo-result/${fileId}/`);
    return response.data;
  } catch (error) {
    console.error(`Erro ao obter resultado do arquivo ${fileId}:`, JSON.stringify(error.response?.data || error.message || error));
    if (error.response && error.response.data) {
      throw error.response.data;
    }
    throw new Error(error.message || 'Falha ao obter resultado da importação');
  }
};

// -------- NOVAS FUNÇÕES ---------

// Envia um PDF e obtém imagens de todas as páginas
export const uploadForPagePreview = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post('/fornecedores/import/preview-pages', formData);
    return response.data;
  } catch (error) {
    console.error(
      'Erro ao enviar arquivo para preview de páginas:',
      JSON.stringify(error.response?.data || error.message || error),
    );
    if (error.response && error.response.data) {
      throw error.response.data;
    }
    throw new Error(error.message || 'Falha ao enviar arquivo para preview');
  }
};

// Extrai dados de uma página específica de um PDF já enviado
export const fetchPageDataForMapping = async (fileId, pageNumber) => {
  try {
    const response = await apiClient.get('/fornecedores/import/extract-page-data', {
      params: { file_id: fileId, page_number: pageNumber },
    });
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao obter dados da página ${pageNumber} do arquivo ${fileId}:`,
      JSON.stringify(error.response?.data || error.message || error),
    );
    if (error.response && error.response.data) {
      throw error.response.data;
    }
    throw new Error(error.message || 'Falha ao extrair dados da página');
  }
};

// Inicia o processamento completo do catálogo
export const startFullProcess = async (payload) => {
  try {
    const response = await apiClient.post('/fornecedores/import/process-full-catalog', payload);
    return response.data;
  } catch (error) {
    console.error(
      'Erro ao iniciar processamento completo do catálogo:',
      JSON.stringify(error.response?.data || error.message || error),
    );
    if (error.response && error.response.data) {
      throw error.response.data;
    }
    throw new Error(error.message || 'Falha ao iniciar processamento do catálogo');
  }
};

// Consulta o progresso de um job de importação
export const getImportProgress = async (jobId) => {
  try {
    const response = await apiClient.get(`/fornecedores/import/progress/${jobId}`);
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao consultar progresso do job ${jobId}:`,
      JSON.stringify(error.response?.data || error.message || error),
    );
    if (error.response && error.response.data) {
      throw error.response.data;
    }
    throw new Error(error.message || 'Falha ao consultar progresso da importação');
  }
};

// Obtém os dados para revisão após o processamento
export const getReviewData = async (jobId, params = {}) => {
  try {
    const response = await apiClient.get(`/fornecedores/import/review/${jobId}`, { params });
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao obter dados de revisão para job ${jobId}:`,
      JSON.stringify(error.response?.data || error.message || error),
    );
    if (error.response && error.response.data) {
      throw error.response.data;
    }
    throw new Error(error.message || 'Falha ao buscar dados de revisão');
  }
};

// Confirma a importação após revisão
export const commitImport = async (jobId) => {
  try {
    const response = await apiClient.post(`/fornecedores/import/commit/${jobId}`);
    return response.data;
  } catch (error) {
    console.error(
      `Erro ao confirmar importação do job ${jobId}:`,
      JSON.stringify(error.response?.data || error.message || error),
    );
    if (error.response && error.response.data) {
      throw error.response.data;
    }
    throw new Error(error.message || 'Falha ao confirmar importação');
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
  getCatalogImportFiles,
  deleteCatalogFile,
  reprocessCatalogFile,
  getImportacaoStatus,
  getImportacaoResult,
  uploadForPagePreview,
  fetchPageDataForMapping,
  startFullProcess,
  getImportProgress,
  getReviewData,
  commitImport,
};
