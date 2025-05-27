// Frontend/app/src/components/produtos/NewProductModal.jsx
import React, { useState, useEffect } from 'react';

function NewProductModal({ isOpen, onClose, onSave, isLoading }) {
  const [nomeBase, setNomeBase] = useState('');
  const [marca, setMarca] = useState('');
  const [categoriaOriginal, setCategoriaOriginal] = useState('');
  const [skuOriginal, setSkuOriginal] = useState('');
  // Adicione aqui estados para outros campos que você queira no modal de novo produto
  // Ex: const [fornecedorId, setFornecedorId] = useState('');

  const clearForm = () => {
    setNomeBase('');
    setMarca('');
    setCategoriaOriginal('');
    setSkuOriginal('');
    // setFornecedorId('');
  };

  const handleSubmit = () => {
    if (!nomeBase.trim()) {
      alert('Nome base é obrigatório.');
      return;
    }
    const produtoData = {
      nome_base: nomeBase,
      marca: marca || null,
      categoria_original: categoriaOriginal || null,
      dados_brutos: skuOriginal ? { sku_original: skuOriginal } : null,
      // fornecedor_id: fornecedorId || null, // Exemplo
    };
    onSave(produtoData).then(() => {
        clearForm(); // Limpa o formulário no sucesso da promise retornada por onSave
    }).catch(err => {
        // O erro já é (ou deveria ser) tratado na ProdutosPage que chama onSave.
        // Não precisa de alertar novamente aqui, a menos que queira um comportamento específico do modal.
        console.error("Falha ao salvar novo produto (do modal):", err);
    });
  };

  // Efeito para limpar o formulário se o modal for fechado externamente (prop isOpen muda)
  useEffect(() => {
    if (!isOpen) {
        clearForm();
    }
  }, [isOpen]);


  if (!isOpen) return null;

  return (
    <div className="modal active" id="new-prod-modal"> {/* Mantém o ID original do protótipo */}
      <div className="modal-content">
        <button className="modal-close" onClick={onClose} disabled={isLoading}>×</button>
        <h3>Novo Produto</h3>
        <div>
            <label htmlFor="p-nome_base">Nome Base*</label>
            <input id="p-nome_base" name="nome_base" type="text" value={nomeBase} onChange={e => setNomeBase(e.target.value)} placeholder="Nome principal do produto" disabled={isLoading} />
        </div>
        <div>
            <label htmlFor="p-marca">Marca</label>
            <input id="p-marca" name="marca" type="text" value={marca} onChange={e => setMarca(e.target.value)} placeholder="Marca do produto" disabled={isLoading} />
        </div>
        <div>
            <label htmlFor="p-categoria_original">Categoria Original</label>
            <input id="p-categoria_original" name="categoria_original" type="text" value={categoriaOriginal} onChange={e => setCategoriaOriginal(e.target.value)} placeholder="Categoria original do produto" disabled={isLoading} />
        </div>
        <div>
            <label htmlFor="p-sku_original">SKU Original (em dados_brutos)</label>
            <input id="p-sku_original" name="sku_original" type="text" value={skuOriginal} onChange={e => setSkuOriginal(e.target.value)} placeholder="SKU original do produto" disabled={isLoading} />
        </div>
        {/* Futuramente, para o campo de fornecedor:
          <div>
            <label htmlFor="p-fornecedor">Fornecedor</label>
            <select id="p-fornecedor" name="fornecedor_id" value={fornecedorId} onChange={e => setFornecedorId(e.target.value)} disabled={isLoading}>
              <option value="">Selecione um fornecedor</option>
              {fornecedoresList.map(f => <option key={f.id} value={f.id}>{f.nome}</option>)}
            </select>
          </div>
        */}
        <button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? 'Salvando...' : 'Salvar Produto'}
        </button>
      </div>
    </div>
  );
}

export default NewProductModal;