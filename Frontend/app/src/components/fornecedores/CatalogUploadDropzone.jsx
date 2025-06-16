import React, { useState, useRef } from 'react';
import fornecedorService from '../../services/fornecedorService';
import '../common/Modal.css';

function CatalogUploadDropzone() {
  const [dragOver, setDragOver] = useState(false);
  const [fileInfo, setFileInfo] = useState(null);
  const [previewImage, setPreviewImage] = useState(null);
  const [startPage, setStartPage] = useState(1);
  const inputRef = useRef(null);

  const handleFiles = async (files) => {
    const file = files && files[0];
    if (!file) return;
    setFileInfo({ name: file.name, size: file.size });
    try {
      const data = await fornecedorService.previewCatalogo(file, 1, 1);
      if (data.previewImages && data.previewImages.length > 0) {
        setPreviewImage(data.previewImages[0]);
      }
    } catch (err) {
      console.error('Erro ao gerar preview:', err);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  const onDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const onDragLeave = () => setDragOver(false);

  const onFileChange = (e) => handleFiles(e.target.files);

  const openFileDialog = () => inputRef.current?.click();

  return (
    <div>
      <div
        className={`file-drop-area${dragOver ? ' drag-over' : ''}`}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={openFileDialog}
      >
        <p>Arraste o PDF aqui ou clique para selecionar</p>
        {fileInfo && (
          <small>
            {fileInfo.name} ({(fileInfo.size / 1024).toFixed(1)} KB)
          </small>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          style={{ display: 'none' }}
          onChange={onFileChange}
        />
      </div>
      <div className="form-group">
        <label>Iniciar processamento na página:</label>
        <input
          type="number"
          min="1"
          value={startPage}
          onChange={(e) => setStartPage(parseInt(e.target.value, 10) || 1)}
        />
      </div>
      {previewImage && (
        <img
          src={`data:image/png;base64,${previewImage}`}
          alt="Preview"
          style={{ maxWidth: '100%', marginTop: '1rem' }}
        />
      )}
    </div>
  );
}

export default CatalogUploadDropzone;
