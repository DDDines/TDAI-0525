// Frontend/app/src/services/productTypeService.js
import axios from 'axios';

// A URL base da API, vinda de variáveis de ambiente Vite ou um valor padrão.
const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// Função para obter o token do localStorage
const getToken = () => localStorage.getItem('userToken');

// Cria uma instância do axios com a baseURL e interceptors
const axiosInstance = axios.create({
  baseURL: API_URL, // Ex: http://localhost:8000/api/v1
});

// Interceptor para adicionar o token de autenticação em cada requisição
axiosInstance.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// --- Serviços para Tipos de Produto (ProductType) ---
// O router no backend para product-types já inclui /api/v1 no seu prefixo,
// então os paths aqui serão relativos a isso se o API_URL for http://localhost:8000.
// Se API_URL é http://localhost:8000/api/v1, então os paths aqui devem ser ex: '/product-types/'

const PRODUCT_TYPES_ENDPOINT = '/product-types'; // Base para os endpoints de ProductType

/**
 * Cria um novo tipo de produto.
 * @param {object} productTypeData - Dados para o novo tipo de produto (schemas.ProductTypeCreate).
 * @param {boolean} [asGlobal=false] - Se true e usuário for admin, cria como global.
 * @returns {Promise<object>} O tipo de produto criado.
 */
export const createProductType = async (productTypeData, asGlobal = false) => {
  try {
    const response = await axiosInstance.post(`${PRODUCT_TYPES_ENDPOINT}/`, productTypeData, {
      params: { as_global: asGlobal },
    });
    return response.data;
  } catch (error) {
    console.error('Erro ao criar tipo de produto:', error.response?.data || error.message);
    throw error.response?.data || error;
  }
};

/**
 * Lista os tipos de produto.
 * @param {object} params - Parâmetros de paginação e filtro.
 * @param {number} [params.skip=0] - Número de itens a pular.
 * @param {number} [params.limit=100] - Número máximo de itens a retornar.
 * @param {boolean} [params.listAllForAdmin=false] - Se true (e user é admin), lista todos.
 * @returns {Promise<Array<object>>} Uma lista de tipos de produto.
 */
export const getProductTypes = async ({ skip = 0, limit = 100, listAllForAdmin = false } = {}) => {
  try {
    const response = await axiosInstance.get(`${PRODUCT_TYPES_ENDPOINT}/`, {
      params: { skip, limit, list_all_for_admin: listAllForAdmin },
    });
    return response.data;
  } catch (error) {
    console.error('Erro ao buscar tipos de produto:', error.response?.data || error.message);
    throw error.response?.data || error;
  }
};

/**
 * Obtém detalhes de um tipo de produto específico pelo ID.
 * @param {number} productTypeId - O ID do tipo de produto.
 * @returns {Promise<object>} O tipo de produto.
 */
export const getProductTypeById = async (productTypeId) => {
  try {
    const response = await axiosInstance.get(`${PRODUCT_TYPES_ENDPOINT}/${productTypeId}`);
    return response.data;
  } catch (error) {
    console.error(`Erro ao buscar tipo de produto ${productTypeId}:`, error.response?.data || error.message);
    throw error.response?.data || error;
  }
};

/**
 * Atualiza um tipo de produto existente.
 * @param {number} productTypeId - O ID do tipo de produto a ser atualizado.
 * @param {object} productTypeUpdateData - Dados para atualização (schemas.ProductTypeUpdate).
 * @returns {Promise<object>} O tipo de produto atualizado.
 */
export const updateProductType = async (productTypeId, productTypeUpdateData) => {
  try {
    const response = await axiosInstance.put(`${PRODUCT_TYPES_ENDPOINT}/${productTypeId}`, productTypeUpdateData);
    return response.data;
  } catch (error) {
    console.error(`Erro ao atualizar tipo de produto ${productTypeId}:`, error.response?.data || error.message);
    throw error.response?.data || error;
  }
};

/**
 * Deleta um tipo de produto.
 * @param {number} productTypeId - O ID do tipo de produto a ser deletado.
 * @returns {Promise<void>}
 */
export const deleteProductType = async (productTypeId) => {
  try {
    await axiosInstance.delete(`${PRODUCT_TYPES_ENDPOINT}/${productTypeId}`);
  } catch (error) {
    console.error(`Erro ao deletar tipo de produto ${productTypeId}:`, error.response?.data || error.message);
    throw error.response?.data || error;
  }
};

// --- Serviços para Atributos de Template (AttributeTemplate) ---

/**
 * Cria um novo atributo de template para um tipo de produto.
 * @param {number} productTypeId - O ID do tipo de produto pai.
 * @param {object} attributeTemplateData - Dados para o novo atributo (schemas.AttributeTemplateCreate).
 * @returns {Promise<object>} O atributo de template criado.
 */
export const createAttributeTemplate = async (productTypeId, attributeTemplateData) => {
  try {
    const response = await axiosInstance.post(`${PRODUCT_TYPES_ENDPOINT}/${productTypeId}/attributes/`, attributeTemplateData);
    return response.data;
  } catch (error) {
    console.error(`Erro ao criar atributo para o tipo de produto ${productTypeId}:`, error.response?.data || error.message);
    throw error.response?.data || error;
  }
};

/**
 * Lista os atributos de template para um tipo de produto específico.
 * @param {number} productTypeId - O ID do tipo de produto pai.
 * @param {object} params - Parâmetros de paginação.
 * @param {number} [params.skip=0] - Número de itens a pular.
 * @param {number} [params.limit=100] - Número máximo de itens a retornar.
 * @returns {Promise<Array<object>>} Uma lista de atributos de template.
 */
export const getAttributeTemplates = async (productTypeId, { skip = 0, limit = 100 } = {}) => {
  try {
    const response = await axiosInstance.get(`${PRODUCT_TYPES_ENDPOINT}/${productTypeId}/attributes/`, {
      params: { skip, limit },
    });
    return response.data;
  } catch (error) {
    console.error(`Erro ao buscar atributos para o tipo de produto ${productTypeId}:`, error.response?.data || error.message);
    throw error.response?.data || error;
  }
};

/**
 * Atualiza um atributo de template existente.
 * @param {number} productTypeId - O ID do tipo de produto pai.
 * @param {number} attributeId - O ID do atributo a ser atualizado.
 * @param {object} attributeTemplateUpdateData - Dados para atualização (schemas.AttributeTemplateUpdate).
 * @returns {Promise<object>} O atributo de template atualizado.
 */
export const updateAttributeTemplate = async (productTypeId, attributeId, attributeTemplateUpdateData) => {
  try {
    const response = await axiosInstance.put(`${PRODUCT_TYPES_ENDPOINT}/${productTypeId}/attributes/${attributeId}/`, attributeTemplateUpdateData);
    return response.data;
  } catch (error)
{
    console.error(`Erro ao atualizar atributo ${attributeId} para o tipo de produto ${productTypeId}:`, error.response?.data || error.message);
    throw error.response?.data || error;
  }
};

/**
 * Deleta um atributo de template.
 * @param {number} productTypeId - O ID do tipo de produto pai.
 * @param {number} attributeId - O ID do atributo a ser deletado.
 * @returns {Promise<void>}
 */
export const deleteAttributeTemplate = async (productTypeId, attributeId) => {
  try {
    await axiosInstance.delete(`${PRODUCT_TYPES_ENDPOINT}/${productTypeId}/attributes/${attributeId}/`);
  } catch (error) {
    console.error(`Erro ao deletar atributo ${attributeId} para o tipo de produto ${productTypeId}:`, error.response?.data || error.message);
    throw error.response?.data || error;
  }
};

// Exporta um objeto com todos os métodos do serviço para facilitar a importação
const productTypeService = {
  createProductType,
  getProductTypes,
  getProductTypeById,
  updateProductType,
  deleteProductType,
  createAttributeTemplate,
  getAttributeTemplates,
  updateAttributeTemplate,
  deleteAttributeTemplate,
};

export default productTypeService;