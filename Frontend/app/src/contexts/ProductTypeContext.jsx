// Frontend/app/src/contexts/ProductTypeContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import productTypeService from '../services/productTypeService';
import { showErrorToast, showSuccessToast } from '../utils/notifications';
import { useAuth } from './AuthContext'; // Importar useAuth para acessar o estado de autenticação
import logger from '../utils/logger';

const ProductTypeContext = createContext(null);

export const ProductTypeProvider = ({ children }) => {
  const [productTypes, setProductTypes] = useState([]);
  const [isLoading, setIsLoading] = useState(false); // Iniciar como false, só carrega se autenticado
  const [error, setError] = useState(null);
  const { user, isLoading: isAuthSessionLoading } = useAuth(); // Obtém usuário e estado de carregamento da autenticação

  const fetchProductTypes = useCallback(async () => {
    // Adicionada verificação explícita do usuário aqui também, embora o useEffect já faça.
    if (!user) {
      logger.log("ProductTypeContext: Usuário não autenticado (ou nulo), não buscando tipos de produto em fetchProductTypes.");
      setProductTypes([]); // Limpa se não houver usuário
      setIsLoading(false); // Garante que o loading pare
      setError(null);
      return;
    }

    logger.log("ProductTypeContext: Iniciando busca de tipos de produto (usuário autenticado).");
    setIsLoading(true);
    setError(null);
    try {
      // O endpoint /product-types/ retorna diretamente uma LISTA de ProductTypeResponse
      const data = await productTypeService.getProductTypes({ skip: 0, limit: 500 }); 
      
      // FIX: Ajustar a condição para verificar se 'data' é um array diretamente
      if (data && Array.isArray(data)) { 
        logger.log("ProductTypeContext: Tipos de produto recebidos:", data.length);
        setProductTypes(data); 
      } else {
        console.warn("ProductTypeContext: Resposta de getProductTypes não era um array. Data:", data);
        setProductTypes([]);
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Falha ao carregar tipos de produto.';
      console.error("ProductTypeContext: Erro ao buscar tipos de produto:", errorMessage, err);
      setError(errorMessage);
      setProductTypes([]);
    } finally {
      setIsLoading(false);
      logger.log("ProductTypeContext: Busca de tipos de produto finalizada.");
    }
  }, [user]); // Dependência 'user' é crucial aqui

  useEffect(() => {
    logger.log("ProductTypeContext useEffect: user mudou ou isAuthSessionLoading mudou.");
    logger.log("ProductTypeContext useEffect: isAuthSessionLoading:", isAuthSessionLoading, "user:", user ? user.email : null);

    // Só tenta buscar se a sessão de autenticação foi completamente verificada (não está mais carregando)
    if (!isAuthSessionLoading) {
      if (user) { 
        logger.log("ProductTypeContext: AuthContext carregado e usuário existe, chamando fetchProductTypes.");
        fetchProductTypes();
      } else {
        logger.log("ProductTypeContext: AuthContext carregado, mas nenhum usuário logado (user é null). Limpando tipos de produto.");
        setProductTypes([]); // Limpa os tipos se não houver usuário
        setError(null);      // Limpa erros anteriores
        setIsLoading(false); // Garante que o estado de loading seja resetado
      }
    } else {
        logger.log("ProductTypeContext: Aguardando AuthContext carregar (isAuthSessionLoading é true).");
    }
  }, [user, isAuthSessionLoading, fetchProductTypes]);

  const refreshProductTypes = useCallback(() => {
    logger.log("ProductTypeContext: Chamada para refreshProductTypes.");
    if (user) { // Só recarrega se houver usuário
        fetchProductTypes();
    } else {
        console.warn("ProductTypeContext: Tentativa de refreshProductTypes sem usuário autenticado.");
    }
  }, [user, fetchProductTypes]);

  const addProductType = useCallback(async (productTypeData) => {
    if (!user) {
        showErrorToast("Você precisa estar logado para adicionar um tipo de produto.");
        throw new Error("Usuário não autenticado");
    }
    logger.log("ProductTypeContext: Adicionando novo tipo de produto:", productTypeData);
    try {
      const newProductType = await productTypeService.createProductType(productTypeData);
      setProductTypes(prevTypes => [...prevTypes, newProductType].sort((a, b) => a.friendly_name.localeCompare(b.friendly_name)));
      showSuccessToast('Tipo de produto adicionado com sucesso!');
      return newProductType;
    }
    // Consider adding a specific catch for IntegrityError if you want to show a more user-friendly message
    // for duplicate key_name, for example. The backend raises it.
    catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Falha ao adicionar tipo de produto.';
      console.error("ProductTypeContext: Erro ao adicionar tipo de produto:", errorMessage, err);
      showErrorToast(errorMessage);
      throw err;
    } finally {
    }
  }, [user]);

  const updateProductType = useCallback(async (id, productTypeData) => {
    if (!user) {
        showErrorToast("Você precisa estar logado para atualizar um tipo de produto.");
        throw new Error("Usuário não autenticado");
    }
    logger.log(`ProductTypeContext: Atualizando tipo de produto ID ${id}:`, productTypeData);
    try {
      const updatedProductType = await productTypeService.updateProductType(id, productTypeData);
      setProductTypes(prevTypes => 
        prevTypes.map(pt => (pt.id === id ? updatedProductType : pt)).sort((a, b) => a.friendly_name.localeCompare(b.friendly_name))
      );
      showSuccessToast('Tipo de produto atualizado com sucesso!');
      return updatedProductType;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Falha ao atualizar tipo de produto.';
      console.error(`ProductTypeContext: Erro ao atualizar tipo de produto ID ${id}:`, errorMessage, err);
      showErrorToast(errorMessage);
      throw err;
    }
  }, [user]);

  const removeProductType = useCallback(async (id) => {
    if (!user) {
        showErrorToast("Você precisa estar logado para remover um tipo de produto.");
        throw new Error("Usuário não autenticado");
    }
    logger.log(`ProductTypeContext: Removendo tipo de produto ID ${id}`);
    try {
      await productTypeService.deleteProductType(id);
      setProductTypes(prevTypes => prevTypes.filter(pt => pt.id !== id));
      showSuccessToast('Tipo de produto removido com sucesso!');
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Falha ao remover tipo de produto.';
      console.error(`ProductTypeContext: Erro ao remover tipo de produto ID ${id}:`, errorMessage, err);
      showErrorToast(errorMessage);
      throw err;
    }
  }, [user]);

  const value = {
    productTypes,
    isLoading, 
    error,
    refreshProductTypes,
    addProductType,
    updateProductType,
    removeProductType,
  };

  return (
    <ProductTypeContext.Provider value={value}>
      {children}
    </ProductTypeContext.Provider>
  );
};

export const useProductTypes = () => {
  const context = useContext(ProductTypeContext);
  if (context === undefined || context === null) { 
    throw new Error('useProductTypes deve ser usado dentro de um ProductTypeProvider');
  }
  return context;
};
