import React, { useRef, useEffect, useState } from 'react';
import { pdfjs } from 'pdfjs-dist';

pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

function PdfRegionSelector({ file, onSelect }) {
  const canvasRef = useRef(null);
  const [pageNum] = useState(1);
  const startPos = useRef(null);
  const [rect, setRect] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);

  useEffect(() => {
    const load = async () => {
      if (!file) return;
    const task = pdfjs.getDocument({ data: file });
    const doc = await task.promise;
    const page = await doc.getPage(pageNum);
      const viewport = page.getViewport({ scale: 1.5 });
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      await page.render({ canvasContext: ctx, viewport }).promise;
    };
    load();
  }, [file, pageNum]);

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
import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.js`;

function PdfRegionSelector({ file, onSelect }) {
  const [numPages, setNumPages] = useState(null);
  const [page, setPage] = useState(1);
  const [rect, setRect] = useState(null);
  const [start, setStart] = useState(null);
  const [pageHeight, setPageHeight] = useState(null);
  const [pageWidth, setPageWidth] = useState(null);

  const handleMouseDown = (e) => {
    const { offsetX, offsetY } = e.nativeEvent;
    setStart({ x: offsetX, y: offsetY });
    setRect(null);
  };

  const handleMouseMove = (e) => {
    if (!start) return;
    const { offsetX, offsetY } = e.nativeEvent;
    setRect({
      x: Math.min(start.x, offsetX),
      y: Math.min(start.y, offsetY),
      w: Math.abs(offsetX - start.x),
      h: Math.abs(offsetY - start.y),
    });
  };

  const handleMouseUp = () => {
    if (isDrawing && rect) {
      onSelect({ page: pageNum, ...rect });
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
    if (!rect || !pageHeight) return;
    const { x, y, w, h } = rect;
    const bbox = [x, pageHeight - (y + h), x + w, pageHeight - y];
    onSelect({ page, bbox });
    setStart(null);
    setRect(null);
  };

  const onRenderSuccess = (info) => {
    setPageHeight(info.height);
    setPageWidth(info.width);
  };

  return (
    <div>
      <div className="pdf-nav">
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>Anterior</button>
        <span style={{ margin: '0 1em' }}>Página {page} de {numPages || '?'}</span>
        <button onClick={() => setPage((p) => Math.min(numPages || 1, p + 1))} disabled={numPages && page >= numPages}>Próxima</button>
      </div>
      <div style={{ position: 'relative', display: 'inline-block' }}>
        <Document file={file} onLoadSuccess={({ numPages }) => setNumPages(numPages)}>
          <Page pageNumber={page} onRenderSuccess={onRenderSuccess} />
        </Document>
        {pageWidth && (
          <div
            style={{ position: 'absolute', top: 0, left: 0, width: pageWidth, height: pageHeight }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
          >
            {rect && (
              <div
                style={{
                  position: 'absolute',
                  left: rect.x,
                  top: rect.y,
                  width: rect.w,
                  height: rect.h,
                  border: '2px dashed red',
                  pointerEvents: 'none',
                }}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default PdfRegionSelector;
