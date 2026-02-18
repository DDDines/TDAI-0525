import React, { useRef, useEffect, useState } from 'react';
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf';
import pdfWorkerSrc from 'pdfjs-dist/legacy/build/pdf.worker.js?url';

// Configura o worker do pdf.js para ambiente Vite
pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerSrc;

function PdfRegionSelector({
  file,
  onSelect,
  initialPage = 1,
  onLoadError,
  onApplyAllChange,
}) {
  const canvasRef = useRef(null);
  const pdfDocumentRef = useRef(null);
  const [pageNum, setPageNum] = useState(initialPage);
  const startPos = useRef(null);
  const [rect, setRect] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [applyAll, setApplyAll] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setPageNum(initialPage);
  }, [initialPage, file]);

  useEffect(() => {
    let task;
    let doc;
    let cancelled = false;

    const load = async () => {
      if (!file) return;
      setLoading(true);
      setError(null);
      try {
        task = pdfjs.getDocument({ data: file });
        doc = await task.promise;
      } catch (err) {
        if (!cancelled && onLoadError) onLoadError(err);
        if (!cancelled) setError('Falha ao carregar PDF');
        return;
      }
      if (cancelled) {
        doc.destroy();
        return;
      }
      if (pdfDocumentRef.current) {
        await pdfDocumentRef.current.destroy();
      }
      pdfDocumentRef.current = doc;
      const page = await doc.getPage(pageNum);
      const viewport = page.getViewport({ scale: 1.5 });
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      await page.render({ canvasContext: ctx, viewport }).promise;
      setLoading(false);
    };

    load();

    return () => {
      cancelled = true;
      if (task) task.destroy();
      if (doc) doc.destroy();
      pdfDocumentRef.current = null;
    };
  }, [file, onLoadError]);

  useEffect(() => {
    const renderPage = async () => {
      const doc = pdfDocumentRef.current;
      if (!doc) return;
      const page = await doc.getPage(pageNum);
      const viewport = page.getViewport({ scale: 1.5 });
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      await page.render({ canvasContext: ctx, viewport }).promise;
    };
    renderPage();
  }, [pageNum]);

  const handleMouseDown = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    startPos.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    setIsDrawing(true);
  };

  const handleMouseMove = (e) => {
    if (!isDrawing) return;
    const rectPos = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rectPos.left;
    const y = e.clientY - rectPos.top;
    setRect({
      x0: Math.min(startPos.current.x, x),
      y0: Math.min(startPos.current.y, y),
      x1: Math.max(startPos.current.x, x),
      y1: Math.max(startPos.current.y, y),
    });
  };

  const handleMouseUp = () => {
    if (isDrawing && rect) {
      const canvas = canvasRef.current;
      const cw = canvas?.width || 1;
      const ch = canvas?.height || 1;
      onSelect({
        page: pageNum,
        bbox: [rect.x0, rect.y0, rect.x1, rect.y1],
        bboxNorm: [rect.x0 / cw, rect.y0 / ch, rect.x1 / cw, rect.y1 / ch],
        canvasWidth: cw,
        canvasHeight: ch,
        applyAllPages: applyAll,
      });
    }
    setIsDrawing(false);
    startPos.current = null;
  };

  return (
    <div style={{ position: 'relative', maxHeight: '70vh', overflow: 'auto', border: '1px solid #ddd', padding: '8px', background: '#f8f8f8' }}>
      {loading && <p>Carregando PDF...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <canvas
        ref={canvasRef}
        style={{ border: '1px solid #ccc', width: '100%' }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
      />
      {rect && isDrawing && (
        <div
          style={{
            position: 'absolute',
            border: '2px solid red',
            left: rect.x0,
            top: rect.y0,
            width: rect.x1 - rect.x0,
            height: rect.y1 - rect.y0,
            pointerEvents: 'none',
          }}
        />
      )}
      <label style={{ display: 'block', marginTop: '0.5em' }}>
        <input
          type="checkbox"
          checked={applyAll}
          onChange={(e) => {
            setApplyAll(e.target.checked);
            if (onApplyAllChange) onApplyAllChange(e.target.checked);
          }}
        />{' '}
        Aplicar esta seleção a todas as páginas
      </label>
    </div>
  );
}

export default PdfRegionSelector;
