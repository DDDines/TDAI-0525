// Frontend/app/src/components/ProductEditModal.jsx
import React, { useState, useEffect } from 'react';
import { showSuccessToast, showErrorToast, showInfoToast } from '../utils/notifications';
import productService from '../services/productService';

// Nomes das abas
const TAB_INFO_PRINCIPAIS = 'INFO_PRINCIPAIS';
const TAB_CONTEUDO_IA = 'CONTEUDO_IA';
const TAB_DADOS_WEB = 'DADOS_WEB';
const TAB_LOG_ENRIQUECIMENTO = 'LOG_ENRIQUECIMENTO';

// Estilos
const tabStyles = {
  tabContainer: { display: 'flex', borderBottom: '1px solid #ccc', marginBottom: '1rem' },
  tabButton: { padding: '10px 15px', cursor: 'pointer', border: 'none', backgroundColor: 'transparent', borderBottom: '3px solid transparent', marginRight: '5px', fontSize: '0.95rem' },
  activeTabButton: { borderBottom: '3px solid var(--primary)', fontWeight: 'bold', color: 'var(--primary)' },
  tabContent: { padding: '1rem 0' },
  formGroup: { marginBottom: '1rem' },
  label: { display: 'block', marginBottom: '0.3rem', fontWeight: '500', color: '#333' },
  input: { width: '100%', padding: '0.6rem 0.75rem', border: '1px solid #ccc', borderRadius: 'var(--radius)', fontSize: '1rem', boxSizing: 'border-box' },
  textarea: { width: '100%', minHeight: '150px', padding: '0.6rem 0.75rem', border: '1px solid #ccc', borderRadius: 'var(--radius)', fontSize: '1rem', boxSizing: 'border-box', resize: 'vertical' },
  button: { padding: '0.7rem 1.2rem', marginTop: '1rem', backgroundColor: 'var(--success)', color: 'white', border: 'none', borderRadius: 'var(--radius)', cursor: 'pointer', fontSize: '1rem' },
  smallButton: { padding: '0.3rem 0.6rem', fontSize: '0.8rem', marginLeft: '10px', backgroundColor: 'var(--danger)', },
  addTitleButton: { padding: '0.5rem 1rem', fontSize: '0.9rem', backgroundColor: 'var(--primary)', marginTop: '0.5rem', marginBottom: '1rem' },
  titleInputGroup: { display: 'flex', alignItems: 'center', marginBottom: '0.5rem' },
  regenerateButton: { backgroundColor: 'var(--info)', marginLeft: '10px' },
  dataViewerPre: { maxHeight: '300px', overflowY: 'auto', background: '#f4f4f4', padding: '10px', borderRadius: '4px', whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: '0.9em' },
  logList: { maxHeight: '300px', overflowY: 'auto', background: '#f4f4f4', padding: '10px', borderRadius: '4px', listStyleType: 'none', fontSize: '0.9em' },
  logListItem: { marginBottom: '5px', paddingBottom: '5px', borderBottom: '1px dashed #ddd', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }
};

// Função auxiliar para renderizar dados web de forma mais amigável
const renderWebDataItem = (key, value) => {
  let displayValue = value;
  if (Array.isArray(value)) {
    displayValue = (
      <ul style={{ margin: 0, paddingLeft: '20px' }}>
        {value.map((item, index) => <li key={index}>{String(item)}</li>)}
      </ul>
    );
  } else if (typeof value === 'object' && value !== null) {
    displayValue = <pre style={{...tabStyles.dataViewerPre, maxHeight: '150px', fontSize: '0.85em'}}>{JSON.stringify(value, null, 2)}</pre>;
  } else {
    displayValue = String(value);
  }

  return (
    <div key={key} style={{ marginBottom: '0.75rem' }}>
      <strong style={{ color: 'var(--sidebar-bg)' }}>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong>
      <div style={{ paddingLeft: '10px', marginTop: '0.25rem' }}>{displayValue}</div>
    </div>
  );
};


function ProductEditModal({ isOpen, onClose, productData, onSave, isLoading: propIsLoading }) {
  const [activeTab, setActiveTab] = useState(TAB_INFO_PRINCIPAIS);
  const [formData, setFormData] = useState({
    nome_base: '', marca: '', categoria_original: '', sku_original: '',
    titulos_sugeridos: [], 
    descricao_principal_gerada: ''
  });
  const [isSaving, setIsSaving] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false); 

  useEffect(() => {
    if (isOpen && productData) {
      setFormData({
        nome_base: productData.nome_base || '',
        marca: productData.marca || '',
        categoria_original: productData.categoria_original || '',
        sku_original: productData.dados_brutos?.sku_original || productData.dados_brutos?.codigo_original || '',
        titulos_sugeridos: Array.isArray(productData.titulos_sugeridos) ? [...productData.titulos_sugeridos] : [],
        descricao_principal_gerada: productData.descricao_principal_gerada || '',
      });
      // Não resetar a aba ativa aqui, a menos que o modal seja fechado e reaberto
    } else if (!isOpen) {
      setFormData({
        nome_base: '', marca: '', categoria_original: '', sku_original: '',
        titulos_sugeridos: [], descricao_principal_gerada: ''
      });
      setActiveTab(TAB_INFO_PRINCIPAIS); // Reseta a aba ao fechar
    }
  }, [productData, isOpen]);

  const handleTabChange = (tabName) => {
    setActiveTab(tabName);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleTituloChange = (index, value) => {
    const novosTitulos = [...formData.titulos_sugeridos];
    novosTitulos[index] = value;
    setFormData(prev => ({ ...prev, titulos_sugeridos: novosTitulos }));
  };

  const handleAddTitulo = () => {
    setFormData(prev => ({ ...prev, titulos_sugeridos: [...prev.titulos_sugeridos, ''] }));
  };

  const handleRemoveTitulo = (index) => {
    const novosTitulos = formData.titulos_sugeridos.filter((_, i) => i !== index);
    setFormData(prev => ({ ...prev, titulos_sugeridos: novosTitulos }));
  };

  const handleSaveInfoPrincipais = async () => {
    if (!productData || !productData.id) { showErrorToast("ID do produto não encontrado."); return; }
    if (!formData.nome_base.trim()) { showErrorToast("Nome base é obrigatório."); return; }
    setIsSaving(true);
    const updatePayload = {
        nome_base: formData.nome_base,
        marca: formData.marca || null,
        categoria_original: formData.categoria_original || null,
        dados_brutos: {
        ...(productData.dados_brutos || {}),
        sku_original: formData.sku_original.trim() ? formData.sku_original.trim() : undefined,
        },
    };
    if (updatePayload.dados_brutos.sku_original === undefined) delete updatePayload.dados_brutos.sku_original;
    try { await onSave(productData.id, updatePayload); } 
    catch (error) { console.error("Falha ao salvar informações principais (do modal):", error); } 
    finally { setIsSaving(false); }
  };

  const handleSaveConteudoIA = async () => {
    if (!productData || !productData.id) { showErrorToast("ID do produto não encontrado."); return; }
    setIsSaving(true);
    const updatePayload = {
      titulos_sugeridos: formData.titulos_sugeridos.map(t => t.trim()).filter(t => t),
      descricao_principal_gerada: formData.descricao_principal_gerada.trim() ? formData.descricao_principal_gerada.trim() : null,
    };
    try { await onSave(productData.id, updatePayload); } 
    catch (error) { console.error("Falha ao salvar conteúdo IA (do modal):", error); } 
    finally { setIsSaving(false); }
  };
  
  const handleRegenerateContent = async (type) => {
    if (!productData || !productData.id) {
      showErrorToast(`ID do produto não disponível para regenerar ${type}.`);
      return;
    }
    setIsGenerating(true);
    showInfoToast(`Solicitando nova geração de ${type} para "${productData.nome_base}"...`);
    try {
      if (type === 'títulos') {
        await productService.gerarTitulosProduto(productData.id);
      } else if (type === 'descrição') {
        await productService.gerarDescricaoProduto(productData.id);
      }
      showSuccessToast(`Solicitação de regeneração de ${type} enviada! Os novos dados e o status serão atualizados em breve.`);
      // Opcional: Fechar o modal ou desabilitar mais ações até que productData seja atualizado pela ProdutosPage
      // onClose(); // Poderia fechar para forçar o usuário a ver a tabela atualizada
    } catch (error) {
        const errorMsg = error?.detail || error?.message || `Falha ao solicitar regeneração de ${type}.`;
        showErrorToast(errorMsg);
    } finally {
      setIsGenerating(false);
    }
  };

  const renderTabContent = () => {
    if (!productData) return <p>Nenhum produto carregado.</p>;

    // Chaves que esperamos do enriquecimento web e que queremos destacar
    const chavesDadosWebDestacadas = [
        'nome_sugerido_seo', 'descricao_detalhada_seo', 
        'lista_caracteristicas_beneficios_bullets', 'palavras_chave_seo_relevantes_lista',
        'especificacoes_tecnicas_dict',
        // Adicionar outras chaves que vêm de web_extractor._normalizar_dados_de_metadados
        // ou de extrair_dados_produto_com_llm que não são os campos principais do produto
        'nome', 'descricao_curta', 'imagem_url', 'sku', 'preco', 'moeda_preco', 'disponibilidade'
    ];

    switch (activeTab) {
      case TAB_INFO_PRINCIPAIS:
        return (
          <div>
            <div style={tabStyles.formGroup}>
              <label htmlFor="modal-nome_base" style={tabStyles.label}>Nome Base*</label>
              <input type="text" id="modal-nome_base" name="nome_base" value={formData.nome_base} onChange={handleChange} style={tabStyles.input} disabled={isSaving || propIsLoading || isGenerating} />
            </div>
            <div style={tabStyles.formGroup}>
              <label htmlFor="modal-sku_original" style={tabStyles.label}>SKU</label>
              <input type="text" id="modal-sku_original" name="sku_original" value={formData.sku_original} onChange={handleChange} style={tabStyles.input} disabled={isSaving || propIsLoading || isGenerating} />
            </div>
            <div style={tabStyles.formGroup}>
              <label htmlFor="modal-marca" style={tabStyles.label}>Marca</label>
              <input type="text" id="modal-marca" name="marca" value={formData.marca} onChange={handleChange} style={tabStyles.input} disabled={isSaving || propIsLoading || isGenerating} />
            </div>
            <div style={tabStyles.formGroup}>
              <label htmlFor="modal-categoria_original" style={tabStyles.label}>Categoria Original</label>
              <input type="text" id="modal-categoria_original" name="categoria_original" value={formData.categoria_original} onChange={handleChange} style={tabStyles.input} disabled={isSaving || propIsLoading || isGenerating} />
            </div>
            <button onClick={handleSaveInfoPrincipais} style={tabStyles.button} disabled={isSaving || propIsLoading || isGenerating}>
              {isSaving ? 'Salvando...' : 'Salvar Informações Principais'}
            </button>
          </div>
        );
      case TAB_CONTEUDO_IA:
        return (
          <div>
            <div style={tabStyles.formGroup}>
              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem'}}>
                <label htmlFor="modal-descricao_principal" style={{...tabStyles.label, marginBottom: 0}}>Descrição Principal Gerada/Editada</label>
                <button onClick={() => handleRegenerateContent('descrição')} style={{...tabStyles.smallButton, ...tabStyles.regenerateButton}} disabled={isGenerating || isSaving || propIsLoading}>
                  {isGenerating ? 'Gerando...' : '🔄 Regenerar Descrição'}
                </button>
              </div>
              <textarea id="modal-descricao_principal" name="descricao_principal_gerada" value={formData.descricao_principal_gerada} onChange={handleChange} style={tabStyles.textarea} rows={8} disabled={isSaving || propIsLoading || isGenerating}/>
            </div>
            <div style={tabStyles.formGroup}>
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem'}}>
                    <label style={{...tabStyles.label, marginBottom: 0}}>Títulos Sugeridos Editáveis</label>
                    <button onClick={() => handleRegenerateContent('títulos')} style={{...tabStyles.smallButton, ...tabStyles.regenerateButton}} disabled={isGenerating || isSaving || propIsLoading}>
                        {isGenerating ? 'Gerando...' : '🔄 Regenerar Títulos'}
                    </button>
                </div>
              {formData.titulos_sugeridos && formData.titulos_sugeridos.map((titulo, index) => (
                <div key={index} style={tabStyles.titleInputGroup}>
                  <input type="text" value={titulo} onChange={(e) => handleTituloChange(index, e.target.value)} style={{ ...tabStyles.input, flexGrow: 1 }} placeholder={`Título ${index + 1}`} disabled={isSaving || propIsLoading || isGenerating} />
                  <button onClick={() => handleRemoveTitulo(index)} style={tabStyles.smallButton} disabled={isSaving || propIsLoading || isGenerating}>Remover</button>
                </div>
              ))}
              <button onClick={handleAddTitulo} style={tabStyles.addTitleButton} disabled={isSaving || propIsLoading || isGenerating}>Adicionar Novo Título</button>
            </div>
            <button onClick={handleSaveConteudoIA} style={tabStyles.button} disabled={isSaving || propIsLoading || isGenerating}>
              {isSaving ? 'Salvando...' : 'Salvar Conteúdo IA'}
            </button>
          </div>
        );
      case TAB_DADOS_WEB:
        const dadosBrutos = productData.dados_brutos || {};
        const dadosWebVisiveis = Object.entries(dadosBrutos)
            .filter(([key]) => chavesDadosWebDestacadas.includes(key) && dadosBrutos[key] !== null && dadosBrutos[key] !== undefined && String(dadosBrutos[key]).trim() !== "")
            .sort(([keyA], [keyB]) => chavesDadosWebDestacadas.indexOf(keyA) - chavesDadosWebDestacadas.indexOf(keyB)); // Ordena pelas chaves destacadas
        
        const outrosDadosBrutos = Object.entries(dadosBrutos)
            .filter(([key]) => !chavesDadosWebDestacadas.includes(key));

        return (
            <div>
              <h4>Dados Coletados do Enriquecimento Web</h4>
              {dadosWebVisiveis.length > 0 ? (
                dadosWebVisiveis.map(([key, value]) => renderWebDataItem(key, value))
              ) : (
                <p>Nenhum dado web destacado para exibir ou enriquecimento ainda não executado.</p>
              )}
              {outrosDadosBrutos.length > 0 && (
                <>
                  <h5 style={{marginTop: '1.5rem', marginBottom: '0.5rem', borderTop: '1px solid #eee', paddingTop: '1rem'}}>Outros Dados Brutos (JSON):</h5>
                  <pre style={tabStyles.dataViewerPre}>
                    {JSON.stringify(Object.fromEntries(outrosDadosBrutos), null, 2)}
                  </pre>
                </>
              )}
              {dadosWebVisiveis.length === 0 && outrosDadosBrutos.length === 0 && (
                <p>Nenhum dado bruto disponível.</p>
              )}
            </div>
          );
      case TAB_LOG_ENRIQUECIMENTO:
        const logMessages = productData.log_enriquecimento_web?.historico_mensagens || [];
        return (
            <div>
              <h4>Log de Enriquecimento e Geração IA</h4>
              {logMessages.length > 0 ? (
                <ul style={tabStyles.logList}>
                  {logMessages.map((msg, index) => (
                    <li key={index} style={tabStyles.logListItem}>{msg}</li>
                  ))}
                </ul>
              ) : (
                <p>Nenhum log disponível para este produto.</p>
              )}
            </div>
          );
      default:
        return null;
    }
  };
  
  if (!isOpen) return null;

  return (
    <div className="modal active" id="product-detail-modal">
      <div className="modal-content" style={{maxWidth: '700px', width: '90%'}}>
        <button className="modal-close" onClick={onClose} disabled={isSaving || propIsLoading || isGenerating}>×</button>
        <h3>
          Detalhes do Produto: {productData?.nome_base || 'Carregando...'} 
          (ID: {productData?.id || 'N/A'})
        </h3>

        <div style={tabStyles.tabContainer}>
          {/* ... (botões das abas, sem alterações) ... */}
          <button style={{...tabStyles.tabButton, ...(activeTab === TAB_INFO_PRINCIPAIS ? tabStyles.activeTabButton : {})}} onClick={() => handleTabChange(TAB_INFO_PRINCIPAIS)} disabled={isSaving || propIsLoading || isGenerating}>Informações Principais</button>
          <button style={{...tabStyles.tabButton, ...(activeTab === TAB_CONTEUDO_IA ? tabStyles.activeTabButton : {})}} onClick={() => handleTabChange(TAB_CONTEUDO_IA)} disabled={isSaving || propIsLoading || isGenerating}>Conteúdo IA</button>
          <button style={{...tabStyles.tabButton, ...(activeTab === TAB_DADOS_WEB ? tabStyles.activeTabButton : {})}} onClick={() => handleTabChange(TAB_DADOS_WEB)} disabled={isSaving || propIsLoading || isGenerating}>Dados Web</button>
          <button style={{...tabStyles.tabButton, ...(activeTab === TAB_LOG_ENRIQUECIMENTO ? tabStyles.activeTabButton : {})}} onClick={() => handleTabChange(TAB_LOG_ENRIQUECIMENTO)} disabled={isSaving || propIsLoading || isGenerating}>Log</button>
        </div>

        <div style={tabStyles.tabContent}>
          {propIsLoading && activeTab === TAB_INFO_PRINCIPAIS ? <p>Carregando dados do produto...</p> : renderTabContent()}
        </div>
      </div>
    </div>
  );
}

export default ProductEditModal;