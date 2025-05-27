// Frontend/app/src/components/produtos/ProductEditModal.jsx
import React, { useState, useEffect } from 'react';

function ProductEditModal({ isOpen, onClose, productData, onSave, isLoading }) {
  const [formData, setFormData] = useState({});

  useEffect(() => {
    if (productData) {
      setFormData({
        nome_base: productData.nome_base || '',
        marca: productData.marca || '',
        categoria_original: productData.categoria_original || '',
        sku_original: productData.dados_brutos?.sku_original || '',
        // Manter uma cópia dos dados brutos originais para fazer merge
        // se não todos os campos de dados_brutos são explicitamente editáveis no formulário.
        dados_brutos_originais: productData.dados_brutos || {}
      });
    } else {
      // Limpa o formulário se não houver productData (ex: ao fechar o modal)
      setFormData({});
    }
  }, [productData]); // Dependência: productData

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = () => {
    // Prepara o payload para atualização, conforme o schema ProdutoUpdate do backend
    const updatePayload = {
        nome_base: formData.nome_base,
        marca: formData.marca || null, // Envia null se o campo estiver vazio
        categoria_original: formData.categoria_original || null,
        dados_brutos: {
            ...(formData.dados_brutos_originais || {}), // Preserva outros campos de dados_brutos
        }
    };

    // Adiciona/atualiza sku_original em dados_brutos apenas se houver valor
    if (formData.sku_original) {
        updatePayload.dados_brutos.sku_original = formData.sku_original;
    } else {
        // Se sku_original foi apagado no form, remove do payload ou define como null
        // dependendo de como o backend lida com isso.
        // Se a chave existir nos dados originais e foi apagada, pode ser necessário
        // enviar explicitamente null ou o backend precisa tratar a ausência da chave como remoção.
        // Por simplicidade, se estava lá e foi apagado, não será incluído aqui,
        // mas se quiser remover explicitamente do BD, precisaria de lógica adicional.
        // Se o campo nunca existiu e está vazio, não faz nada.
        // Se existia e foi esvaziado, e o backend espera `null` para limpar, então:
        // if (formData.dados_brutos_originais?.hasOwnProperty('sku_original') && !formData.sku_original) {
        //   updatePayload.dados_brutos.sku_original = null;
        // }
    }
    
    // Se dados_brutos ficou um objeto vazio e você não quer enviar `{}`
    if (Object.keys(updatePayload.dados_brutos).length === 0) {
        // delete updatePayload.dados_brutos; // Ou envie null, dependendo da API
        updatePayload.dados_brutos = null;
    }


    if (productData && productData.id) {
        onSave(productData.id, updatePayload);
    } else {
        console.error("Product ID is missing, cannot save.");
        alert("Erro: ID do produto não encontrado. Não foi possível salvar.");
    }
  };

  if (!isOpen || !productData) return null;

  return (
    <div className="modal active" id="product-edit-modal"> {/* ID único para o modal */}
      <div className="modal-content">
        <button className="modal-close" onClick={onClose} disabled={isLoading}>×</button>
        <h3>Editar Produto: {productData.nome_base} (ID: {productData.id})</h3>
        <div>
          <label htmlFor="edit-nome_base">Nome Base*</label>
          <input id="edit-nome_base" name="nome_base" type="text" value={formData.nome_base || ''} onChange={handleChange} disabled={isLoading} />
        </div>
        <div>
          <label htmlFor="edit-marca">Marca</label>
          <input id="edit-marca" name="marca" type="text" value={formData.marca || ''} onChange={handleChange} disabled={isLoading} />
        </div>
        <div>
          <label htmlFor="edit-categoria_original">Categoria Original</label>
          <input id="edit-categoria_original" name="categoria_original" type="text" value={formData.categoria_original || ''} onChange={handleChange} disabled={isLoading} />
        </div>
        <div>
            <label htmlFor="edit-sku_original">SKU Original (em dados_brutos)</label>
            <input id="edit-sku_original" name="sku_original" type="text" value={formData.sku_original || ''} onChange={handleChange} disabled={isLoading} />
        </div>

        {/* Adicionar mais campos específicos de dados_brutos aqui se necessário */}

        <h4>Dados Brutos Completos (Visualização JSON)</h4>
        <pre style={{ background: '#f0f0f0', padding: '10px', borderRadius: '4px', maxHeight: '150px', overflowY: 'auto', fontSize: '0.8em', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
          {JSON.stringify(productData.dados_brutos, null, 2)}
        </pre>
        <button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? 'Salvando...' : 'Salvar Alterações'}
        </button>
      </div>
    </div>
  );
}

export default ProductEditModal;