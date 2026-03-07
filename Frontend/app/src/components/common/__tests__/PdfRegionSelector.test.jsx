import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import PdfRegionSelector from '../PdfRegionSelector.jsx';
import { renderPdfPage } from '../PdfRegionSelector.helpers.js';

const mockGetDocument = jest.fn();

jest.mock('pdfjs-dist/legacy/build/pdf.worker.js?url', () => 'worker-src-stub', {
  virtual: true,
});

jest.mock(
  'pdfjs-dist/legacy/build/pdf',
  () => ({
    GlobalWorkerOptions: { workerSrc: '' },
    getDocument: (...args) => mockGetDocument(...args),
  }),
  { virtual: true }
);

function makeSuccessfulPdfTask({ width = 200, height = 100 } = {}) {
  const page = {
    getViewport: jest.fn(() => ({ width, height })),
    render: jest.fn(() => ({ promise: Promise.resolve() })),
  };
  const doc = {
    getPage: jest.fn(() => Promise.resolve(page)),
    destroy: jest.fn(() => Promise.resolve()),
  };
  return {
    doc,
    task: {
      promise: Promise.resolve(doc),
      destroy: jest.fn(),
    },
  };
}

function createDeferredPdfTask() {
  let resolve;
  const page = {
    getViewport: jest.fn(() => ({ width: 120, height: 80 })),
    render: jest.fn(() => ({ promise: Promise.resolve() })),
  };
  const doc = {
    getPage: jest.fn(() => Promise.resolve(page)),
    destroy: jest.fn(() => Promise.resolve()),
  };
  return {
    doc,
    task: {
      promise: new Promise((res) => {
        resolve = () => res(doc);
      }),
      destroy: jest.fn(),
    },
    resolve,
  };
}

beforeAll(() => {
  Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
    value: jest.fn(() => ({})),
    configurable: true,
  });
});

beforeEach(() => {
  jest.clearAllMocks();
  const pdf = makeSuccessfulPdfTask();
  mockGetDocument.mockReturnValue(pdf.task);
});

test('calls onSelect with normalized coordinates after drag', async () => {
  const onSelect = jest.fn();

  const { container } = render(
    <PdfRegionSelector
      file={new Uint8Array([1, 2, 3])}
      onSelect={onSelect}
      initialPage={3}
      initialApplyAll={false}
    />
  );

  const canvas = container.querySelector('canvas');
  Object.defineProperty(canvas, 'getBoundingClientRect', {
    value: () => ({ left: 10, top: 20, width: 200, height: 100 }),
    configurable: true,
  });

  await waitFor(() => {
    expect(canvas.width).toBe(200);
    expect(canvas.height).toBe(100);
  });

  fireEvent.mouseDown(canvas, { clientX: 20, clientY: 30 });
  fireEvent.mouseMove(canvas, { clientX: 60, clientY: 80 });
  fireEvent.mouseUp(canvas);

  expect(onSelect).toHaveBeenCalledWith({
    page: 3,
    bbox: [10, 10, 50, 60],
    bboxNorm: [0.05, 0.1, 0.25, 0.6],
    canvasWidth: 200,
    canvasHeight: 100,
    applyAllPages: false,
  });
});

test('renderPdfPage exits early when there is no document or canvas', async () => {
  await expect(renderPdfPage(null, 1, null)).resolves.toBeUndefined();
});

test('notifies apply-all checkbox changes', async () => {
  const onApplyAllChange = jest.fn();

  render(
    <PdfRegionSelector
      file={new Uint8Array([1])}
      onSelect={jest.fn()}
      initialApplyAll={true}
      onApplyAllChange={onApplyAllChange}
    />
  );

  const checkbox = await screen.findByRole('checkbox');
  expect(checkbox).toBeChecked();

  fireEvent.click(checkbox);
  expect(checkbox).not.toBeChecked();
  expect(onApplyAllChange).toHaveBeenCalledWith(false);
});

test('shows error and calls onLoadError when pdf load fails', async () => {
  const error = new Error('pdf load failed');
  const onLoadError = jest.fn();

  mockGetDocument.mockReturnValue({
    promise: Promise.reject(error),
    destroy: jest.fn(),
  });

  render(
    <PdfRegionSelector
      file={new Uint8Array([9])}
      onSelect={jest.fn()}
      onLoadError={onLoadError}
    />
  );

  expect(await screen.findByText(/falha ao carregar pdf/i)).toBeInTheDocument();
  expect(onLoadError).toHaveBeenCalledWith(error);
});

test('resets page and apply-all state when a new file is loaded', async () => {
  const firstPdf = makeSuccessfulPdfTask({ width: 200, height: 100 });
  const secondPdf = makeSuccessfulPdfTask({ width: 150, height: 75 });
  mockGetDocument
    .mockReturnValueOnce(firstPdf.task)
    .mockReturnValueOnce(secondPdf.task);

  const { rerender } = render(
    <PdfRegionSelector
      file={new Uint8Array([1, 2, 3])}
      onSelect={jest.fn()}
      initialPage={3}
      initialApplyAll={false}
    />
  );

  const checkbox = await screen.findByRole('checkbox');
  expect(checkbox).not.toBeChecked();

  rerender(
    <PdfRegionSelector
      file={new Uint8Array([4, 5, 6])}
      onSelect={jest.fn()}
      initialPage={5}
      initialApplyAll={true}
    />
  );

  await waitFor(() => {
    expect(screen.getByRole('checkbox')).toBeChecked();
  });
});

test('does not call onSelect when the user releases the mouse without drawing a rectangle', async () => {
  const onSelect = jest.fn();

  const { container, unmount } = render(
    <PdfRegionSelector
      file={new Uint8Array([1, 2, 3])}
      onSelect={onSelect}
      initialPage={2}
      initialApplyAll={true}
    />
  );

  const canvas = container.querySelector('canvas');
  Object.defineProperty(canvas, 'getBoundingClientRect', {
    value: () => ({ left: 0, top: 0, width: 200, height: 100 }),
    configurable: true,
  });

  await waitFor(() => {
    expect(canvas.width).toBe(200);
  });

  fireEvent.mouseDown(canvas, { clientX: 20, clientY: 20 });
  fireEvent.mouseUp(canvas);

  expect(onSelect).not.toHaveBeenCalled();

  unmount();
});

test('ignores mouse move events before drawing starts', async () => {
  const onSelect = jest.fn();

  const { container } = render(
    <PdfRegionSelector
      file={new Uint8Array([1, 2, 3])}
      onSelect={onSelect}
      initialPage={2}
      initialApplyAll={true}
    />
  );

  const canvas = container.querySelector('canvas');
  Object.defineProperty(canvas, 'getBoundingClientRect', {
    value: () => ({ left: 0, top: 0, width: 200, height: 100 }),
    configurable: true,
  });

  await waitFor(() => {
    expect(canvas.width).toBe(200);
  });

  fireEvent.mouseMove(canvas, { clientX: 50, clientY: 60 });
  fireEvent.mouseUp(canvas);

  expect(onSelect).not.toHaveBeenCalled();
  expect(container.querySelector('.pdf-region-selector-overlay')).not.toBeInTheDocument();
});

test('handles missing files without requesting a PDF document', () => {
  render(<PdfRegionSelector file={null} onSelect={jest.fn()} />);

  expect(screen.getByRole('checkbox')).toBeChecked();
  expect(mockGetDocument).not.toHaveBeenCalled();
});

test('destroys a deferred pdf load when the selector unmounts before completion', async () => {
  const deferred = createDeferredPdfTask();
  mockGetDocument.mockReturnValueOnce(deferred.task);

  const { unmount } = render(
    <PdfRegionSelector file={new Uint8Array([7, 8, 9])} onSelect={jest.fn()} />
  );

  unmount();
  deferred.resolve();

  await waitFor(() => {
    expect(deferred.doc.destroy).toHaveBeenCalled();
  });
});

test('destroys the previous pdf document and rerenders when the page changes', async () => {
  const firstPdf = makeSuccessfulPdfTask({ width: 200, height: 100 });
  const secondPdf = makeSuccessfulPdfTask({ width: 160, height: 90 });
  mockGetDocument
    .mockReturnValueOnce(firstPdf.task)
    .mockReturnValueOnce(secondPdf.task);

  const firstFile = new Uint8Array([1, 2, 3]);
  const secondFile = new Uint8Array([4, 5, 6]);
  const { rerender, container } = render(
    <PdfRegionSelector
      file={firstFile}
      onSelect={jest.fn()}
      initialPage={1}
      initialApplyAll={true}
    />
  );

  const canvas = container.querySelector('canvas');
  await waitFor(() => {
    expect(canvas.width).toBe(200);
  });

  rerender(
    <PdfRegionSelector
      file={secondFile}
      onSelect={jest.fn()}
      initialPage={1}
      initialApplyAll={true}
    />
  );

  await waitFor(() => {
    expect(firstPdf.doc.destroy).toHaveBeenCalled();
  });

  rerender(
    <PdfRegionSelector
      file={secondFile}
      onSelect={jest.fn()}
      initialPage={4}
      initialApplyAll={true}
    />
  );

  await waitFor(() => {
    expect(secondPdf.doc.getPage).toHaveBeenCalledWith(4);
  });
});
