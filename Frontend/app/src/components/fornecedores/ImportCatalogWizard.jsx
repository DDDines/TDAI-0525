import React, { useState, useEffect } from 'react';
import fornecedorService from '../../services/fornecedorService';
import LoadingPopup from '../common/LoadingPopup';
import PdfRegionSelector from '../common/PdfRegionSelector';
import { useProductTypes } from '../../contexts/ProductTypeContext';

function ImportCatalogWizard({ isOpen, onClose, fornecedorId }) {
  const { productTypes } = useProductTypes();
  const [step, setStep] = useState(1);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewImages, setPreviewImages] = useState([]);
  const [headers, setHeaders] = useState([]);
  const [sampleRows, setSampleRows] = useState([]);
  const [totalPages, setTotalPages] = useState(0);
  const [loadedPages, setLoadedPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(0);
  const [selectedPages, setSelectedPages] = useState(new Set());
  const [productTypeId, setProductTypeId] = useState('');
  const [mapping] = useState({});
  const [importFileId, setImportFileId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [regionOpen, setRegionOpen] = useState(false);
  const [regionPage, setRegionPage] = useState(1);
  const [importStatus, setImportStatus] = useState(null);

  useEffect(() => {
    if (!isOpen) {
      setStep(1);
      setSelectedFile(null);
      setPreviewImages([]);
      setHeaders([]);
      setSampleRows([]);
      setTotalPages(0);
      setLoadedPages(0);
      setCurrentPage(0);
      setSelectedPages(new Set());
      setProductTypeId('');
      setImportFileId(null);
      setLoading(false);
      setRegionOpen(false);
      setImportStatus(null);
    }
  }, [isOpen]);

  const handleFileChange = (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleGeneratePreview = async () => {
    if (!selectedFile) return;
    setLoading(true);
    try {
      let data;
      const isPdf =
        selectedFile.type === 'application/pdf' ||
        selectedFile.name.toLowerCase().endsWith('.pdf');
      if (isPdf) {
        data = await fornecedorService.previewPdf(fornecedorId, file, 0, 20);
        setTotalPages(data.totalPages || data.total_pages || 0);
        setLoadedPages((data.pages || data.previewImages || []).length);
        data = await fornecedorService.previewPdf(selectedFile, 0, 20, fornecedorId);
      } else {
        data = await fornecedorService.previewCatalogo(selectedFile, 20, 1, fornecedorId);
      }
      setImportFileId(data.fileId || null);
      setHeaders(Array.isArray(data.headers) ? data.headers : []);
      setSampleRows(data.sampleRows || []);
      const pages = data.previewImages || data.pages || [];
      setPreviewImages(pages);
      const num = data.numPages || data.totalPages || data.total_pages || pages.length;
      setTotalPages(num);
      setLoadedPages(pages.length);
      setSelectedPages(new Set(Array.from({ length: num }, (_, i) => i + 1)));
      setStep(2);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadMore = async () => {
    if (!selectedFile) return;
    setLoading(true);
    try {
      const data = await fornecedorService.previewCatalogo(
        selectedFile,
        20,
        loadedPages + 1,
        fornecedorId,
      );
      const pages = data.previewImages || data.pages || [];
      setPreviewImages((prev) => [...prev, ...pages]);
      setLoadedPages((prev) => prev + pages.length);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleNextPage = async () => {
    const next = currentPage + 1;
    if (next >= loadedPages && loadedPages < totalPages) {
      await loadMore();
    }
    setCurrentPage((p) => Math.min(p + 1, previewImages.length - 1));
  };

  const handleLoadMore = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const data = await fornecedorService.previewPdf(
        fornecedorId,
        file,
        loadedPages,
        20,
      );
      setPreview((prev) => ({
        ...prev,
        previewImages: [
          ...(prev.previewImages || []),
          ...(data.pages || data.previewImages || []),
        ],
      }));
      setLoadedPages((prev) => prev + (data.pages ? data.pages.length : (data.previewImages || []).length));
      if (data.totalPages || data.total_pages) {
        setTotalPages(data.totalPages || data.total_pages);
      }
    } catch (err) {
      alert(err.detail || err.message || 'Erro ao carregar mais páginas');
    } finally {
      setLoading(false);
    }
  const handlePrevPage = () => {
    setCurrentPage((p) => Math.max(p - 1, 0));
  };

  const togglePage = (page) => {
    setSelectedPages((prev) => {
      const n = new Set(prev);
      if (n.has(page)) n.delete(page);
      else n.add(page);
      return n;
    });
  };

  const handleRegionSelect = async ({ page, bbox }) => {
    if (!importFileId) return;
    setLoading(true);
    try {
      const res = await fornecedorService.selecionarRegiao(importFileId, page, bbox);
      if (res.produtos) setSampleRows(res.produtos);
    } catch (err) {
      console.error(err);
    } finally {
      setRegionOpen(false);
      setLoading(false);
    }
  };

  const handleConfirmImport = async () => {
    setLoading(true);
    try {
      const typeId = parseInt(productTypeId, 10);
      const resp = await fornecedorService.finalizarImportacaoCatalogo(
        importFileId,
        fornecedorId,
        mapping,
        typeId,
        selectedPages,
      );
      setImportFileId(resp.file_id || importFileId);
      setStep(4);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  useEffect(() => {
    let timer;
    if (step === 4 && importFileId) {
      timer = setInterval(async () => {
        try {
          const data = await fornecedorService.getImportacaoStatus(importFileId);
          if (data.status === 'IMPORTED') {
            clearInterval(timer);
            setImportStatus('IMPORTED');
          }
        } catch (err) {
          clearInterval(timer);
        }
      }, 1000);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [step, importFileId]);

  const isConfirmDisabled = headers.length === 0;

  if (!isOpen) return null;

  const renderStep1 = () => (
    <div>
      <input type="file" onChange={handleFileChange} />
      <button onClick={handleGeneratePreview}>Gerar Preview</button>
    </div>
  );

  const renderStep2 = () => (
    <div>
      {previewImages.length > 0 && (
        <div>
          <button onClick={handlePrevPage} disabled={currentPage === 0}>
            Anterior
          </button>
          <span>
            Página {currentPage + 1} de {totalPages}
          </span>
          <button onClick={handleNextPage} disabled={currentPage + 1 >= totalPages}>
            Próxima
          </button>
          <div>
            <input
              type="checkbox"
              checked={selectedPages.has(currentPage + 1)}
              onChange={() => togglePage(currentPage + 1)}
            />
            <img
              src={`data:image/png;base64,${previewImages[currentPage]}`}
              alt="preview"
            />
          </div>
          <button onClick={() => { setRegionPage(currentPage + 1); setRegionOpen(true); }}>
            Selecionar Região
          </button>
        </div>
      )}
      <select value={productTypeId} onChange={(e) => setProductTypeId(e.target.value)}>
        <option value="">Selecione...</option>
        {productTypes.map((pt) => (
          <option key={pt.id} value={pt.id}>
            {pt.friendly_name}
          </option>
        ))}
      </select>
      <button onClick={() => setStep(3)} disabled={!productTypeId}>
        Continuar
      </button>
    </div>
  );

  const renderStep3 = () => (
    <div>
      {sampleRows.map((row, idx) => (
        <div key={idx}>
          {headers.map((h) => (
            <input key={h} value={row[h] || ''} readOnly />
          ))}
        </div>
      ))}
      <button onClick={handleConfirmImport} disabled={isConfirmDisabled}>
        Confirmar Importação
      </button>
    </div>
  );

  const renderStep4 = () => (
    <div>
      <p>{importStatus === 'IMPORTED' ? 'Importação concluída' : 'Processando...'}</p>
      {importStatus === 'IMPORTED' && <button onClick={onClose}>Fechar</button>}
    </div>
  );

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
        {step === 4 && renderStep4()}
      </div>
      <LoadingPopup isOpen={loading} />
      {regionOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <button onClick={() => setRegionPage((p) => Math.max(1, p - 1))}>Anterior</button>
            <span>Página {regionPage}</span>
            <button onClick={() => setRegionPage((p) => p + 1)}>Próxima</button>
            <PdfRegionSelector
              file={selectedFile}
              onSelect={handleRegionSelect}
              initialPage={regionPage}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default ImportCatalogWizard;
