import React, { useState, useEffect } from 'react';
import Modal from '../common/Modal.jsx';
import fornecedorService from '../../services/fornecedorService';
import { useProductTypes } from '../../contexts/ProductTypeContext';

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
    }
  }, [isOpen]);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleGeneratePreview = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const data = await fornecedorService.previewCatalogo(file);
      setPreview({ headers: data.headers, previewImages: data.previewImages || [] });
      setFileId(data.fileId);
      setSampleRows(data.sampleRows || []);
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
    if (!fileId || !productTypeId) return;
    if (!fileId) return;
    if (!selectedType) {
      alert('Selecione um tipo de produto.');
      return;
    }
    setLoading(true);
    try {
      await fornecedorService.finalizarImportacaoCatalogo(
        fileId,
        mapping,
        sampleRows,
        selectedType.id
      );
      setMessage('Importação concluída com sucesso');
      setStep(4);
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
            {preview.previewImages.map((img, idx) => (
              <img
                key={idx}
                src={`data:image/png;base64,${img}`}
                alt={`Página ${idx + 1}`}
                style={{ maxWidth: '100%', marginBottom: '1em' }}
              />
            ))}
          </div>
        )}
        {sampleRows.length > 0 && (
          <table className="preview-table">
            <thead>
              <tr>
                {preview.headers.map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sampleRows.map((row, rowIdx) => (
                <tr key={rowIdx}>
                  {preview.headers.map((h) => (
                    <td key={h}>{row[h]}</td>
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
            {preview.headers.map((h) => (
              <tr key={h}>
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
                {preview.headers.map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sampleRows.map((row, rowIdx) => (
                <tr key={rowIdx}>
                  {preview.headers.map((h) => (
                    <td key={h}>
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
    </>
  );
}

export default ImportCatalogWizard;
