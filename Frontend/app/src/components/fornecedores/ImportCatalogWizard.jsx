// Caminho: Frontend/app/src/components/fornecedores/ImportCatalogWizard.jsx

import React, { useState, useEffect, useCallback } from 'react';
import * as fornecedorService from '../../services/fornecedorService';
import LoadingPopup from '../common/LoadingPopup';
import ColumnMappingModal from '../common/ColumnMappingModal.jsx';
import PdfRegionSelector from '../common/PdfRegionSelector.jsx';
import Modal from '../common/Modal.jsx';
import ImportProgress from './ImportProgress.jsx';
import PaginationControls from '../common/PaginationControls';
import getBackendBaseUrl from '../../utils/backend.js';
import { showErrorToast } from '../../utils/notifications';

const FIELD_OPTIONS = [
  { value: 'nome_base', label: 'Nome Base' },
  { value: 'sku', label: 'SKU' },
  { value: 'preco_venda', label: 'Preço' },
];

const ImportCatalogWizard = ({ fornecedor, onClose }) => {
  const [step, setStep] = useState(1);
  const [selectedFile, setSelectedFile] = useState(null);
  const [mapping, setMapping] = useState(
    fornecedor.default_column_mapping || {}
  );
  const [isLoading, setIsLoading] = useState(false);
  const [extractionResult, setExtractionResult] = useState(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [previewPages, setPreviewPages] = useState([]);
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [limit] = useState(5); // Define 5 páginas por vez
  const [fileId, setFileId] = useState(null);

  const fetchPreviewPages = useCallback(async () => {
    if (!selectedFile) return;
    setIsLoadingPreview(true);
    const offset = (currentPage - 1) * limit;
    try {
      const data = await fornecedorService.previewPdf(
        fornecedor.id,
        selectedFile,
        offset,
        limit,
      );
      if (data && data.pages) {
        setPreviewPages(data.pages);
        setTotalPages(data.total_pages);
        if (data.file_id) setFileId(data.file_id);
      } else {
        setPreviewPages([]);
        setTotalPages(0);
      }
    } catch (error) {
      console.error("Falha ao carregar o preview do PDF:", error);
      showErrorToast("Erro ao carregar o preview do PDF.");
    } finally {
      setIsLoadingPreview(false);
    }
  }, [currentPage, selectedFile, fornecedor.id, limit]);


const backendBaseUrl = getBackendBaseUrl();

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setCurrentPage(1); // Reseta para a página 1
    }
  };

  const handleGeneratePreview = () => {
    if (!selectedFile) return;
    setCurrentPage(1);
    setPageImages([]);
    setTotalPdfPages(0);
    setStep('select_page');
    setLoading(true);
    setLoadingMessage('A gerar pré-visualização inicial...');
    setError('');
    setIsLoadingPreview(true);
    try {
      const offset = (currentPage - 1) * limit;
      const response = await fornecedorService.getPdfPreview(
        selectedFile,
        fornecedor.id,
        offset,
        limit,
      );
      console.log('DADOS RECEBIDOS DA API:', response);
      setFileId(response.import_file_id);
      setPreviewPages(response.image_urls || []);
      setCurrentPage(1);
      setTotalPages(response.total_pages || 0);
      setStep('select_page');
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setError(`Erro: ${detail}`);
    } finally {
      setLoading(false);
      setIsLoadingPreview(false);
    }
  };


  const handlePageClick = async (page) => {
    if (!fileId || !selectedFile) return;
    const buffer = await selectedFile.arrayBuffer();
    setPdfBytes(new Uint8Array(buffer));
    setCurrentPage(page);
    setRegionPreview(null);
    setRegionError('');
    setShowRegionModal(true);
  };

  const handleRegionSelect = async ({ page, bbox, applyAllPages }) => {
    if (!fileId) return;
    setLoading(true);
    setLoadingMessage('Extraindo região selecionada...');
    setApplyAllPages(!!applyAllPages);
    setSelectedBbox(bbox);
    try {
      const data = await fornecedorService.selecionarRegiao({
        fileId,
        pageNumber: page,
        bbox,
      });
      const headers = data.columns.map((h) => String(h));
      setRegionPreview({
        headers,
        rows: data.data,
      });
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setRegionError(`Erro: ${detail}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUseRegion = () => {
    if (!regionPreview) return;
    setShowRegionModal(false);
    setMappingHeaders(regionPreview.headers);
    setMappingRows(regionPreview.rows.slice(0, 5));
    setShowMappingModal(true);
  };

  const handleConfirmMapping = async (map) => {
    setShowMappingModal(false);
    setMapping(map);
    setLoading(true);
    setLoadingMessage('Iniciando processamento...');
    try {
      let resp;
      if (applyAllPages) {
        resp = await fornecedorService.extractRegionBulk({
          fileId,
          bbox: selectedBbox,
          allPages: true,
        });
      } else {
        resp = await fornecedorService.startFullProcess({
          file_id: fileId,
          fornecedor_id: fornecedor.id,
          mapping: map,
        });
      }
      setJobId(resp.job_id);
      setStep('processing');
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setError(`Erro: ${detail}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchPreviewPages = useCallback(async () => {
    if (!selectedFile) return;
    const offset = (currentPage - 1) * limit;
    setIsLoadingPreview(true);
    setError('');
    try {
      const response = await fornecedorService.getPdfPreview(
        selectedFile,
        fornecedor.id,
        offset,
        limit,
      );
      setPreviewPages(response.image_urls || []);
      setTotalPages(response.total_pages || 0);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setError(`Erro: ${detail}`);
    } finally {
      setIsLoadingPreview(false);
    }
  }, [selectedFile, currentPage, fornecedor.id, limit]);

  useEffect(() => {
    fetchPreviewPages();
  }, [fetchPreviewPages]);
  useEffect(() => {
    const fetchPreview = async () => {
      if (!selectedFile || step !== 'select_page') return;
      setLoading(true);
      setLoadingMessage('A gerar pré-visualização...');
      setError('');
      setIsLoadingPreview(true);
      try {
        const offset = (currentPage - 1) * limit;
        const response = await fornecedorService.getPdfPreview(
          selectedFile,
          fornecedor.id,
          offset,
          limit,
        );
        console.log('DADOS RECEBIDOS DA API:', response);
        setFileId(response.import_file_id);
        setPreviewPages(response.image_urls || []);
        setTotalPages(response.total_pages || 0);
      } catch (err) {
        const detail = err.response?.data?.detail || err.message;
        setError(`Erro: ${detail}`);
      } finally {
        setLoading(false);
        setIsLoadingPreview(false);
      }
    };

    fetchPreview();
  }, [currentPage, selectedFile, step]);



  return (
    <div className="wizard-container">
      {loading && <LoadingPopup message={loadingMessage} isOpen={loading} />}
      {isLoadingPreview && (
        <LoadingPopup
          message="A gerar pré-visualização..."
          isOpen={isLoadingPreview}
        />
      )}
      {isLoadingPreview && (
        <LoadingPopup
          message="A gerar pré-visualização..."
          isOpen={isLoadingPreview}
        />
      )}
      {error && (
        <p
          style={{
            color: 'red',
            fontWeight: 'bold',
            border: '1px solid red',
            padding: '10px',
            marginTop: '10px',
          }}
        >
          {error}
        </p>
      )}

      {step === 'upload' && (
        <div>
          <h3>Passo 1: Selecione o Catálogo PDF</h3>
          <input type="file" accept=".pdf" onChange={handleFileChange} />
          {selectedFile && <p>Ficheiro selecionado: {selectedFile.name}</p>}
          <button
            onClick={handleGeneratePreview}
            disabled={!selectedFile || loading}
          >
            Gerar Preview
          </button>
        </div>
      )}

      {step === 'select_page' && (
        <div>
          <h3>Passo 2: Escolha a página da tabela</h3>
          <div className="pdf-preview-section">
            {isLoadingPreview && (
              <p style={{ textAlign: 'center', padding: '20px' }}>
                Carregando preview...
              </p>
            )}

            {!isLoadingPreview && previewPages.length > 0 && (
              <div className="pdf-preview-container">
                {previewPages.map((imgData, index) => (
                  <img
                    key={`${fileId}-${currentPage}-${index}`}
                    src={`data:image/png;base64,${imgData}`}
                    alt={`Página de preview ${
                      (currentPage - 1) * limit + index + 1
                    }`}
                    style={{
                      width: '100%',
                      marginBottom: '10px',
                      border: '1px solid #ddd',
                    }}
                  />
                ))}
              </div>
            )}

            {!isLoadingPreview && selectedFile && previewPages.length === 0 && (
              <p style={{ textAlign: 'center', padding: '20px' }}>
                Nenhuma página para exibir. O arquivo pode estar vazio ou ocorreu um erro.
              </p>
            )}

            {!isLoadingPreview && totalPages > 0 && (
              <PaginationControls
                currentPage={currentPage}
                totalPages={Math.ceil(totalPages / limit)}
                onPageChange={(page) => setCurrentPage(page)}
              />
            )}
          </div>
        </div>
      )}

      {step === 'processing' && jobId && (
        <ImportProgress jobId={jobId} onPendingReview={() => setStep('review')} />
      )}

      {step === 'review' && <p>Processamento concluído. Revise os dados.</p>}

      <Modal
        isOpen={showRegionModal}
        onClose={() => setShowRegionModal(false)}
        title="Selecione a região da tabela"
      >
        {pdfBytes && (
          <PdfRegionSelector
            file={pdfBytes}
            onSelect={handleRegionSelect}
            initialPage={currentPage}
            onApplyAllChange={setApplyAllPages}
          />
        )}
        {regionError && (
          <p style={{ color: 'red', marginTop: '0.5em' }}>{regionError}</p>
        )}
        {regionPreview && (
          <div style={{ marginTop: '1em' }}>
            <table className="preview-table">
              <thead>
                <tr>
                  {regionPreview.headers.map((h) => (
                    <th key={h}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {regionPreview.rows.slice(0, 5).map((row, idx) => (
                  <tr key={idx}>
                    {regionPreview.headers.map((h) => (
                      <td key={h}>{row[h]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <button type="button" onClick={handleUseRegion} style={{ marginTop: '0.5em' }}>
              Usar Esta Região
            </button>
          </div>
        )}
      </Modal>

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
