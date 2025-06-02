// Frontend/app/src/contexts/ProductTypeContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import productTypeService from '../services/productTypeService';
import { useAuth } from './AuthContext';

// 1. Criar o Contexto (NÃO EXPORTAR DIRETAMENTE PARA MELHORAR COMPATIBILIDADE COM HMR)
const ProductTypeContext = createContext(null); // Inicializado como null

// 2. Criar um Hook customizado para facilitar o uso do contexto (JÁ EXPORTADO)
export const useProductTypes = () => {
  const context = useContext(ProductTypeContext);
  if (context === null) { // Verifica se o contexto ainda é null (não está dentro de um Provider)
    throw new Error('useProductTypes deve ser usado dentro de um ProductTypeProvider');
  }
  return context;
};

// 3. Criar o Componente Provider (JÁ EXPORTADO)
export const ProductTypeProvider = ({ children }) => {
  const [productTypes, setProductTypes] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const { user, isSessionLoading: isAuthSessionLoading } = useAuth();

  const fetchProductTypes = useCallback(async () => {
    if (!user) {
      console.log("ProductTypeContext: Usuário não autenticado, não buscando tipos de produto.");
      setProductTypes([]); // Limpa os tipos se não houver usuário
      setIsLoading(false);
      setError(null); // Limpa erros anteriores se o usuário deslogar
      return;
    }

    console.log("ProductTypeContext: Usuário autenticado, buscando tipos de produto...");
    setIsLoading(true);
    setError(null);
    try {
      const data = await productTypeService.getProductTypes();
      console.log("ProductTypeContext: Tipos de produto recebidos:", data);
      setProductTypes(Array.isArray(data) ? data : []);
    } catch (err) {
      const errorData = err.response?.data || { message: err.message || "Erro desconhecido" };
      console.error("ProductTypeContext: Falha ao buscar tipos de produto:", errorData, err);
      setError(errorData);
      setProductTypes([]);
    } finally {
      setIsLoading(false);
    }
  }, [user]); // 'user' é a dependência chave

  useEffect(() => {
    // Só tenta buscar se a sessão de autenticação foi verificada
    if (!isAuthSessionLoading) {
      if (user) {
        console.log("ProductTypeContext: AuthContext carregado e usuário existe, chamando fetchProductTypes.");
        fetchProductTypes();
      } else {
        console.log("ProductTypeContext: AuthContext carregado, mas nenhum usuário logado. Limpando tipos de produto.");
        setProductTypes([]);
        setError(null); // Limpa erros se não houver usuário
      }
    }
  }, [user, isAuthSessionLoading, fetchProductTypes]);

  const addProductType = async (productTypeData) => {
    if (!user) {
      const authError = { detail: "Usuário não autenticado para adicionar tipo de produto." };
      setError(authError);
      throw authError; // Lança um objeto de erro consistente
    }
    setIsLoading(true);
    try {
      const newProductType = await productTypeService.createProductType(productTypeData);
      await fetchProductTypes(); // Recarrega após adicionar
      return newProductType;
    } catch (err) {
      const errorData = err.response?.data || { detail: err.message || "Falha ao adicionar tipo" };
      console.error("ProductTypeContext: Falha ao adicionar tipo de produto:", errorData, err);
      setError(errorData);
      throw err; // Relança o erro original ou o erro processado
    } finally {
      setIsLoading(false);
    }
  };

  const updateExistingProductType = async (productTypeId, productTypeUpdateData) => {
    if (!user) {
      const authError = { detail: "Usuário não autenticado para atualizar tipo de produto." };
      setError(authError);
      throw authError;
    }
    setIsLoading(true);
    try {
      const updatedProductType = await productTypeService.updateProductType(productTypeId, productTypeUpdateData);
      await fetchProductTypes();
      return updatedProductType;
    } catch (err) {
      const errorData = err.response?.data || { detail: err.message || "Falha ao atualizar tipo" };
      console.error("ProductTypeContext: Falha ao atualizar tipo de produto:", errorData, err);
      setError(errorData);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const removeProductType = async (productTypeId) => {
    if (!user) {
      const authError = { detail: "Usuário não autenticado para remover tipo de produto." };
      setError(authError);
      throw authError;
    }
    setIsLoading(true);
    try {
      await productTypeService.deleteProductType(productTypeId);
      await fetchProductTypes();
    } catch (err) {
      const errorData = err.response?.data || { detail: err.message || "Falha ao remover tipo" };
      console.error("ProductTypeContext: Falha ao remover tipo de produto:", errorData, err);
      setError(errorData);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const contextValue = {
    productTypes,
    isLoading,
    error,
    reloadProductTypes: fetchProductTypes,
    addProductType,
    updateExistingProductType,
    removeProductType
  };

  return (
    <ProductTypeContext.Provider value={contextValue}>
      {children}
    </ProductTypeContext.Provider>
  );
};