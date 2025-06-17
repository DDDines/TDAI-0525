import React, { useState, useEffect, useRef, lazy, Suspense } from 'react';
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf';
import Modal from '../common/Modal.jsx';

if (pdfjs.GlobalWorkerOptions) {
  // Use bundled worker for both browser and test environments
  // eslint-disable-next-line global-require
  pdfjs.GlobalWorkerOptions.workerSrc = require('pdfjs-dist/legacy/build/pdf.worker.js');
}
import fornecedorService from '../../services/fornecedorService';
import { useProductTypes } from '../../contexts/ProductTypeContext';
import LoadingOverlay from '../common/LoadingOverlay.jsx';
const PdfRegionSelector = lazy(() => import('../common/PdfRegionSelector.jsx'));

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

const INITIAL_PREVIEW_PAGE_COUNT = 3;

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
  const [pagesTotal, setPagesTotal] = useState(0);
  const [pagesProcessed, setPagesProcessed] = useState(0);
  const [selectedType, setSelectedType] = useState(null);
  const [isNewTypeModalOpen, setIsNewTypeModalOpen] = useState(false);
  const [newTypeName, setNewTypeName] = useState('');
  const [isSubmittingType, setIsSubmittingType] = useState(false);
  const intervalRef = useRef(null);
  const [currentPreviewPage, setCurrentPreviewPage] = useState(0);
  const [regionPage, setRegionPage] = useState(1);
  const [regionProducts, setRegionProducts] = useState(null);
  const [isRegionModalOpen, setIsRegionModalOpen] = useState(false);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [firstPageThumb, setFirstPageThumb] = useState(null);
  const [selectedPages, setSelectedPages] = useState(new Set());
  const [resultSummary, setResultSummary] = useState(null);
  const previewImageRef = useRef(null);
  const [isTextModalOpen, setIsTextModalOpen] = useState(false);
  const [textPreview, setTextPreview] = useState('');
  const [startPage, setStartPage] = useState(1);
  const [dragOver, setDragOver] = useState(false);

  const { productTypes, addProductType } = useProductTypes();

  useEffect(() => {
    if (!isOpen) {
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }
      setStep(1);
      setFile(null);
      setPreview(null);
      setFileId(null);
      setSampleRows([]);
      setMapping({});
      setProductTypeId('');
      setMessage('');
      setPagesTotal(0);
      setPagesProcessed(0);
      setLoading(false);
      setSelectedType(null);
      setNewTypeName('');
      setIsNewTypeModalOpen(false);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setCurrentPreviewPage(0);
      setRegionPage(1);
      setPdfUrl(null);
      setFirstPageThumb(null);
      setSelectedPages(new Set());
      setStartPage(1);
      setResultSummary(null);
    }
  }, [isOpen]);

  useEffect(() => {
    if (preview?.numPages) {
      const value = Math.min(Math.max(startPage, 1), preview.numPages);
      setSelectedPages(
        new Set(
          Array.from({ length: preview.numPages - value + 1 }, (_, i) => value + i),
        ),
      );
    }
  }, [startPage, preview]);

  const handleFileChange = (e) => {
    const f = e.target.files[0];
    if (pdfUrl) {
      URL.revokeObjectURL(pdfUrl);
      setPdfUrl(null);
    }
    setFile(f);
    setFirstPageThumb(null);
    if (f && f.type === 'application/pdf') {
      const url = URL.createObjectURL(f);
      setPdfUrl(url);

      const reader = new FileReader();
      reader.onload = async () => {
        try {
          const data = reader.result;
          const doc = await pdfjs.getDocument({ data }).promise;
          const page = await doc.getPage(1);
          const viewport = page.getViewport({ scale: 1.5 });
          const canvas = document.createElement('canvas');
          canvas.width = viewport.width;
          canvas.height = viewport.height;
          const ctx = canvas.getContext('2d');
          await page.render({ canvasContext: ctx, viewport }).promise;
          setFirstPageThumb(canvas.toDataURL('image/png'));
        } catch (err) {
          console.error('Failed to load first page', err);
        }
      };
      reader.readAsArrayBuffer(f);
    }
  };

  const onDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  };

  const onDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  };

  const onDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileChange({ target: { files: e.dataTransfer.files } });
      e.dataTransfer.clearData();
    }
  };

  const handleGeneratePreview = async () => {
    if (!file) return;
    setLoading(true);
    try {
      let data = await fornecedorService.previewCatalogo(
        file,
        INITIAL_PREVIEW_PAGE_COUNT,
        1,
        fornecedorId,
      );
      if (data.numPages && data.numPages > INITIAL_PREVIEW_PAGE_COUNT) {
        data = await fornecedorService.previewCatalogo(
          file,
          data.numPages,
          1,
          fornecedorId,
        );
      }
      setPreview({
        headers: data.headers,
        previewImages: data.previewImages || [],
        numPages: data.numPages,
        tablePages: data.tablePages || [],
      });
      setMapping(
        data.headers.reduce((acc, h) => {
          acc[h] = '';
          return acc;
        }, {})
      );
      if (data.numPages) {
        setStartPage(1);
        setSelectedPages(new Set(Array.from({ length: data.numPages }, (_, i) => i + 1)));
      } else {
        setStartPage(1);
        setSelectedPages(new Set());
      }
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

  const handleRegionConfirm = async (selection) => {
    if (!fileId) return;
    setLoading(true);
    try {
      const data = await fornecedorService.selecionarRegiao(
        fileId,
        selection.page,
        selection.bbox,
      );
      setRegionProducts(data.produtos);
      setSampleRows(data.produtos);
      setIsRegionModalOpen(false);
    } catch (err) {
      alert(err.detail || err.message || 'Erro ao processar região');
    } finally {
      setLoading(false);
    }
  };

  const handlePreviewText = async () => {
    if (!fileId || !previewImageRef.current) return;
    const { naturalWidth, naturalHeight } = previewImageRef.current;
    setLoading(true);
    try {
      const data = await fornecedorService.selecionarRegiao(
        fileId,
        currentPreviewPage + 1,
        [0, 0, naturalWidth, naturalHeight],
      );
      const texto = data.texto || JSON.stringify(data.produtos || data, null, 2);
      setTextPreview(texto);
      setIsTextModalOpen(true);
    } catch (err) {
      alert(err.detail || err.message || 'Erro ao pré-visualizar texto');
    } finally {
      setLoading(false);
    }
  };

  const toggleSelectedPage = (page) => {
    setSelectedPages((prev) => {
      const next = new Set(prev);
      if (next.has(page)) {
        next.delete(page);
      } else {
        next.add(page);
      }
      return next;
    });
  };

  const handleStartPageChange = (e) => {
    if (!preview?.numPages) return;
    let value = parseInt(e.target.value, 10);
    if (Number.isNaN(value)) value = 1;
    value = Math.min(Math.max(value, 1), preview.numPages);
    setStartPage(value);
    setSelectedPages(
      new Set(
        Array.from({ length: preview.numPages - value + 1 }, (_, i) => value + i),
      ),
    );
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
    const mappedValues = Object.values(mapping || {});
    if (!mappedValues.includes('sku_original') && !mappedValues.includes('nome_base')) {
      alert('Mapeie pelo menos Nome ou SKU antes de continuar.');
      return;
    }
    setLoading(true);
    try {
      await fornecedorService.finalizarImportacaoCatalogo(
        fileId,
        fornecedorId,
        mapping,
        selectedType.id,
        selectedPages,
      );
      setMessage('Processando...');
      setStep(4);
      const checkStatus = async () => {
        try {
          const { status, pages_total, pages_processed } = await fornecedorService.getImportacaoStatus(fileId);
          setPagesTotal(pages_total);
          setPagesProcessed(pages_processed);
          if (status === 'DONE') {
            const result = await fornecedorService.getImportacaoResult(fileId);
            setResultSummary(result);
            setMessage('Importação concluída');
            setStep(5);
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          } else if (status === 'FAILED') {
            setMessage('Falha na importação');
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          } else if (status === 'PROCESSING' && pages_total) {
            setMessage(`Página ${pages_processed} de ${pages_total}`);
          }
          return status;
        } catch {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
          return 'FAILED';
        }
      };
      const initialStatus = await checkStatus();
      if (initialStatus === 'PROCESSING') {
        intervalRef.current = setInterval(async () => {
          const s = await checkStatus();
          if (s !== 'PROCESSING' && intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        }, 2000);
      }
    } catch (err) {
      alert(err.detail || err.message || 'Erro ao importar catálogo');
    } finally {
      setLoading(false);
    }
  };

  const renderStep1 = () => (
    <div>
      <input type="file" accept=".csv,.xls,.xlsx,.pdf" onChange={handleFileChange} />
      {firstPageThumb && (
        <div style={{ marginTop: '1em' }}>
          <img src={firstPageThumb} alt="Primeira página" style={{ maxWidth: '100%' }} />
        </div>
      )}
      <div
        className={`file-drop-area${dragOver ? ' drag-over' : ''}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
      >
        <input
          type="file"
          accept=".csv,.xls,.xlsx,.pdf"
          onChange={handleFileChange}
        />
      </div>
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
        {pdfUrl && (
          <div style={{ marginBottom: '1em' }}>
            <object
              data={pdfUrl}
              type="application/pdf"
              width="100%"
              height="500px"
            >
              <p>
                Visualização não disponível.{' '}
                <a href={pdfUrl} target="_blank" rel="noopener noreferrer">
                  Baixar PDF
                </a>
              </p>
            </object>
          </div>
        )}
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
            <div style={{ position: 'relative', display: 'inline-block' }}>
              <input
                type="checkbox"
                checked={selectedPages.has(currentPreviewPage + 1)}
                onChange={() => toggleSelectedPage(currentPreviewPage + 1)}
                style={{ position: 'absolute', top: 10, left: 10, zIndex: 1 }}
              />
              <img
                ref={previewImageRef}
                src={`data:image/png;base64,${preview.previewImages[currentPreviewPage]}`}
                alt={`Página ${currentPreviewPage + 1}`}
                style={{ maxWidth: '100%', marginBottom: '1em' }}
              />
            </div>
            <button
              type="button"
              onClick={() => {
                setRegionPage(currentPreviewPage + 1);
                setIsRegionModalOpen(true);
              }}
              className="btn-small"
            >
              Selecionar Região
            </button>
            <button
              type="button"
              onClick={handlePreviewText}
              className="btn-small"
            >
              Pré-visualizar texto
            </button>
            {preview.tablePages && preview.tablePages.length > 0 && (
              <p>Páginas com tabelas: {preview.tablePages.join(', ')}</p>
            )}
          </div>
        )}
      {preview.numPages > 1 && (
        <div className="form-group">
          <label htmlFor="start-page-input">Página inicial:</label>
          <input
            id="start-page-input"
            type="number"
            min="1"
            max={preview.numPages}
            value={startPage}
            onChange={handleStartPageChange}
          />
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
    const mappedValues = Object.values(mapping || {});
    const isMappingValid =
      mappedValues.includes('sku_original') || mappedValues.includes('nome_base');

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
          <button onClick={handleConfirmImport} disabled={loading || !isMappingValid} className="btn-primary">
            {loading ? 'Importando...' : 'Confirmar Importação'}
          </button>
        </div>
      </div>
    );
  };

const renderStep4 = () => (
  <div>
    {pagesTotal > 0 && (
      <>
        <progress
          value={pagesProcessed}
          max={pagesTotal}
          style={{ width: '100%' }}
        />
        <p>
          Página {pagesProcessed} de {pagesTotal}
        </p>
      </>
    )}
    {message && !message.startsWith('Página') && <p>{message}</p>}
    <button onClick={onClose}>Fechar</button>
  </div>
);

const renderStep5 = () => (
  <div>
    <h4>Resumo da Importação</h4>
    {resultSummary && (
      <>
        {resultSummary.created?.length > 0 && (
          <div>
            <h5>Criados</h5>
            <ul>
              {resultSummary.created.map((p) => (
                <li key={p.id}>{p.nome_base} ({p.sku || p.ean})</li>
              ))}
            </ul>
          </div>
        )}
        {resultSummary.updated?.length > 0 && (
          <div>
            <h5>Atualizados</h5>
            <ul>
              {resultSummary.updated.map((p) => (
                <li key={p.id}>{p.nome_base} ({p.sku || p.ean})</li>
              ))}
            </ul>
          </div>
        )}
        {resultSummary.errors?.length > 0 && (
          <div>
            <h5>Erros</h5>
            <ul>
              {resultSummary.errors.map((e, idx) => (
                <li key={idx}>{e.motivo_descarte || JSON.stringify(e)}</li>
              ))}
            </ul>
          </div>
        )}
      </>
    )}
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
        {step === 5 && renderStep5()}
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
      <Modal isOpen={isTextModalOpen} onClose={() => setIsTextModalOpen(false)} title="Pré-visualização do Texto">
        <pre style={{ whiteSpace: 'pre-wrap' }}>{textPreview}</pre>
      </Modal>
      <Modal isOpen={isRegionModalOpen} onClose={() => setIsRegionModalOpen(false)} title="Selecionar Região">
        {file && (
          <Suspense fallback={<div>Carregando...</div>}>
            <PdfRegionSelector
              file={file}
              onSelect={handleRegionConfirm}
              initialPage={regionPage}
            />
          </Suspense>
        )}
        {preview && (
          <div className="preview-nav" style={{ marginTop: '1em' }}>
            <button
              type="button"
              onClick={() => setRegionPage((p) => Math.max(1, p - 1))}
              disabled={regionPage <= 1}
            >
              Anterior
            </button>
            <span style={{ margin: '0 1em' }}>
              Página {regionPage} de {preview.numPages || preview.previewImages.length}
            </span>
            <button
              type="button"
              onClick={() =>
                setRegionPage((p) =>
                  Math.min(
                    preview.numPages || preview.previewImages.length,
                    p + 1,
                  )
                )
              }
              disabled={
                regionPage >= (preview.numPages || preview.previewImages.length)
              }
            >
              Próxima
            </button>
          </div>
        )}
      </Modal>
      <LoadingOverlay isOpen={loading || isSubmittingType} message="Processando..." />
    </>
  );
}

export default ImportCatalogWizard;
