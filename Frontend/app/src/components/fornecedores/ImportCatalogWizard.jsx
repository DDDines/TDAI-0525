// Caminho: Frontend/app/src/components/fornecedores/ImportCatalogWizard.jsx

import React, { useState } from 'react';
import * as fornecedorService from '../../services/fornecedorService';
import LoadingPopup from '../common/LoadingPopup';
import ColumnMappingModal from '../common/ColumnMappingModal.jsx';
import ImportProgress from '../common/ImportProgress.jsx';
import getBackendBaseUrl from '../../utils/backend.js';

const FIELD_OPTIONS = [
  { value: 'nome_base', label: 'Nome Base' },
  { value: 'sku', label: 'SKU' },
  { value: 'preco_venda', label: 'Preço' },
];

const ImportCatalogWizard = ({ fornecedor, onClose }) => {
  const [step, setStep] = useState('upload');
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState('');

  const [fileId, setFileId] = useState(null);
  const [pageImages, setPageImages] = useState([]);
  const [totalPages, setTotalPages] = useState(0);

  const [mappingHeaders, setMappingHeaders] = useState([]);
  const [mappingRows, setMappingRows] = useState([]);
  const [showMappingModal, setShowMappingModal] = useState(false);
  const [mapping, setMapping] = useState(null);
  const [importResult, setImportResult] = useState(null);

  const backendBaseUrl = getBackendBaseUrl();

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
      setError('');
    } else {
      setError('Por favor, selecione um ficheiro PDF válido.');
      setSelectedFile(null);
    }
  };

  const handleGeneratePreview = async () => {
    if (!selectedFile) return;
    setLoading(true);
    setLoadingMessage('A gerar pré-visualização inicial...');
    setError('');
    try {
      const response = await fornecedorService.previewPdf(
        fornecedor.id,
        selectedFile,
      );
      setFileId(response.import_file_id);
      setPageImages(response.image_urls || []);
      setTotalPages(response.total_pages || 0);
      setStep('select_page');
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setError(`Erro: ${detail}`);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadMore = async () => {
    if (!selectedFile) return;
    setLoading(true);
    setLoadingMessage('A carregar mais páginas...');
    try {
      const response = await fornecedorService.previewPdf(
        fornecedor.id,
        selectedFile,
        pageImages.length,
        20,
      );
      setPageImages((prev) => [...prev, ...(response.image_urls || [])]);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setError(`Erro: ${detail}`);
    } finally {
      setLoading(false);
    }
  };

  const handlePageClick = async (page) => {
    if (!fileId) return;
    setLoading(true);
    setLoadingMessage('Extraindo dados da página...');
    try {
      const data = await fornecedorService.fetchPageDataForMapping(fileId, page);
      if (data.table && data.table.length > 0) {
        const headers = data.table[0].map((h) => String(h));
        const rows = data.table.slice(1).map((r) => {
          const obj = {};
          headers.forEach((h, idx) => {
            obj[h] = r[idx];
          });
          return obj;
        });
        setMappingHeaders(headers);
        setMappingRows(rows.slice(0, 5));
      } else {
        setMappingHeaders([]);
        setMappingRows([]);
      }
      setShowMappingModal(true);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setError(`Erro: ${detail}`);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmMapping = async (map) => {
    setShowMappingModal(false);
    setMapping(map);
    setLoading(true);
    setLoadingMessage('Iniciando processamento...');
    try {
      await fornecedorService.finalizarImportacaoCatalogo(
        fileId,
        fornecedor.id,
        map,
      );
      setStep('processing');
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setError(`Erro: ${detail}`);
    } finally {
      setLoading(false);
    }
  };

  const handleProcessDone = (result) => {
    setImportResult(result);
    setStep('review');
  };


  return (
    <div className="wizard-container">
      {loading && <LoadingPopup message={loadingMessage} isOpen={loading} />}
      {error && (
        <p style={{ color: 'red', fontWeight: 'bold', border: '1px solid red', padding: '10px', marginTop: '10px' }}>
          {error}
        </p>
      )}

      {step === 'upload' && (
        <div>
          <h3>Passo 1: Selecione o Catálogo PDF</h3>
          <input type="file" accept=".pdf" onChange={handleFileChange} />
          {selectedFile && <p>Ficheiro selecionado: {selectedFile.name}</p>}
          <button onClick={handleGeneratePreview} disabled={!selectedFile || loading}>
            Gerar Preview
          </button>
        </div>
      )}

      {step === 'select_page' && (
        <div>
          <h3>Passo 2: Escolha a página da tabela</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap' }}>
            {pageImages.map((url, idx) => (
              <img
                key={idx}
                src={`${backendBaseUrl}${url}`}
                alt={`Página ${idx + 1}`}
                style={{ maxWidth: '120px', margin: '0.5em', cursor: 'pointer' }}
                onClick={() => handlePageClick(idx + 1)}
              />
            ))}
          </div>
          {pageImages.length < totalPages && (
            <button onClick={handleLoadMore} disabled={loading}>
              Carregar mais páginas
            </button>
          )}
        </div>
      )}

      {step === 'processing' && fileId && (
        <ImportProgress fileId={fileId} onDone={handleProcessDone} />
      )}

      {step === 'review' && importResult && (
        <div>
          <h3>Importação Concluída</h3>
          <pre>{JSON.stringify(importResult, null, 2)}</pre>
        </div>
      )}

      <ColumnMappingModal
        isOpen={showMappingModal}
        onClose={() => setShowMappingModal(false)}
        headers={mappingHeaders}
        rows={mappingRows}
        fieldOptions={FIELD_OPTIONS}
        onConfirm={handleConfirmMapping}
      />

      <hr style={{ margin: '20px 0' }} />
      <button type="button" onClick={onClose}>
        Fechar
      </button>
    </div>
  );
};

export default ImportCatalogWizard;
