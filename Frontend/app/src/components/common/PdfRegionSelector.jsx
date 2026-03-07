/**
 * Module pdf region selector.
 *
 * Defines responsibilities and integration points for components common.
 */

import React, { useEffect, useRef, useState } from 'react';
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf';
import pdfWorkerSrc from 'pdfjs-dist/legacy/build/pdf.worker.js?url';
import './PdfRegionSelector.css';

async function renderPdfPage(pdfDocument, pageNumber, canvasElement) {
  if (!pdfDocument || !canvasElement) return;

  const page = await pdfDocument.getPage(pageNumber);
  const viewport = page.getViewport({ scale: 1.5 });
  const context = canvasElement.getContext('2d');
  canvasElement.width = viewport.width;
  canvasElement.height = viewport.height;
  await page.render({ canvasContext: context, viewport }).promise;
}

function PdfRegionSelector(


  {
    file,
    onSelect,
    initialPage = 1,
    initialApplyAll = true,
    onLoadError,
    onApplyAllChange
  }) {
    const canvasRef = useRef(null);
    const pdfDocumentRef = useRef(null);
    const [pageNum, setPageNum] = useState(initialPage);
    const startPos = useRef(null);
    const [rect, setRect] = useState(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [applyAll, setApplyAll] = useState(Boolean(initialApplyAll));
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
      setPageNum(initialPage);
    }, [initialPage, file]);

    useEffect(() => {
      setApplyAll(Boolean(initialApplyAll));
    }, [initialApplyAll, file]);

    useEffect(() => {
      let task;
      let doc;
      let cancelled = false;

      const load = async () => {
        if (!file) {
          setLoading(false);
          return;
        }
        setLoading(true);
        setError(null);
        try {
          task = pdfjs.getDocument({ data: file });
          doc = await task.promise;
          if (cancelled) {
            await doc.destroy();
            return;
          }
          if (pdfDocumentRef.current) {
            await pdfDocumentRef.current.destroy();
          }
          pdfDocumentRef.current = doc;
          await renderPdfPage(doc, pageNum, canvasRef.current);
        } catch (err) {
          if (!cancelled && onLoadError) onLoadError(err);
          if (!cancelled) setError('Falha ao carregar PDF');
        } finally {
          if (!cancelled) {
            setLoading(false);
          }
        }
      };

      load();

      return () => {
        cancelled = true;
        if (task) task.destroy();
        if (doc) {
          void doc.destroy();
        }
        pdfDocumentRef.current = null;
      };
    }, [file, onLoadError]);

    useEffect(() => {
      const renderPage = async () => {
        const doc = pdfDocumentRef.current;
        if (!doc) return;
        await renderPdfPage(doc, pageNum, canvasRef.current);
      };
      void renderPage();
    }, [pageNum]);

    const handleMouseDown = (e) => {
      const bounds = canvasRef.current.getBoundingClientRect();
      startPos.current = { x: e.clientX - bounds.left, y: e.clientY - bounds.top };
      setIsDrawing(true);
    };

    const handleMouseMove = (e) => {
      if (!isDrawing) return;
      const bounds = canvasRef.current.getBoundingClientRect();
      const x = e.clientX - bounds.left;
      const y = e.clientY - bounds.top;
      setRect({
        x0: Math.min(startPos.current.x, x),
        y0: Math.min(startPos.current.y, y),
        x1: Math.max(startPos.current.x, x),
        y1: Math.max(startPos.current.y, y)
      });
    };

    const handleMouseUp = () => {
      if (isDrawing && rect) {
        const canvas = canvasRef.current;
        const canvasWidth = canvas?.width || 1;
        const canvasHeight = canvas?.height || 1;
        onSelect({
          page: pageNum,
          bbox: [rect.x0, rect.y0, rect.x1, rect.y1],
          bboxNorm: [rect.x0 / canvasWidth, rect.y0 / canvasHeight, rect.x1 / canvasWidth, rect.y1 / canvasHeight],
          canvasWidth,
          canvasHeight,
          applyAllPages: applyAll
        });
      }
      setIsDrawing(false);
      startPos.current = null;
    };

    return (
      <div className="pdf-region-selector">
      <p className="pdf-region-selector-tip">
        Clique e arraste para desenhar a área da tabela que será extraída.
      </p>

      {loading && <p className="pdf-region-selector-loading">Carregando PDF...</p>}
      {error && <p className="pdf-region-selector-error">{error}</p>}

      <canvas
          ref={canvasRef}
          className="pdf-region-selector-canvas"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          aria-label="Área para seleção da região do PDF" />


      {rect && isDrawing &&
        <div
          className="pdf-region-selector-overlay"
          style={{
            left: rect.x0,
            top: rect.y0,
            width: rect.x1 - rect.x0,
            height: rect.y1 - rect.y0
          }} />

        }

      <label className="pdf-region-selector-apply-all">
        <input
            type="checkbox"
            checked={applyAll}
            onChange={(e) => {
              setApplyAll(e.target.checked);
              if (onApplyAllChange) onApplyAllChange(e.target.checked);
            }} />

        Aplicar esta seleção a todas as páginas
      </label>
    </div>);

  }

pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerSrc;

export default PdfRegionSelector;
