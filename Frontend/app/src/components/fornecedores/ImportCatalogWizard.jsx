import React, { useState } from 'react';
import Modal from '../common/Modal.jsx';
import fornecedorService from '../../services/fornecedorService';

const FIELD_OPTIONS = [
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
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleGeneratePreview = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const data = await fornecedorService.previewCatalogo(file);
      setPreview({ headers: data.headers });
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

  const handleConfirmImport = async () => {
    if (!fileId) return;
    setLoading(true);
    try {
      await fornecedorService.finalizarImportacaoCatalogo(fileId, mapping, sampleRows);
      setMessage('Importação concluída com sucesso');
      setStep(3);
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
        {preview.preview_images && (
          <div className="preview-images">
            {preview.preview_images.map((img, idx) => (
              <img
                key={idx}
                src={`data:image/png;base64,${img}`}
                alt={`Página ${idx + 1}`}
                style={{ maxWidth: '100px', marginRight: '4px' }}
              />
            ))}
          </div>
        )}
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
        <button onClick={handleConfirmImport} disabled={loading}>
          {loading ? 'Importando...' : 'Confirmar Importação'}
        </button>
      </div>
    );
  };

  const renderStep3 = () => (
    <div>
      <p>{message || 'Processo finalizado.'}</p>
      <button onClick={onClose}>Fechar</button>
    </div>
  );

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Importar Catálogo">
      {step === 1 && renderStep1()}
      {step === 2 && renderStep2()}
      {step === 3 && renderStep3()}
    </Modal>
  );
}

export default ImportCatalogWizard;
