// Caminho: Frontend/app/src/components/fornecedores/ImportCatalogWizard.jsx

import React, { useState, useEffect, useMemo } from 'react';
import * as fornecedorService from '../../services/fornecedorService';
import LoadingPopup from '../common/LoadingPopup';
import ColumnMappingModal from '../common/ColumnMappingModal.jsx';
import PdfRegionSelector from '../common/PdfRegionSelector.jsx';
import Modal from '../common/Modal.jsx';
import ImportProgress from './ImportProgress.jsx';
import PaginationControls from '../common/PaginationControls';
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
  const [jobId, setJobId] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [limit, setLimit] = useState(5);
  const [totalPdfPages, setTotalPdfPages] = useState(0);
  const [pageImages, setPageImages] = useState([]);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const totalPages = totalPdfPages;

  const [mappingHeaders, setMappingHeaders] = useState([]);
  const [mappingRows, setMappingRows] = useState([]);
  const [showMappingModal, setShowMappingModal] = useState(false);
  const [mapping, setMapping] = useState(null);

  const [showRegionModal, setShowRegionModal] = useState(false);
  const [regionPreview, setRegionPreview] = useState(null);
  const [regionError, setRegionError] = useState('');
  const [pdfBytes, setPdfBytes] = useState(null);
  const [applyAllPages, setApplyAllPages] = useState(false);
  const [selectedBbox, setSelectedBbox] = useState(null);

  const previewPages = useMemo(
    () =>
      pageImages.slice(
        (currentPage - 1) * limit,
        (currentPage - 1) * limit + limit,
      ),
    [pageImages, currentPage, limit],
  );

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
    setIsLoadingPreview(true);
    setLoading(true);
    setLoadingMessage('A gerar pré-visualização inicial...');
    setError('');
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
      setPageImages(response.image_urls || []);
      setCurrentPage(1);
      setTotalPdfPages(response.total_pages || 0);
      setStep('select_page');
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setError(`Erro: ${detail}`);
    } finally {
      setIsLoadingPreview(false);
      setLoading(false);
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

  useEffect(() => {
    const fetchPreview = async () => {
      if (!selectedFile || step !== 'select_page') return;
      setIsLoadingPreview(true);
      setLoading(true);
      setLoadingMessage('A gerar pré-visualização...');
      setError('');
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
        setPageImages(response.image_urls || []);
        setTotalPdfPages(response.total_pages || 0);
      } catch (err) {
        const detail = err.response?.data?.detail || err.message;
        setError(`Erro: ${detail}`);
      } finally {
        setIsLoadingPreview(false);
        setLoading(false);
      }
    };

    fetchPreview();
  }, [currentPage, selectedFile]);



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
          {isLoadingPreview && <p>A carregar pré-visualização...</p>}
          <div style={{ display: 'flex', flexWrap: 'wrap' }}>
            {previewPages.map((imgData, index) => (
              <img
                key={`${fileId}-${currentPage}-${index}`}
                src={`data:image/png;base64,${imgData}`}
                alt={`Página ${(currentPage - 1) * limit + index + 1}`}
                style={{ maxWidth: '120px', margin: '0.5em', cursor: 'pointer' }}
                onClick={() => handlePageClick((currentPage - 1) * limit + index + 1)}
              />
            ))}
          </div>
          <PaginationControls
            currentPage={currentPage}
            totalPages={Math.ceil(totalPages / limit)}
            onPageChange={(page) => setCurrentPage(page)}
          />
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
