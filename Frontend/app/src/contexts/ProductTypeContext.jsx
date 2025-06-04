// Frontend/app/src/contexts/ProductTypeContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import productTypeService from '../services/productTypeService';
import { showErrorToast, showSuccessToast } from '../utils/notifications';
import { useAuth } from './AuthContext'; // Importar useAuth para acessar o estado de autenticação

const ProductTypeContext = createContext(null);

export const ProductTypeProvider = ({ children }) => {
  const [productTypes, setProductTypes] = useState([]);
  const [isLoading, setIsLoading] = useState(false); // Iniciar como false, só carrega se autenticado
  const [error, setError] = useState(null);
  const { user, isLoading: isAuthSessionLoading } = useAuth(); // Obtém usuário e estado de carregamento da autenticação

  const fetchProductTypes = useCallback(async () => {
    // Adicionada verificação explícita do usuário aqui também, embora o useEffect já faça.
    if (!user) {
      console.log("ProductTypeContext: Usuário não autenticado (ou nulo), não buscando tipos de produto em fetchProductTypes.");
      setProductTypes([]); // Limpa se não houver usuário
      setIsLoading(false); // Garante que o loading pare
      setError(null);
      return;
    }

    console.log("ProductTypeContext: Iniciando busca de tipos de produto (usuário autenticado).");
    setIsLoading(true);
    setError(null);
    try {
      const data = await productTypeService.getProductTypes({ skip: 0, limit: 500 }); 
      if (data && Array.isArray(data.items)) {
        console.log("ProductTypeContext: Tipos de produto recebidos:", data.items.length);
        setProductTypes(data.items);
      } else {
        console.warn("ProductTypeContext: Resposta de getProductTypes não continha 'items' ou não era um array. Data:", data);
        setProductTypes([]);
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Falha ao carregar tipos de produto.';
      console.error("ProductTypeContext: Erro ao buscar tipos de produto:", errorMessage, err);
      setError(errorMessage);
      // Removido showErrorToast daqui para evitar barulho excessivo na carga inicial se houver falha antes do usuário interagir.
      // A página que consome o contexto pode decidir mostrar o erro.
      setProductTypes([]);
    } finally {
      setIsLoading(false);
      console.log("ProductTypeContext: Busca de tipos de produto finalizada.");
    }
  }, [user]); // Dependência 'user' é crucial aqui

  useEffect(() => {
    console.log("ProductTypeContext useEffect: user mudou ou isAuthSessionLoading mudou.");
    console.log("ProductTypeContext useEffect: isAuthSessionLoading:", isAuthSessionLoading, "user:", user ? user.email : null);

    // Só tenta buscar se a sessão de autenticação foi completamente verificada (não está mais carregando)
    if (!isAuthSessionLoading) {
      if (user) { // E se o usuário existir (está logado e os dados do usuário foram carregados)
        console.log("ProductTypeContext: AuthContext carregado e usuário existe, chamando fetchProductTypes.");
        fetchProductTypes();
      } else {
        console.log("ProductTypeContext: AuthContext carregado, mas nenhum usuário logado (user é null). Limpando tipos de produto.");
        setProductTypes([]); // Limpa os tipos se não houver usuário
        setError(null);      // Limpa erros anteriores
        setIsLoading(false); // Garante que o estado de loading seja resetado
      }
    } else {
        console.log("ProductTypeContext: Aguardando AuthContext carregar (isAuthSessionLoading é true).");
        // Opcional: definir productTypes como [] e isLoading como true se a sessão de auth ainda está carregando
        // setProductTypes([]);
        // setIsLoading(true); 
    }
  }, [user, isAuthSessionLoading, fetchProductTypes]);

  const refreshProductTypes = useCallback(() => {
    console.log("ProductTypeContext: Chamada para refreshProductTypes.");
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
    console.log("ProductTypeContext: Adicionando novo tipo de produto:", productTypeData);
    // setIsLoading(true); // Opcional: loading específico para esta ação
    try {
      const newProductType = await productTypeService.createProductType(productTypeData);
      // refreshProductTypes(); // Recarrega toda a lista para garantir consistência
      setProductTypes(prevTypes => [...prevTypes, newProductType].sort((a, b) => a.friendly_name.localeCompare(b.friendly_name)));
      showSuccessToast('Tipo de produto adicionado com sucesso!');
      return newProductType;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Falha ao adicionar tipo de produto.';
      console.error("ProductTypeContext: Erro ao adicionar tipo de produto:", errorMessage, err);
      showErrorToast(errorMessage);
      throw err;
    } finally {
      // setIsLoading(false);
    }
  }, [user /*, refreshProductTypes ou setProductTypes */]);

  const updateProductType = useCallback(async (id, productTypeData) => {
    if (!user) {
        showErrorToast("Você precisa estar logado para atualizar um tipo de produto.");
        throw new Error("Usuário não autenticado");
    }
    console.log(`ProductTypeContext: Atualizando tipo de produto ID ${id}:`, productTypeData);
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
  }, [user /*, setProductTypes */]);

  const removeProductType = useCallback(async (id) => {
    if (!user) {
        showErrorToast("Você precisa estar logado para remover um tipo de produto.");
        throw new Error("Usuário não autenticado");
    }
    console.log(`ProductTypeContext: Removendo tipo de produto ID ${id}`);
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
  }, [user /*, setProductTypes */]);

  const value = {
    productTypes,
    isLoading, // Este isLoading é do ProductTypeContext
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