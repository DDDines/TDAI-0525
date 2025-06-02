// Frontend/app/src/contexts/ProductTypeContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import productTypeService from '../services/productTypeService'; // Nosso serviço recém-criado

// 1. Criar o Contexto
export const ProductTypeContext = createContext(); // <--- CORREÇÃO: 'export' adicionado aqui

// 2. Criar um Hook customizado para facilitar o uso do contexto
export const useProductTypes = () => {
  const context = useContext(ProductTypeContext);
  if (!context) {
    throw new Error('useProductTypes deve ser usado dentro de um ProductTypeProvider');
  }
  return context;
};

// 3. Criar o Componente Provider
export const ProductTypeProvider = ({ children }) => {
  const [productTypes, setProductTypes] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Função para buscar/recarregar os tipos de produto
  const fetchProductTypes = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Usamos a função getProductTypes do nosso serviço.
      // Por padrão, ela buscará os tipos do usuário logado + globais.
      // Se precisarmos de 'listAllForAdmin', precisaríamos de lógica adicional aqui
      // para verificar o papel do usuário (talvez vindo de um AuthContext).
      // Por agora, vamos manter simples e buscar os tipos padrão.
      const data = await productTypeService.getProductTypes();
      setProductTypes(data || []); // Garante que seja um array mesmo se data for null/undefined
    } catch (err) {
      console.error("Falha ao buscar tipos de produto no contexto:", err);
      setError(err);
      setProductTypes([]); // Limpa os tipos em caso de erro
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Buscar os tipos de produto quando o provider for montado pela primeira vez
  useEffect(() => {
    fetchProductTypes();
  }, [fetchProductTypes]); // fetchProductTypes é estável devido ao useCallback

  // Funções para interagir com o serviço e atualizar o estado (opcional, mas útil)
  // Estas funções encapsulam a chamada ao serviço e o recarregamento dos dados.

  const addProductType = async (productTypeData, asGlobal = false) => {
    try {
      const newProductType = await productTypeService.createProductType(productTypeData, asGlobal);
      // Recarrega a lista após a criação bem-sucedida
      // Ou, para otimismo, adiciona diretamente à lista:
      // setProductTypes(prevTypes => [...prevTypes, newProductType]);
      // Mas recarregar garante consistência com o backend.
      await fetchProductTypes();
      return newProductType; // Retorna o tipo criado para feedback
    } catch (err) {
      console.error("Falha ao adicionar tipo de produto:", err);
      setError(err); // Define o erro no contexto se necessário
      throw err; // Relança o erro para o componente tratar
    }
  };

  const updateExistingProductType = async (productTypeId, productTypeUpdateData) => {
    try {
      const updatedProductType = await productTypeService.updateProductType(productTypeId, productTypeUpdateData);
      // Recarrega a lista ou atualiza o item específico
      // setProductTypes(prevTypes =>
      //   prevTypes.map(pt => (pt.id === productTypeId ? updatedProductType : pt))
      // );
      await fetchProductTypes();
      return updatedProductType;
    } catch (err) {
      console.error("Falha ao atualizar tipo de produto:", err);
      setError(err);
      throw err;
    }
  };

  const removeProductType = async (productTypeId) => {
    try {
      await productTypeService.deleteProductType(productTypeId);
      // Recarrega a lista ou remove o item
      // setProductTypes(prevTypes => prevTypes.filter(pt => pt.id !== productTypeId));
      await fetchProductTypes();
    } catch (err) {
      console.error("Falha ao remover tipo de produto:", err);
      setError(err);
      throw err;
    }
  };


  // O valor que o Provider vai fornecer aos seus componentes filhos
  const contextValue = {
    productTypes,
    isLoading,
    error,
    reloadProductTypes: fetchProductTypes, // Função para recarregar manualmente
    addProductType,                       // Função para criar e recarregar
    updateExistingProductType,            // Função para atualizar e recarregar
    removeProductType                     // Função para deletar e recarregar
  };

  return (
    <ProductTypeContext.Provider value={contextValue}>
      {children}
    </ProductTypeContext.Provider>
  );
};