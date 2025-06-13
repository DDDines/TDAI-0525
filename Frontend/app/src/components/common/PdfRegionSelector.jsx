import React, { useRef, useEffect, useState } from 'react';
import * as pdfjs from 'pdfjs-dist/build/pdf';

if (pdfjs.GlobalWorkerOptions) {
  // Use bundled worker for both browser and test environments
  // eslint-disable-next-line global-require
  pdfjs.GlobalWorkerOptions.workerSrc = require('pdfjs-dist/build/pdf.worker.js');
}

function PdfRegionSelector({ file, onSelect, initialPage = 1 }) {
  const canvasRef = useRef(null);
  const [pageNum, setPageNum] = useState(initialPage);
  const startPos = useRef(null);
  const [rect, setRect] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);

  useEffect(() => {
    setPageNum(initialPage);
  }, [initialPage, file]);

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
