import React, { useState, useEffect, useRef } from 'react';
import Modal from '../common/Modal.jsx';
import fornecedorService from '../../services/fornecedorService';
import { useProductTypes } from '../../contexts/ProductTypeContext';
import LoadingOverlay from '../common/LoadingOverlay.jsx';

const BASE_FIELD_OPTIONS = [
  { value: 'nome_base', label: 'Nome Base' },
  { value: 'sku_original', label: 'SKU' },
  { value: 'descricao_original', label: 'Descrição' },
  { value: 'marca', label: 'Marca' },
  { value: 'categoria_original', label: 'Categoria' },
  { value: 'ean_original', label: 'EAN' },
  { value: 'preco_original', label: 'Preço' },
  { value: 'imagem_url_original', label: 'URL Imagem' },
];

const PREVIEW_PAGE_COUNT = 3;

function ImportCatalogWizard({ isOpen, onClose, fornecedorId }) {
  const [step, setStep] = useState(1);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [fileId, setFileId] = useState(null);
  const [sampleRows, setSampleRows] = useState([]);
  const [mapping, setMapping] = useState({});
  const [productTypeId, setProductTypeId] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [selectedType, setSelectedType] = useState(null);
  const [isNewTypeModalOpen, setIsNewTypeModalOpen] = useState(false);
  const [newTypeName, setNewTypeName] = useState('');
  const [isSubmittingType, setIsSubmittingType] = useState(false);
  const intervalRef = useRef(null);
  const [currentPreviewPage, setCurrentPreviewPage] = useState(0);

  const { productTypes, addProductType } = useProductTypes();

  useEffect(() => {
    if (!isOpen) {
      setStep(1);
      setFile(null);
      setPreview(null);
      setFileId(null);
      setSampleRows([]);
      setMapping({});
      setProductTypeId('');
      setMessage('');
      setLoading(false);
      setSelectedType(null);
      setNewTypeName('');
      setIsNewTypeModalOpen(false);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setCurrentPreviewPage(0);
    }
  }, [isOpen]);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleGeneratePreview = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const data = await fornecedorService.previewCatalogo(file, 5);
      setPreview({ headers: data.headers, previewImages: data.previewImages || [] });
      const data = await fornecedorService.previewCatalogo(file, PREVIEW_PAGE_COUNT);
      setPreview({
        headers: data.headers,
        previewImages: data.previewImages || [],
        numPages: data.numPages,
        tablePages: data.tablePages || [],
      });
      setFileId(data.fileId);
      setSampleRows(data.sampleRows || []);
      setCurrentPreviewPage(0);
      setStep(2);
    } catch (err) {
      alert(err.detail || err.message || 'Erro ao gerar preview');
    } finally {
      setLoading(false);
    }
  };

  const handleMappingChange = (header, value) => {
    setMapping((prev) => ({ ...prev, [header]: value }));
  };

  const handleRowChange = (rowIndex, header, value) => {
    setSampleRows((prev) => {
      const updated = [...prev];
      const row = { ...updated[rowIndex], [header]: value };
      updated[rowIndex] = row;
      return updated;
    });
  };

  const handleContinueAfterTypeSelect = () => {
    if (productTypeId) {
      const id = parseInt(productTypeId, 10);
      const type = productTypes.find((pt) => pt.id === id);
      setSelectedType(type || null);
      setStep(3);
    }
  };

  const handleTypeChange = (e) => {
    const id = parseInt(e.target.value, 10);
    const type = productTypes.find((pt) => pt.id === id);
    setSelectedType(type || null);
    if (!Number.isNaN(id)) {
      setProductTypeId(id);
    }
  };

  const handleSaveNewType = async () => {
    if (!newTypeName.trim()) return;
    const keyName = newTypeName.trim()
      .toLowerCase()
      .replace(/\s+/g, '_')
      .replace(/[^a-z0-9_]/g, '');
    setIsSubmittingType(true);
    try {
      const newType = await addProductType({
        key_name: keyName,
        friendly_name: newTypeName.trim(),
        attribute_templates: [],
      });
      setSelectedType(newType);
      setIsNewTypeModalOpen(false);
    } catch (err) {
      // erros tratados no contexto
    } finally {
      setIsSubmittingType(false);
    }
  };

  const handleConfirmImport = async () => {
    if (!productTypeId) return;
    if (!selectedType) {
      alert('Selecione um tipo de produto.');
      return;
    }
    setLoading(true);
    try {
      await fornecedorService.finalizarImportacaoCatalogo(
        fileId,
        fornecedorId,
        mapping,
        sampleRows,
        selectedType.id
      );
      setMessage('Processando...');
      setStep(4);
      const checkStatus = async () => {
        try {
          const { status } = await fornecedorService.getImportacaoStatus(fileId);
          if (status === 'IMPORTED') {
            setMessage('Importação concluída com sucesso');
            clearInterval(intervalRef.current);
          } else if (status !== 'PROCESSING') {
            setMessage('Falha na importação');
            clearInterval(intervalRef.current);
          }
        } catch {
          clearInterval(intervalRef.current);
        }
      };
      await checkStatus();
      intervalRef.current = setInterval(checkStatus, 2000);
    } catch (err) {
      alert(err.detail || err.message || 'Erro ao importar catálogo');
    } finally {
      setLoading(false);
    }
  };

  const renderStep1 = () => (
    <div>
      <input type="file" accept=".csv,.xls,.xlsx,.pdf" onChange={handleFileChange} />
      <button onClick={handleGeneratePreview} disabled={!file || loading}>
        {loading ? 'Enviando...' : 'Gerar Preview'}
      </button>
    </div>
  );

  const renderStep2 = () => {
    if (!preview) return null;
    if (preview.message && !preview.headers?.length) {
      return <p>{preview.message}</p>;
    }
    return (
      <div>
        {preview.previewImages && preview.previewImages.length > 0 && (
          <div className="pdf-preview-images">
            <div className="preview-nav">
              <button
                type="button"
                onClick={() => setCurrentPreviewPage((p) => Math.max(p - 1, 0))}
                disabled={currentPreviewPage === 0}
              >
                Anterior
              </button>
              <span style={{ margin: '0 1em' }}>
                Página {currentPreviewPage + 1} de {preview.numPages || preview.previewImages.length}
              </span>
              <button
                type="button"
                onClick={() =>
                  setCurrentPreviewPage((p) => Math.min(p + 1, preview.previewImages.length - 1))
                }
                disabled={currentPreviewPage >= preview.previewImages.length - 1}
              >
                Próxima
              </button>
            </div>
            <img
              src={`data:image/png;base64,${preview.previewImages[currentPreviewPage]}`}
              alt={`Página ${currentPreviewPage + 1}`}
              style={{ maxWidth: '100%', marginBottom: '1em' }}
            />
            {preview.tablePages && preview.tablePages.length > 0 && (
              <p>Páginas com tabelas: {preview.tablePages.join(', ')}</p>
            )}
          </div>
        )}
        {sampleRows.length > 0 && (
          <table className="preview-table">
            <thead>
              <tr>
                {preview.headers.map((h, idx) => (
                  <th key={`${idx}-${h}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sampleRows.map((row, rowIdx) => (
                <tr key={rowIdx}>
                  {preview.headers.map((h, idx) => (
                    <td key={`${rowIdx}-${idx}`}>{row[h]}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="form-group">
          <label htmlFor="product-type-select">Tipo de Produto:</label>
          <select id="product-type-select" value={selectedType?.id || ''} onChange={handleTypeChange}>
            <option value="">Selecione...</option>
            {productTypes.map((pt) => (
              <option key={pt.id} value={pt.id}>{pt.friendly_name}</option>
            ))}
          </select>
          <button type="button" onClick={() => setIsNewTypeModalOpen(true)} className="btn-small">Criar novo tipo</button>
        </div>
        <div className="modal-actions">
          <button onClick={() => setStep(1)} className="btn-secondary">Voltar</button>
          <button onClick={() => selectedType && setStep(3)} className="btn-primary" disabled={!selectedType}>Continuar</button>
        </div>
      </div>
    );
  };

  const renderStep3 = () => {
    if (!preview) return null;
    const FIELD_OPTIONS = [
      ...BASE_FIELD_OPTIONS,
      ...(selectedType?.attribute_templates || []).map((attr) => ({
        value: attr.attribute_key,
        label: attr.label,
      })),
    ];
    return (
      <div>
        <table className="mapping-table">
          <thead>
            <tr>
              <th>Coluna Detectada</th>
              <th>Mapear para</th>
            </tr>
          </thead>
          <tbody>
            {preview.headers.map((h, idx) => (
              <tr key={`${idx}-${h}`}>
                <td>{h}</td>
                <td>
                  <select value={mapping[h] || ''} onChange={(e) => handleMappingChange(h, e.target.value)}>
                    <option value="">Ignorar</option>
                    {FIELD_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {sampleRows.length > 0 && (
          <table className="preview-table">
            <thead>
              <tr>
                {preview.headers.map((h, idx) => (
                  <th key={`${idx}-${h}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sampleRows.map((row, rowIdx) => (
                <tr key={rowIdx}>
                  {preview.headers.map((h, idx) => (
                    <td key={`${rowIdx}-${idx}`}>
                      <input
                        value={row[h] || ''}
                        onChange={(e) => handleRowChange(rowIdx, h, e.target.value)}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="modal-actions">
          <button onClick={() => setStep(2)} className="btn-secondary">Voltar</button>
          <button onClick={handleConfirmImport} disabled={loading} className="btn-primary">
            {loading ? 'Importando...' : 'Confirmar Importação'}
          </button>
        </div>
      </div>
    );
  };

  const renderStep4 = () => (
    <div>
      <p>{message || 'Processo finalizado.'}</p>
      <button onClick={onClose}>Fechar</button>
    </div>
  );

  return (
    <>
      <Modal isOpen={isOpen} onClose={onClose} title="Importar Catálogo">
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
        {step === 4 && renderStep4()}
      </Modal>

      <Modal isOpen={isNewTypeModalOpen} onClose={() => setIsNewTypeModalOpen(false)} title="Criar Novo Tipo de Produto">
        <div className="form-group">
          <label htmlFor="new-type-name">Nome do Tipo*</label>
          <input id="new-type-name" value={newTypeName} onChange={(e) => setNewTypeName(e.target.value)} disabled={isSubmittingType} />
        </div>
        <div className="modal-actions">
          <button className="btn-secondary" onClick={() => setIsNewTypeModalOpen(false)} disabled={isSubmittingType}>Cancelar</button>
          <button className="btn-success" onClick={handleSaveNewType} disabled={isSubmittingType}>{isSubmittingType ? 'Salvando...' : 'Salvar Tipo'}</button>
        </div>
      </Modal>
      <LoadingOverlay isOpen={loading || isSubmittingType} message="Processando..." />
    </>
  );
}

export default ImportCatalogWizard;
