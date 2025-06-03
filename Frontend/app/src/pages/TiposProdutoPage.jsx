// Frontend/app/src/pages/TiposProdutoPage.jsx
import React, { useEffect, useState } from 'react';
import { useProductTypes } from '../contexts/ProductTypeContext'; // Usar o hook do contexto
import { showErrorToast, showSuccessToast } from '../utils/notifications';
// Importa o arquivo CSS recém-criado
import './TiposProdutoPage.css';

function TiposProdutoPage() {
  const { productTypes, isLoading, error, reloadProductTypes, addProductType, removeProductType } = useProductTypes();
  const [isNewTypeModalOpen, setIsNewTypeModalOpen] = useState(false);
  const [newTypeKeyName, setNewTypeKeyName] = useState('');
  const [newTypeFriendlyName, setNewTypeFriendlyName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    // O contexto já busca os tipos na inicialização se o usuário estiver logado.
    // Podemos adicionar um reloadProductTypes() aqui se quisermos forçar uma atualização ao montar a página,
    // mas geralmente não é necessário se o contexto estiver gerenciando bem.
  }, []);

  const handleOpenNewTypeModal = () => {
    setNewTypeKeyName('');
    setNewTypeFriendlyName('');
    setIsNewTypeModalOpen(true);
  };

  const handleCloseNewTypeModal = () => {
    setIsNewTypeModalOpen(false);
  };

  const handleSaveNewType = async () => {
    if (!newTypeKeyName.trim() || !newTypeFriendlyName.trim()) {
      showErrorToast("Chave e Nome Amigável são obrigatórios.");
      return;
    }
    setIsSubmitting(true);
    try {
      await addProductType({
        key_name: newTypeKeyName.trim(),
        friendly_name: newTypeFriendlyName.trim()
      });
      showSuccessToast("Tipo de Produto criado com sucesso!");
      handleCloseNewTypeModal();
      // reloadProductTypes(); // O addProductType no contexto já faz o reload
    } catch (err) {
      showErrorToast(err.message || err.detail || "Falha ao criar Tipo de Produto.");
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleDeleteType = async (typeId, typeName) => {
      if(window.confirm(`Tem certeza que deseja deletar o tipo de produto "${typeName}" (ID: ${typeId})? Isso não poderá ser desfeito.`)){
          try {
              await removeProductType(typeId);
              showSuccessToast(`Tipo de produto "${typeName}" deletado com sucesso.`);
              // A lista será atualizada pelo contexto
          } catch (err) {
              showErrorToast(err.message || err.detail || `Falha ao deletar o tipo "${typeName}". Verifique se ele não está em uso.`);
          }
      }
  }

  if (isLoading && productTypes.length === 0) {
    return <div className="loading-message">Carregando tipos de produto...</div>;
  }

  if (error) {
    return <div className="error-message">Erro ao carregar tipos de produto: {error.message || error.detail}</div>;
  }

  return (
    <div className="tipos-produto-container">
      <div className="tipos-produto-header">
        <h1 className="tipos-produto-title">Gerenciar Tipos de Produto</h1>
        <button onClick={handleOpenNewTypeModal} className="tipos-produto-button">
          + Novo Tipo de Produto
        </button>
      </div>

      {productTypes.length === 0 && !isLoading && (
        <p>Nenhum tipo de produto cadastrado ainda. Clique em "+ Novo Tipo de Produto" para começar.</p>
      )}

      {productTypes.length > 0 && (
        <div className="card"> {/* Adiciona a classe card aqui para o estilo de caixa */}
            <div className="card-header"> {/* Adiciona a classe card-header para o cabeçalho da tabela */}
                <h3>Lista de Tipos de Produto</h3> {/* Título do card */}
            </div>
            <table className="tipos-produto-table">
            <thead>
                <tr>
                <th className="tipos-produto-table th">ID</th>
                <th className="tipos-produto-table th">Chave (key_name)</th>
                <th className="tipos-produto-table th">Nome Amigável</th>
                <th className="tipos-produto-table th">Nº de Atributos</th>
                <th className="tipos-produto-table th">Ações</th>
                </tr>
            </thead>
            <tbody>
                {productTypes.map((type) => (
                <tr key={type.id}>
                    <td className="tipos-produto-table td">{type.id}</td>
                    <td className="tipos-produto-table td">{type.key_name}</td>
                    <td className="tipos-produto-table td">{type.friendly_name}</td>
                    <td className="tipos-produto-table td">{type.attribute_templates?.length || 0}</td>
                    <td className="tipos-produto-table td">
                    <div className="tipos-produto-actions-cell">
                        <button 
                            onClick={() => alert(`Editar tipo ID: ${type.id} - Funcionalidade pendente.`)}
                            className="tipos-produto-action-button edit"
                            title="Editar Tipo e Atributos"
                        >
                            ✏️ Editar
                        </button>
                        <button 
                            onClick={() => handleDeleteType(type.id, type.friendly_name)}
                            className="tipos-produto-action-button delete"
                            title="Deletar Tipo"
                        >
                            🗑️ Deletar
                        </button>
                    </div>
                    </td>
                </tr>
                ))}
            </tbody>
            </table>
        </div> 
      )}

      {/* Modal para Novo Tipo de Produto */}
      {isNewTypeModalOpen && (
        <div className="tipos-produto-modal">
          <div className="tipos-produto-modal-content">
            <div className="tipos-produto-modal-header">
                <h2 className="tipos-produto-modal-header h2">Novo Tipo de Produto</h2>
                <button onClick={handleCloseNewTypeModal} className="tipos-produto-modal-close-button">×</button>
            </div>
            <div className="tipos-produto-form-group">
              <label htmlFor="type-key-name" className="tipos-produto-form-group label">Chave (Identificador Único)*:</label>
              <input
                type="text"
                id="type-key-name"
                value={newTypeKeyName}
                onChange={(e) => setNewTypeKeyName(e.target.value)}
                className="tipos-produto-form-group input"
                placeholder="Ex: eletronicos, vestuario_camisetas"
                disabled={isSubmitting}
              />
            </div>
            <div className="tipos-produto-form-group">
              <label htmlFor="type-friendly-name" className="tipos-produto-form-group label">Nome Amigável*:</label>
              <input
                type="text"
                id="type-friendly-name"
                value={newTypeFriendlyName}
                onChange={(e) => setNewTypeFriendlyName(e.target.value)}
                className="tipos-produto-form-group input"
                placeholder="Ex: Eletrônicos, Camisetas (Vestuário)"
                disabled={isSubmitting}
              />
            </div>
            <div className="tipos-produto-modal-actions">
              <button onClick={handleCloseNewTypeModal} className="tipos-produto-modal-button cancel" disabled={isSubmitting}>
                Cancelar
              </button>
              <button onClick={handleSaveNewType} className="tipos-produto-modal-button save" disabled={isSubmitting}>
                {isSubmitting ? 'Salvando...' : 'Salvar Tipo'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default TiposProdutoPage;
