// Caminho: Frontend/app/src/components/fornecedores/ImportCatalogWizard.jsx

import React, { useEffect, useState } from 'react';
import * as fornecedorService from '../../services/fornecedorService';
import productTypeService from '../../services/productTypeService';
import LoadingPopup from '../common/LoadingPopup';
import ColumnMappingModal from '../common/ColumnMappingModal.jsx';
import PdfRegionSelector from '../common/PdfRegionSelector.jsx';
import Modal from '../common/Modal.jsx';

const BASE_FIELD_OPTIONS = [
  { value: 'nome_base', label: 'Nome Base' },
  { value: 'sku_original', label: 'SKU' },
  { value: 'auto:sku_nome', label: 'SKU + Nome (Auto)' },
  { value: 'ean_original', label: 'EAN' },
  { value: 'preco_original', label: 'Preco' },
  { value: 'descricao_original', label: 'Descricao' },
  { value: 'marca', label: 'Marca' },
  { value: 'categoria_original', label: 'Categoria' },
];

const ImportCatalogWizard = ({ fornecedor, productTypeId: initialProductTypeId, onClose, isOpen }) => {
  const [step, setStep] = useState('upload'); // upload -> preview -> processing
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileId, setFileId] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [previewError, setPreviewError] = useState('');
  const [startPage, setStartPage] = useState(1);
  const [pageCount, setPageCount] = useState(15);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [mapping, setMapping] = useState(fornecedor?.default_column_mapping || {});
  const [showMappingModal, setShowMappingModal] = useState(false);
  const [showRegionModal, setShowRegionModal] = useState(false);
  const [pdfBytes, setPdfBytes] = useState(null);
  const [selectedBbox, setSelectedBbox] = useState(null);
  const [selectedBboxNorm, setSelectedBboxNorm] = useState(null);
  const [selectedPageForRegion, setSelectedPageForRegion] = useState(null);
  const [applyAllPages, setApplyAllPages] = useState(false);
  const [regionPreview, setRegionPreview] = useState(null);
  const [manualMappingRows, setManualMappingRows] = useState([]);
  const [showPagePicker, setShowPagePicker] = useState(false);
  const [selectedPreviewIndex, setSelectedPreviewIndex] = useState(null);
  const [productTypes, setProductTypes] = useState([]);
  const [productTypeId, setProductTypeId] = useState(initialProductTypeId || '');
  const [fieldOptions, setFieldOptions] = useState(BASE_FIELD_OPTIONS);
  const [statusData, setStatusData] = useState(null);
  const [resultData, setResultData] = useState(null);
  const [error, setError] = useState('');
  const [regionError, setRegionError] = useState('');

  useEffect(() => {
    if (isOpen) {
      setStep('upload');
      setSelectedFile(null);
      setFileId(null);
      setPreviewData(null);
      setPreviewError('');
      setStartPage(1);
      setPageCount(15);
      setShowRegionModal(false);
      setPdfBytes(null);
      setSelectedBbox(null);
      setSelectedBboxNorm(null);
      setSelectedPageForRegion(null);
      setApplyAllPages(false);
      setRegionPreview(null);
      setManualMappingRows([]);
      setShowPagePicker(false);
      setSelectedPreviewIndex(null);
      setMapping(fornecedor?.default_column_mapping || {});
      setProductTypeId(initialProductTypeId || '');
      setStatusData(null);
      setResultData(null);
      setError('');
      setRegionError('');
    }
  }, [isOpen, fornecedor, initialProductTypeId]);

  useEffect(() => {
    const loadProductTypes = async () => {
      try {
        const data = await productTypeService.getProductTypes({ limit: 100 });
        const fetched = data.items || data || [];
        setProductTypes(fetched);
      } catch (err) {
        console.error('Erro ao carregar tipos de produto:', err);
        setProductTypes([]);
      }
    };
    if (isOpen) loadProductTypes();
  }, [isOpen]);

  const refreshFieldOptionsByProductType = async (ptId) => {
    const base = [...BASE_FIELD_OPTIONS];
    if (!ptId) {
        setFieldOptions(base);
        return;
    }
    try {
      const details = await productTypeService.getProductTypeDetails(ptId);
      const attrs = details?.attribute_templates || details?.attributeTemplates || [];
      const attrOptions = attrs.map((a) => ({
        value: `attr:${a.attribute_key}`,
        label: `Atributo: ${a.label || a.attribute_key}`,
      }));
      setFieldOptions([...base, ...attrOptions]);
    } catch (err) {
      console.warn('Falha ao carregar atributos do tipo de produto:', err);
      setFieldOptions(base);
    }
  };

  useEffect(() => {
    refreshFieldOptionsByProductType(productTypeId);
  }, [productTypeId]);

  const handleProductTypeChange = (nextValue) => {
    setProductTypeId(nextValue);
  };

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewData(null);
      setPreviewError('');
      setStep('upload');
    }
  };

  const handlePreview = async () => {
    if (!selectedFile) return;
    setIsLoading(true);
    setLoadingMessage('Gerando preview...');
    setPreviewError('');
    try {
      const preview = await fornecedorService.previewCatalogo(
        selectedFile,
        pageCount,
        startPage,
        fornecedor.id
      );
      if (preview.error) {
        setPreviewError(preview.error);
        setPreviewData(null);
      } else {
        setFileId(preview.fileId);
        setPreviewData(preview);
        setStep('preview');
        setSelectedPageForRegion(startPage);
        setSelectedPreviewIndex(null);
        // Se houver mÃºltiplas pÃ¡ginas no preview, jÃ¡ abre o seletor de pÃ¡gina
        if (preview.previewImages && preview.previewImages.length > 1) {
          setShowPagePicker(true);
        }
      }
    } catch (err) {
      const detail = err?.detail || err?.message || 'Falha ao gerar preview';
      setPreviewError(detail);
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  };

  const handleOpenRegionSelector = async () => {
    if (!selectedFile || !fileId) return;
    // Se houver mÃºltiplas prÃ©vias, pedir para escolher a pÃ¡gina primeiro
    if (previewData?.previewImages && previewData.previewImages.length > 1) {
      setShowPagePicker(true);
    } else {
      await launchRegionSelector(selectedPageForRegion || startPage);
    }
  };

  const launchRegionSelector = async (pageToUse) => {
    if (!selectedFile || !fileId) return;
    const buffer = await selectedFile.arrayBuffer();
    setPdfBytes(new Uint8Array(buffer));
    setSelectedPageForRegion(pageToUse);
    if (previewData?.previewImages && previewData.previewImages.length > 0) {
      const idx = Math.max(0, Math.min(previewData.previewImages.length - 1, pageToUse - startPage));
      setSelectedPreviewIndex(idx);
    }
    setSelectedBbox(null);
    setApplyAllPages(false);
    setRegionPreview(null);
    setShowRegionModal(true);
  };

  const handleRegionSelect = async ({ page, bbox, bboxNorm, canvasWidth, canvasHeight, applyAllPages: applyAll }) => {
    if (!fileId) return;
    setSelectedPageForRegion(page);
    setSelectedBbox(bbox);
    setSelectedBboxNorm(bboxNorm);
    setApplyAllPages(!!applyAll);
    setShowRegionModal(false);
    setShowPagePicker(false);
    setIsLoading(true);
    setLoadingMessage('Extraindo regiÃ£o selecionada...');
    try {
      const data = await fornecedorService.selecionarRegiaoProduto({
        fileId,
        pageNumber: page,
        bbox,
        bboxNorm,
        canvasWidth,
        canvasHeight,
      });
      const produtosArr = Array.isArray(data?.produtos) ? data.produtos : [];
      const previewHeaders = data?.preview_headers || [];
      const previewRows = data?.preview_rows || [];

      // Preferir sempre os dados crus retornados pelo backend (preview_rows),
      // pois os produtos jÃ¡ processados podem vir descartados por falta de nome/SKU.
      if (previewHeaders.length > 0 && previewRows.length > 0) {
        setRegionPreview({ headers: previewHeaders, rows: previewRows });
        setManualMappingRows(previewRows);
        console.debug('Region preview (raw rows):', previewRows.slice(0, 5));
        setShowMappingModal(true);
      } else if (produtosArr.length > 0) {
        const headers = Object.keys(produtosArr[0]);
        const rows = produtosArr.slice(0, 5);
        setRegionPreview({ headers, rows });
        setManualMappingRows(rows);
        console.debug('Region preview (produtos):', rows);
        setShowMappingModal(true);
      } else {
        // fallback: nÃ£o veio nada processado, cria headers genÃ©ricos
        const headers = ['col_0', 'col_1', 'col_2', 'col_3', 'col_4'];
        setRegionPreview({ headers, rows: [] });
        setManualMappingRows([]);
        setPreviewError('Nenhum dado extraÃ­do da regiÃ£o selecionada.');
      }
    } catch (err) {
      const detail = err?.detail || err?.message || 'Falha ao extrair regiÃ£o';
      setRegionError(detail);
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  };

  const startImport = async () => {
    if (!fileId) {
      setError('Gere o preview primeiro.');
      return;
    }
    const ptId = productTypeId ? parseInt(productTypeId, 10) : null;
    if (!ptId) {
      setError('Selecione um tipo de produto.');
      return;
    }
    setIsLoading(true);
    setLoadingMessage('Iniciando processamento...');
    setError('');
    try {
      await fornecedorService.finalizarImportacaoCatalogo({
        fileId,
        productTypeId: ptId,
        fornecedorId: fornecedor.id,
        mapping: mapping && Object.keys(mapping).length ? mapping : null,
        pages: applyAllPages ? null : (selectedPageForRegion ? [selectedPageForRegion] : null),
        region: selectedBboxNorm || selectedBbox,
      });
      setStep('processing');
      pollStatus(fileId);
    } catch (err) {
      const detail = err?.detail || err?.message || 'Falha ao iniciar processamento';
      setError(detail);
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  };

  const openManualMapping = () => {
    // Usa os headers/rows atuais ou cria placeholders
    const headers =
      regionPreview?.headers && regionPreview.headers.length > 0
        ? regionPreview.headers
        : manualMappingRows.length > 0
          ? Object.keys(manualMappingRows[0])
          : ['col_0', 'col_1', 'col_2', 'col_3', 'col_4'];
    const rows =
      manualMappingRows && manualMappingRows.length > 0
        ? manualMappingRows
        : [];
    setRegionPreview({ headers, rows });
    setShowMappingModal(true);
  };

  const handleConfirmMapping = async (map) => {
    setMapping(map);
    // Salva mapping no fornecedor para reutilizar
    try {
      if (fornecedor?.id) {
        await fornecedorService.setFornecedorMapping(fornecedor.id, map);
      }
    } catch (err) {
      console.warn('Falha ao salvar mapping no fornecedor:', err);
    }
    setShowMappingModal(false);
  };

  const pollStatus = async (id) => {
    let keepPolling = true;
    while (keepPolling) {
      try {
        const status = await fornecedorService.getImportacaoStatus(id);
        setStatusData(status);
        if (status.status && status.status !== 'PROCESSING') {
          keepPolling = false;
          if (status.status === 'IMPORTED' || status.status === 'FAILED') {
            try {
              const res = await fornecedorService.getImportacaoResult(id);
              setResultData(res);
            } catch (err) {
              console.error('Erro ao obter resultado final:', err);
              const detail = err?.detail || err?.message || 'Falha ao obter resultado final da importaÃ§Ã£o.';
              setError(detail);
            }
          }
        }
      } catch (err) {
        console.error('Erro ao consultar status:', err);
        const detail = err?.detail || err?.message || 'Falha ao consultar status da importaÃ§Ã£o.';
        setError(detail);
        keepPolling = false;
      }
      if (keepPolling) {
        // eslint-disable-next-line no-await-in-loop
        await new Promise((r) => setTimeout(r, 2500));
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="wizard-container">
      {isLoading && <LoadingPopup message={loadingMessage || 'Processando...'} isOpen={isLoading} />}
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
          <h3>Passo 1: Selecione o CatÃ¡logo (PDF, XLSX ou CSV)</h3>
          <div style={{ marginBottom: '1em' }}>
            <input
              type="file"
              accept=".pdf,.xlsx,.xls,.csv"
              onChange={handleFileChange}
              aria-label="Arquivo de catÃ¡logo"
            />
            {selectedFile && <p>Ficheiro selecionado: {selectedFile.name}</p>}
            <div style={{ display: 'flex', gap: '10px', marginTop: '10px', flexWrap: 'wrap' }}>
              <label>
                PÃ¡gina inicial:
                <input
                  type="number"
                  min="1"
                  value={startPage}
                  onChange={(e) => setStartPage(Math.max(1, parseInt(e.target.value || '1', 10)))}
                  style={{ marginLeft: '6px', width: '80px' }}
                />
              </label>
              <label>
                Quantidade de pÃ¡ginas:
                <input
                  type="number"
                  min="1"
                  value={pageCount}
                  onChange={(e) => setPageCount(Math.max(1, parseInt(e.target.value || '1', 10)))}
                  style={{ marginLeft: '6px', width: '80px' }}
                />
              </label>
            </div>
          </div>
          <button onClick={handlePreview} disabled={!selectedFile || isLoading} type="button">
            Gerar Preview
          </button>
          {previewError && <p style={{ color: 'red', marginTop: '0.5em' }}>{previewError}</p>}
        </div>
      )}

      {step === 'preview' && previewData && (
        <div>
          <h3>Passo 2: Revisar Preview</h3>
          {!previewData.headers && !previewData.previewImages && (
            <p style={{ color: '#a76b00' }}>Nenhum preview disponÃ­vel. Verifique se o arquivo Ã© suportado.</p>
          )}
          {previewData.headers && previewData.sampleRows && (
            <div>
              <p>PrÃ©via das colunas detectadas:</p>
              <table className="preview-table">
                <thead>
                  <tr>
                    {previewData.headers.map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {previewData.sampleRows.slice(0, 5).map((row, idx) => (
                    <tr key={idx}>
                      {previewData.headers.map((h) => (
                        <td key={h}>{row[h]}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {previewData.previewImages && previewData.previewImages.length > 0 && (
            <div style={{ marginTop: '1em' }}>
              <p>PrÃ©via de pÃ¡ginas (PDF): mostrando {selectedPreviewIndex != null ? 1 : previewData.previewImages.length} pÃ¡gina(s)</p>
              {(selectedPreviewIndex != null ? [previewData.previewImages[selectedPreviewIndex]] : previewData.previewImages).map((img, idx) => {
                const absoluteIdx = selectedPreviewIndex != null ? selectedPreviewIndex : idx;
                const pageNumber = startPage + absoluteIdx;
                return (
                <img
                  key={idx}
                  src={
                    typeof img === 'string'
                    ? (img.startsWith('data:image') ? img : `data:image/png;base64,${img}`)
                    : (img && img.image ? img.image : '')
                  }
                  alt={`PÃ¡gina ${pageNumber}`}
                  style={{ width: '100%', maxHeight: '320px', objectFit: 'contain', marginBottom: '10px', border: '1px solid #ddd' }}
                />
                );
              })}
            </div>
          )}

          <div style={{ marginTop: '1em', display: 'flex', gap: '1em', alignItems: 'center', flexWrap: 'wrap' }}>
            <button type="button" onClick={() => setShowMappingModal(true)}>
              Definir mapeamento
            </button>
            <button type="button" onClick={handleOpenRegionSelector} disabled={!fileId}>
              Selecionar regiÃ£o
            </button>
            <button type="button" onClick={openManualMapping}>
              Mapear manualmente
            </button>
            <label>
              PÃ¡gina para seleÃ§Ã£o:
              <input
                type="number"
                min="1"
                value={selectedPageForRegion || startPage}
                onChange={(e) => {
                  const val = Math.max(1, parseInt(e.target.value || '1', 10));
                  setSelectedPageForRegion(val);
                }}
                style={{ marginLeft: '6px', width: '80px' }}
              />
            </label>
            <label>
              Tipo de Produto:
              <select
                value={productTypeId}
                onChange={(e) => handleProductTypeChange(e.target.value)}
                style={{ marginLeft: '0.5em' }}
              >
                <option value="">Selecione...</option>
                {productTypes.map((pt) => {
                  const value = pt.id;
                  if (value === null || value === undefined) return null;
                  const label = pt.friendly_name || pt.nome || pt.name || pt.slug || pt.key_name || value;
                  return (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  );
                })}
              </select>
            </label>
            <button type="button" onClick={startImport} disabled={isLoading}>
              Iniciar Processamento
            </button>
          </div>

          {regionPreview && regionPreview.headers && (
            <div style={{ marginTop: '1em' }}>
              <p>PrÃ©via da regiÃ£o selecionada:</p>
              <table className="preview-table">
                <thead>
                  <tr>
                    {regionPreview.headers.map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {regionPreview.rows.map((row, idx) => (
                    <tr key={idx}>
                      {regionPreview.headers.map((h) => {
                        const cell = row?.[h];
                        const display =
                          cell === null || cell === undefined
                            ? ''
                            : typeof cell === 'object'
                              ? JSON.stringify(cell)
                              : cell;
                        return <td key={h}>{display}</td>;
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {regionError && <p style={{ color: 'red', marginTop: '0.5em' }}>{regionError}</p>}

          <ColumnMappingModal
            isOpen={showMappingModal}
            onClose={() => setShowMappingModal(false)}
            headers={
              (regionPreview && regionPreview.headers) ||
              (previewData && previewData.headers) ||
              ['col_0', 'col_1', 'col_2', 'col_3']
            }
            rows={
              (regionPreview && regionPreview.rows) ||
              (previewData && previewData.sampleRows) ||
              manualMappingRows ||
              []
            }
            fieldOptions={fieldOptions}
            productTypes={productTypes}
            productTypeId={productTypeId}
            onProductTypeChange={handleProductTypeChange}
            onConfirm={handleConfirmMapping}
          />
        </div>
      )}

      {step === 'processing' && (
        <div>
          <h3>Processando...</h3>
          {statusData && (
            <p>
              Status: {statusData.status} | Páginas: {statusData.pages_processed}/
              {statusData.total_pages ?? statusData.pages_total ?? 0}
            </p>
          )}
          {!statusData && <p>Aguarde, verificando status...</p>}
          {resultData && (
            <div style={{ marginTop: '1em' }}>
              <h4>Resultado</h4>
              {statusData?.status === 'FAILED' && resultData?.errors?.length > 0 && (
                <p style={{ color: '#b00020', fontWeight: 600 }}>
                  Falha: {resultData.errors[0]?.erro_processamento_pdf || resultData.errors[0]?.erro_processamento || 'Verifique os detalhes em Erros/Log.'}
                </p>
              )}
              {(resultData.stats || resultData.created || resultData.updated || resultData.errors) && (
                <ul>
                  <li>Criados: {resultData?.stats?.produtos_criados ?? (resultData?.created?.length || 0)}</li>
                  <li>Atualizados: {resultData?.stats?.produtos_atualizados ?? (resultData?.updated?.length || 0)}</li>
                  <li>Erros: {resultData?.stats?.erros ?? (resultData?.errors?.length || 0)}</li>
                  <li>
                    Páginas: {resultData?.stats?.pages_processed ?? statusData?.pages_processed ?? 0}/
                    {resultData?.stats?.pages_total ?? statusData?.total_pages ?? statusData?.pages_total ?? 0}
                  </li>
                  <li>Formato: {resultData?.stats?.ext || selectedFile?.name?.split('.').pop()?.toLowerCase() || '-'}</li>
                </ul>
              )}
              {resultData.errors && resultData.errors.length > 0 && (
                <details>
                  <summary>Erros</summary>
                  <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(resultData.errors, null, 2)}</pre>
                </details>
              )}
              {resultData.log && resultData.log.length > 0 && (
                <details>
                  <summary>Log</summary>
                  <pre style={{ whiteSpace: 'pre-wrap' }}>{resultData.log.join('\n')}</pre>
                </details>
              )}
            </div>
          )}
        </div>
      )}

      <Modal
        isOpen={showRegionModal}
        onClose={() => setShowRegionModal(false)}
        title="Selecione a regiÃ£o da tabela"
      >
        {pdfBytes && (
          <PdfRegionSelector
            key={`pdf-region-${selectedPageForRegion || startPage}`}
            file={pdfBytes}
            onSelect={handleRegionSelect}
            initialPage={selectedPageForRegion || startPage}
            onApplyAllChange={setApplyAllPages}
          />
        )}
      </Modal>

      <Modal
        isOpen={showPagePicker}
        onClose={() => setShowPagePicker(false)}
        title="Escolha a pÃ¡gina para selecionar a regiÃ£o"
      >
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: '10px' }}>
          {previewData?.previewImages?.map((img, idx) => {
            const src =
              typeof img === 'string'
                ? (img.startsWith('data:image') ? img : `data:image/png;base64,${img}`)
                : (img && img.image ? img.image : '');
            const pageNumber = startPage + idx;
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                  setShowPagePicker(false);
                  setSelectedPreviewIndex(idx);
                  // Aguarda o fechamento do modal e abre o recorte na pÃ¡gina escolhida
                  setTimeout(() => launchRegionSelector(pageNumber), 0);
                }}
                style={{
                  border: '1px solid #ccc',
                  padding: 0,
                  background: '#fff',
                  cursor: 'pointer',
                }}
              >
                <div style={{ fontSize: '0.85em', padding: '4px' }}>PÃ¡gina {pageNumber}</div>
                <img
                  src={src}
                  alt={`PÃ¡gina ${pageNumber}`}
                  style={{ width: '100%', maxHeight: '160px', objectFit: 'cover', display: 'block' }}
                />
              </button>
            );
          })}
        </div>
      </Modal>

      <hr style={{ margin: '20px 0' }} />
      <button type="button" onClick={onClose}>
        Fechar
      </button>
    </div>
  );
};

export default ImportCatalogWizard;

