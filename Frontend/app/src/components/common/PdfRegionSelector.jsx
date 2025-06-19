import React, { useRef, useEffect, useState } from 'react';
import * as pdfjs from 'pdfjs-dist/legacy/build/pdf';
// Vite has trouble resolving the worker through the ?url syntax on some setups.
// Use the "new URL" pattern recommended by pdf.js/React-PDF so the bundler
// generates the correct worker file URL.
let workerSrc;
try {
  workerSrc = new URL('pdfjs-dist/legacy/build/pdf.worker.js', import.meta.url);
  if (pdfjs.GlobalWorkerOptions) {
    pdfjs.GlobalWorkerOptions.workerSrc = workerSrc.toString();
  }
} catch (_) {
  // Ignore errors during tests or if the worker cannot be resolved.
}

function PdfRegionSelector({ file, onSelect, initialPage = 1, onLoadError }) {
  const canvasRef = useRef(null);
  const pdfDocumentRef = useRef(null);
  const [pageNum, setPageNum] = useState(initialPage);
  const startPos = useRef(null);
  const [rect, setRect] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);

  useEffect(() => {
    setPageNum(initialPage);
  }, [initialPage, file]);

  useEffect(() => {
    let task;
    let doc;
    let cancelled = false;

    const load = async () => {
      if (!file) return;
      try {
        task = pdfjs.getDocument({ data: file });
        doc = await task.promise;
      } catch (err) {
        if (!cancelled && onLoadError) onLoadError(err);
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
      onSelect({ page: pageNum, bbox: [rect.x0, rect.y0, rect.x1, rect.y1] });
    }
    setIsDrawing(false);
    startPos.current = null;
  };

  return (
    <div style={{ position: 'relative' }}>
      <canvas
        ref={canvasRef}
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
    </div>
  );
}

export default PdfRegionSelector;
