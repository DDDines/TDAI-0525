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
