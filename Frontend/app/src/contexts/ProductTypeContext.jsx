/**
 * Module product type context.
 *
 * Defines responsibilities and integration points for contexts.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import productTypeService from '../services/productTypeService';
import { showErrorToast, showSuccessToast } from '../utils/notifications';
import { useAuth } from './AuthContext';
import logger from '../utils/logger';

const ProductTypeContext = createContext(null);

function filterOutProductType(prevTypes, id) {
  return prevTypes.filter((pt) => pt.id !== id);
}

function ProductTypeProvider({ children }) {
  const [productTypes, setProductTypes] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const { user, isLoading: isAuthSessionLoading } = useAuth();

  const fetchProductTypes = useCallback(async () => {
    logger.log('ProductTypeContext: Iniciando busca de tipos de produto (usuÃ¡rio autenticado).');
    setIsLoading(true);
    setError(null);
    try {
      const data = await productTypeService.getProductTypes({ skip: 0, limit: 500 });
      if (Array.isArray(data)) {
        logger.log('ProductTypeContext: Tipos de produto recebidos:', data.length);
        setProductTypes(data);
      } else {
        console.warn('ProductTypeContext: Resposta de getProductTypes nÃ£o era um array. Data:', data);
        setProductTypes([]);
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Falha ao carregar tipos de produto.';
      console.error('ProductTypeContext: Erro ao buscar tipos de produto:', errorMessage, err);
      setError(errorMessage);
      setProductTypes([]);
    } finally {
      setIsLoading(false);
      logger.log('ProductTypeContext: Busca de tipos de produto finalizada.');
    }
  }, []);

  useEffect(() => {
    logger.log('ProductTypeContext useEffect: user mudou ou isAuthSessionLoading mudou.');
    logger.log(
      'ProductTypeContext useEffect: isAuthSessionLoading:',
      isAuthSessionLoading,
      'user:',
      user ? user.email : null
    );

    if (isAuthSessionLoading) {
      logger.log('ProductTypeContext: Aguardando AuthContext carregar (isAuthSessionLoading Ã© true).');
      return;
    }

    if (user) {
      logger.log('ProductTypeContext: AuthContext carregado e usuÃ¡rio existe, chamando fetchProductTypes.');
      void fetchProductTypes();
      return;
    }

    logger.log('ProductTypeContext: AuthContext carregado, mas nenhum usuÃ¡rio logado (user Ã© null). Limpando tipos de produto.');
    setProductTypes([]);
    setError(null);
    setIsLoading(false);
  }, [fetchProductTypes, isAuthSessionLoading, user]);

  const refreshProductTypes = useCallback(() => {
    logger.log('ProductTypeContext: Chamada para refreshProductTypes.');
    if (user) {
      void fetchProductTypes();
    } else {
      console.warn('ProductTypeContext: Tentativa de refreshProductTypes sem usuÃ¡rio autenticado.');
    }
  }, [fetchProductTypes, user]);

  const addProductType = useCallback(
    async (productTypeData) => {
      if (!user) {
        showErrorToast('VocÃª precisa estar logado para adicionar um tipo de produto.');
        throw new Error('UsuÃ¡rio nÃ£o autenticado');
      }
      logger.log('ProductTypeContext: Adicionando novo tipo de produto:', productTypeData);
      try {
        const newProductType = await productTypeService.createProductType(productTypeData);
        setProductTypes((prevTypes) =>
          [...prevTypes, newProductType].sort((a, b) => a.friendly_name.localeCompare(b.friendly_name))
        );
        showSuccessToast('Tipo de produto adicionado com sucesso!');
        return newProductType;
      } catch (err) {
        const errorMessage = err.response?.data?.detail || err.message || 'Falha ao adicionar tipo de produto.';
        console.error('ProductTypeContext: Erro ao adicionar tipo de produto:', errorMessage, err);
        showErrorToast(errorMessage);
        throw err;
      }
    },
    [user]
  );

  const updateProductType = useCallback(
    async (id, productTypeData) => {
      if (!user) {
        showErrorToast('VocÃª precisa estar logado para atualizar um tipo de produto.');
        throw new Error('UsuÃ¡rio nÃ£o autenticado');
      }
      logger.log(`ProductTypeContext: Atualizando tipo de produto ID ${id}:`, productTypeData);
      try {
        const updatedProductType = await productTypeService.updateProductType(id, productTypeData);
        setProductTypes((prevTypes) =>
          prevTypes
            .map((pt) => (pt.id === id ? updatedProductType : pt))
            .sort((a, b) => a.friendly_name.localeCompare(b.friendly_name))
        );
        showSuccessToast('Tipo de produto atualizado com sucesso!');
        return updatedProductType;
      } catch (err) {
        const errorMessage = err.response?.data?.detail || err.message || 'Falha ao atualizar tipo de produto.';
        console.error(`ProductTypeContext: Erro ao atualizar tipo de produto ID ${id}:`, errorMessage, err);
        showErrorToast(errorMessage);
        throw err;
      }
    },
    [user]
  );

  const removeProductType = useCallback(
    async (id) => {
      if (!user) {
        showErrorToast('VocÃª precisa estar logado para remover um tipo de produto.');
        throw new Error('UsuÃ¡rio nÃ£o autenticado');
      }
      logger.log(`ProductTypeContext: Removendo tipo de produto ID ${id}`);
      try {
        await productTypeService.deleteProductType(id);
        setProductTypes(filterOutProductType(productTypes, id));
        showSuccessToast('Tipo de produto removido com sucesso!');
      } catch (err) {
        const errorMessage = err.response?.data?.detail || err.message || 'Falha ao remover tipo de produto.';
        console.error(`ProductTypeContext: Erro ao remover tipo de produto ID ${id}:`, errorMessage, err);
        showErrorToast(errorMessage);
        throw err;
      }
    },
    [productTypes, user]
  );

  const value = {
    productTypes,
    isLoading,
    error,
    refreshProductTypes,
    addProductType,
    updateProductType,
    removeProductType,
  };

  return <ProductTypeContext.Provider value={value}>{children}</ProductTypeContext.Provider>;
}

function useProductTypes() {
  const context = useContext(ProductTypeContext);
  if (context === undefined || context === null) {
    throw new Error('useProductTypes deve ser usado dentro de um ProductTypeProvider');
  }
  return context;
}

export { ProductTypeProvider, useProductTypes };
