// Frontend/app/src/pages/TiposProdutoPage.jsx
import React, { useEffect, useState } from 'react';
import { useProductTypes } from '../contexts/ProductTypeContext'; // Usar o hook do contexto
import { showErrorToast, showSuccessToast } from '../utils/notifications';
// import productTypeService from '../services/productTypeService'; // Será usado para criar/editar/deletar

// Estilos básicos (podem ser movidos para um arquivo CSS)
const pageStyles = {
  container: { padding: '20px' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' },
  title: { fontSize: '1.8rem', fontWeight: '600' },
  button: { backgroundColor: 'var(--primary)', color: 'white', padding: '10px 18px', border: 'none', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: '0.95rem' },
  table: { width: '100%', borderCollapse: 'collapse', marginTop: '20px' },
  th: { backgroundColor: '#f9fafb', padding: '12px', borderBottom: '1px solid var(--border-color)', textAlign: 'left', fontWeight: '600' },
  td: { padding: '12px', borderBottom: '1px solid var(--border-color)', textAlign: 'left' },
  actionsCell: { display: 'flex', gap: '10px' },
  actionButton: { padding: '6px 10px', fontSize: '0.85rem', borderRadius: 'var(--radius-sm)', cursor: 'pointer' },
  editButton: { backgroundColor: 'var(--info-light)', color: 'var(--info)', border: '1px solid var(--info)'},
  deleteButton: { backgroundColor: 'var(--danger-light)', color: 'var(--danger)', border: '1px solid var(--danger)'},
  // Estilos para o modal de novo tipo de produto
  modal: { position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1050 },
  modalContent: { backgroundColor: 'white', padding: '25px', borderRadius: 'var(--radius-lg)', width: '90%', maxWidth: '500px' },
  modalFormGroup: { marginBottom: '15px' },
  modalLabel: { display: 'block', marginBottom: '5px', fontWeight: '500'},
  modalInput: { width: '100%', padding: '10px', border: '1px solid var(--border-color)', borderRadius: 'var(--radius)', boxSizing: 'border-box'},
  modalActions: { marginTop: '20px', display: 'flex', justifyContent: 'flex-end', gap: '10px' },
  modalButton: { padding: '10px 15px', border: 'none', borderRadius: 'var(--radius)', cursor: 'pointer'},
  modalSaveButton: { backgroundColor: 'var(--success)', color: 'white' },
  modalCancelButton: { backgroundColor: 'var(--disabled-bg)', color: '#333' }
};

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
    return <div style={pageStyles.container}>Carregando tipos de produto...</div>;
  }

  if (error) {
    return <div style={pageStyles.container}>Erro ao carregar tipos de produto: {error.message || error.detail}</div>;
  }

  return (
    <div style={pageStyles.container}>
      <div style={pageStyles.header}>
        <h1 style={pageStyles.title}>Gerenciar Tipos de Produto</h1>
        <button onClick={handleOpenNewTypeModal} style={pageStyles.button}>
          + Novo Tipo de Produto
        </button>
      </div>

      {productTypes.length === 0 && !isLoading && (
        <p>Nenhum tipo de produto cadastrado ainda. Clique em "+ Novo Tipo de Produto" para começar.</p>
      )}

      {productTypes.length > 0 && (
        <table style={pageStyles.table}>
          <thead>
            <tr>
              <th style={pageStyles.th}>ID</th>
              <th style={pageStyles.th}>Chave (key_name)</th>
              <th style={pageStyles.th}>Nome Amigável</th>
              <th style={pageStyles.th}>Nº de Atributos</th>
              <th style={pageStyles.th}>Ações</th>
            </tr>
          </thead>
          <tbody>
            {productTypes.map((type) => (
              <tr key={type.id}>
                <td style={pageStyles.td}>{type.id}</td>
                <td style={pageStyles.td}>{type.key_name}</td>
                <td style={pageStyles.td}>{type.friendly_name}</td>
                <td style={pageStyles.td}>{type.attribute_templates?.length || 0}</td>
                <td style={pageStyles.td}>
                  <div style={pageStyles.actionsCell}>
                    <button 
                        onClick={() => alert(`Editar tipo ID: ${type.id} - Funcionalidade pendente.`)}
                        style={{...pageStyles.actionButton, ...pageStyles.editButton}}
                        title="Editar Tipo e Atributos"
                    >
                        ✏️ Editar
                    </button>
                    <button 
                        onClick={() => handleDeleteType(type.id, type.friendly_name)}
                        style={{...pageStyles.actionButton, ...pageStyles.deleteButton}}
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
      )}

      {/* Modal para Novo Tipo de Produto */}
      {isNewTypeModalOpen && (
        <div style={pageStyles.modal}>
          <div style={pageStyles.modalContent}>
            <h2>Novo Tipo de Produto</h2>
            <div style={pageStyles.modalFormGroup}>
              <label htmlFor="type-key-name" style={pageStyles.modalLabel}>Chave (Identificador Único)*:</label>
              <input
                type="text"
                id="type-key-name"
                value={newTypeKeyName}
                onChange={(e) => setNewTypeKeyName(e.target.value)}
                style={pageStyles.modalInput}
                placeholder="Ex: eletronicos, vestuario_camisetas"
                disabled={isSubmitting}
              />
            </div>
            <div style={pageStyles.modalFormGroup}>
              <label htmlFor="type-friendly-name" style={pageStyles.modalLabel}>Nome Amigável*:</label>
              <input
                type="text"
                id="type-friendly-name"
                value={newTypeFriendlyName}
                onChange={(e) => setNewTypeFriendlyName(e.target.value)}
                style={pageStyles.modalInput}
                placeholder="Ex: Eletrônicos, Camisetas (Vestuário)"
                disabled={isSubmitting}
              />
            </div>
            <div style={pageStyles.modalActions}>
              <button onClick={handleCloseNewTypeModal} style={{...pageStyles.modalButton, ...pageStyles.modalCancelButton}} disabled={isSubmitting}>
                Cancelar
              </button>
              <button onClick={handleSaveNewType} style={{...pageStyles.modalButton, ...pageStyles.modalSaveButton}} disabled={isSubmitting}>
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