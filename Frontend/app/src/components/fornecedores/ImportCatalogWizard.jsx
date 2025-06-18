import React, { useState } from 'react';
import fornecedorService from '../../services/fornecedorService';
import LoadingPopup from '../common/LoadingPopup';
import PdfRegionSelector from '../common/PdfRegionSelector';

const ImportCatalogWizard = ({ fornecedor, onClose }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState({ pages: [], totalPages: 0 });
  const [loadedPages, setLoadedPages] = useState(0);
  const [loading, setLoading] = useState(false);
  const [regionFile, setRegionFile] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files && e.target.files[0];
    setSelectedFile(file || null);
  };

  const handleGeneratePreview = async () => {
    if (!selectedFile) return;
    setLoading(true);
    try {
      const data = await fornecedorService.previewPdf(
        fornecedor.id,
        selectedFile,
      );
      setPreview({
        pages: data.pages || [],
        totalPages: data.totalPages || 0,
      });
      setLoadedPages((data.pages || []).length);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadMore = async () => {
    setLoading(true);
    try {
      const data = await fornecedorService.previewPdf(
        fornecedor.id,
        selectedFile,
        loadedPages,
        20,
      );
      setPreview((prev) => ({
        pages: [...prev.pages, ...(data.pages || [])],
        totalPages: data.totalPages || prev.totalPages,
      }));
      setLoadedPages((prev) => prev + (data.pages ? data.pages.length : 0));
    } finally {
      setLoading(false);
    }
  };

  const handleRegionSelect = ({ file }) => {
    setRegionFile(file);
  };

  return (
    <div>
      <input type="file" onChange={handleFileChange} />
      <button onClick={handleGeneratePreview}>Gerar Preview</button>
      <div>
        {preview.pages.map((img, idx) => (
          <img key={idx} src={img} alt={`Página ${idx + 1}`} />
        ))}
      </div>
      {loadedPages < preview.totalPages && (
        <button onClick={handleLoadMore}>Carregar mais</button>
      )}
      {regionFile && (
        <PdfRegionSelector file={regionFile} onSelect={() => {}} />
      )}
      <button type="button" onClick={onClose}>Fechar</button>
      <LoadingPopup isOpen={loading} />
    </div>
  );
};

export default ImportCatalogWizard;
