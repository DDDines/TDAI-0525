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
} from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import productTypeService from '../services/productTypeService';
import { showErrorToast, showSuccessToast } from '../utils/notifications';
import { useAuth } from './AuthContext';
import logger from '../utils/logger';
import { queryKeys } from '../lib/queryKeys.js';

const ProductTypeContext = createContext(null);

function sortProductTypes(productTypes) {
  return [...productTypes].sort((a, b) => a.friendly_name.localeCompare(b.friendly_name));
}

function filterOutProductType(prevTypes, id) {
  return prevTypes.filter((pt) => pt.id !== id);
}

function resolveProductTypeErrorMessage(error) {
  return (
    error?.response?.data?.detail ||
    error?.message ||
    'Falha ao carregar tipos de produto.'
  );
}

function ProductTypeProvider({ children }) {
  const { user, isLoading: isAuthSessionLoading } = useAuth();
  const queryClient = useQueryClient();
  const productTypesQueryKey = queryKeys.productTypes();

  const isQueryEnabled = !isAuthSessionLoading && Boolean(user);

  const productTypesQuery = useQuery({
    queryKey: productTypesQueryKey,
    enabled: isQueryEnabled,
    queryFn: async () => {
      logger.log('ProductTypeContext: Iniciando busca de tipos de produto (usuÃ¡rio autenticado).');
      const data = await productTypeService.getProductTypes({ skip: 0, limit: 500 });
      if (Array.isArray(data)) {
        logger.log('ProductTypeContext: Tipos de produto recebidos:', data.length);
        return sortProductTypes(data);
      }
      console.warn('ProductTypeContext: Resposta de getProductTypes nÃ£o era um array. Data:', data);
      return [];
    },
  });

  const setProductTypesCache = useCallback((updater) => {
    queryClient.setQueryData(productTypesQueryKey, (previous = []) => {
      const safePrevious = Array.isArray(previous) ? previous : [];
      const nextValue = typeof updater === 'function' ? updater(safePrevious) : updater;
      return sortProductTypes(Array.isArray(nextValue) ? nextValue : []);
    });
  }, [productTypesQueryKey, queryClient]);

  const addProductTypeMutation = useMutation({
    mutationFn: (productTypeData) => productTypeService.createProductType(productTypeData),
    onSuccess: (newProductType) => {
      setProductTypesCache((prevTypes) => [...prevTypes, newProductType]);
      showSuccessToast('Tipo de produto adicionado com sucesso!');
    },
  });

  const updateProductTypeMutation = useMutation({
    mutationFn: ({ id, productTypeData }) =>
      productTypeService.updateProductType(id, productTypeData),
    onSuccess: (updatedProductType, variables) => {
      setProductTypesCache((prevTypes) =>
        prevTypes.map((pt) => (pt.id === variables.id ? updatedProductType : pt))
      );
      showSuccessToast('Tipo de produto atualizado com sucesso!');
    },
  });

  const removeProductTypeMutation = useMutation({
    mutationFn: (id) => productTypeService.deleteProductType(id),
    onSuccess: (_, removedId) => {
      setProductTypesCache((prevTypes) => filterOutProductType(prevTypes, removedId));
      showSuccessToast('Tipo de produto removido com sucesso!');
    },
  });

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
      logger.log('ProductTypeContext: AuthContext carregado e usuÃ¡rio existe, query habilitada.');
      return;
    }

    logger.log('ProductTypeContext: AuthContext carregado, mas nenhum usuÃ¡rio logado (user Ã© null). Limpando tipos de produto.');
    queryClient.removeQueries({ queryKey: productTypesQueryKey, exact: true });
  }, [isAuthSessionLoading, productTypesQueryKey, queryClient, user]);

  const refreshProductTypes = useCallback(() => {
    logger.log('ProductTypeContext: Chamada para refreshProductTypes.');
    if (user) {
      void productTypesQuery.refetch();
    } else {
      console.warn('ProductTypeContext: Tentativa de refreshProductTypes sem usuÃ¡rio autenticado.');
    }
  }, [productTypesQuery, user]);

  const addProductType = useCallback(
    async (productTypeData) => {
      if (!user) {
        showErrorToast('VocÃª precisa estar logado para adicionar um tipo de produto.');
        throw new Error('UsuÃ¡rio nÃ£o autenticado');
      }
      logger.log('ProductTypeContext: Adicionando novo tipo de produto:', productTypeData);
      try {
        return await addProductTypeMutation.mutateAsync(productTypeData);
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
        return await updateProductTypeMutation.mutateAsync({ id, productTypeData });
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
        await removeProductTypeMutation.mutateAsync(id);
      } catch (err) {
        const errorMessage = err.response?.data?.detail || err.message || 'Falha ao remover tipo de produto.';
        console.error(`ProductTypeContext: Erro ao remover tipo de produto ID ${id}:`, errorMessage, err);
        showErrorToast(errorMessage);
        throw err;
      }
    },
    [removeProductTypeMutation, user]
  );

  const productTypes = Array.isArray(productTypesQuery.data) ? productTypesQuery.data : [];
  const isLoading = isQueryEnabled ? productTypesQuery.isLoading || productTypesQuery.isFetching : false;
  const error = isQueryEnabled && productTypesQuery.error
    ? resolveProductTypeErrorMessage(productTypesQuery.error)
    : null;

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
