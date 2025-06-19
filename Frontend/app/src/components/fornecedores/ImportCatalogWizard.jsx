// Caminho: Frontend/app/src/components/fornecedores/ImportCatalogWizard.jsx

import React, { useState, useEffect, useCallback } from 'react';
import * as fornecedorService from '../../services/fornecedorService';
import LoadingPopup from '../common/LoadingPopup';
import PdfRegionSelector from '../common/PdfRegionSelector';

const ImportCatalogWizard = ({ fornecedor, onClose }) => {
    // Estados para controlar o fluxo passo a passo
    const [step, setStep] = useState(1);
    const [selectedFile, setSelectedFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [loadingMessage, setLoadingMessage] = useState('');
    const [error, setError] = useState('');
    const [pdfPreviewError, setPdfPreviewError] = useState(null);

    // Estados para a nossa lógica de pré-visualização paginada
    const [previewImages, setPreviewImages] = useState([]);
    const [totalPages, setTotalPages] = useState(0);
    const [loadedPages, setLoadedPages] = useState(0);

    // Informações retornadas após upload inicial do PDF
    const [uploadedFile, setUploadedFile] = useState(null);

    // Dados extraídos da seleção de região
    const [extractedColumns, setExtractedColumns] = useState([]);
    const [previewRows, setPreviewRows] = useState([]);

    const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file && file.type === 'application/pdf') {
            setSelectedFile(file);
            setError('');
            setPreviewImages([]);
            setTotalPages(0);
            setLoadedPages(0);
            setStep(1);
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
            const response = await fornecedorService.previewPdf(fornecedor.id, selectedFile);

            // CORREÇÃO CRÍTICA: Usa 'image_urls' e 'total_pages' como vem da API
            setPreviewImages(response.image_urls || []);
            setTotalPages(response.total_pages || 0);
            setLoadedPages((response.image_urls || []).length);
            if (response.import_file_id) {
                setUploadedFile({ id: response.import_file_id });
            }

            setStep(2); // Avança para o passo de visualização
        } catch (err) {
            console.error("Erro ao gerar pré-visualização:", err);
            const errorDetail = err.response?.data?.detail || err.message || 'Falha ao gerar pré-visualização.';
            setError(`Erro: ${errorDetail}`);
        } finally {
            setLoading(false);
        }
    };

    const handleLoadMore = async () => {
        if (!selectedFile) return;
        setLoading(true);
        setLoadingMessage('A carregar mais páginas...');
        setError('');
        try {
            const response = await fornecedorService.previewPdf(
                fornecedor.id,
                selectedFile,
                loadedPages, // Offset
                20          // Limit
            );
            setPreviewImages(prev => [...prev, ...(response.image_urls || [])]);
            setLoadedPages(prev => prev + (response.image_urls || []).length);
        } catch (err) {
            console.error("Erro ao carregar mais páginas:", err);
            const errorDetail = err.response?.data?.detail || err.message || 'Não foi possível carregar mais páginas.';
            setError(`Erro: ${errorDetail}`);
        } finally {
            setLoading(false);
        }
    };

    const handleRegionSelect = async (selection) => {
        // selection deve conter { page: number, bbox: [x0, y0, x1, y1] }
        if (!uploadedFile) return;
        setLoading(true);
        try {
            const requestBody = {
                file_id: uploadedFile.id,
                page_number: selection.page,
                region: selection.bbox,
            };
            const previewData = await fornecedorService.previewCatalogRegion(requestBody);
            setExtractedColumns(previewData.columns);
            setPreviewRows(previewData.data);
            setStep(3);
        } catch (error) {
            console.error('Erro ao pré-visualizar dados da região:', error);
            alert('Não foi possível extrair dados. Tente selecionar novamente.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="wizard-container">
            {loading && <LoadingPopup message={loadingMessage} isOpen={loading} />}
            {error && <p style={{ color: 'red', fontWeight: 'bold', border: '1px solid red', padding: '10px', marginTop: '10px' }}>{error}</p>}
            
            {step === 1 && (
                <div>
                    <h3>Passo 1: Selecione o Catálogo PDF</h3>
                    <input type="file" accept=".pdf" onChange={handleFileChange} />
                    {selectedFile && <p>Ficheiro selecionado: {selectedFile.name}</p>}
                    <button onClick={handleGeneratePreview} disabled={!selectedFile || loading}>
                        Gerar Amostra de Preview
                    </button>
                </div>
            )}

            {step === 2 && (
                <div>
                    <h3>Passo 2: Selecione a Região da Tabela</h3>
                    <PdfRegionSelector
                        imageUrls={previewImages}
                        onSelect={handleRegionSelect}
                    />
                    
                    {loadedPages > 0 && (
                        <div style={{ textAlign: 'center', marginTop: '1rem' }}>
                            <p>Mostrando {loadedPages} de {totalPages} páginas.</p>
                            {loadedPages < totalPages && (
                                <button onClick={handleLoadMore} disabled={loading}>
                                    {loading ? 'A carregar...' : 'Carregar mais páginas'}
                                </button>
                            )}
                        </div>
                    )}
                </div>
            )}
            
            <hr style={{ margin: '20px 0' }} />
            <button type="button" onClick={onClose}>Fechar</button>
        </div>
    );
};

export default ImportCatalogWizard;