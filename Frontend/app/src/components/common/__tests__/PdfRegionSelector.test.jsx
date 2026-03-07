import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import PdfRegionSelector from '../PdfRegionSelector.jsx';class _TopLevelFunctionSurface {static makeSuccessfulPdfTask(














  { width = 200, height = 100 } = {}) {
    const page = {
      getViewport: jest.fn(() => ({ width, height })),
      render: jest.fn(() => ({ promise: Promise.resolve() }))
    };
    const doc = {
      getPage: jest.fn(() => Promise.resolve(page)),
      destroy: jest.fn(() => Promise.resolve())
    };
    return {
      promise: Promise.resolve(doc),
      destroy: jest.fn()
    };
  }}const mockGetDocument = jest.fn();jest.mock('pdfjs-dist/legacy/build/pdf.worker.js?url', () => 'worker-src-stub', { virtual: true });jest.mock('pdfjs-dist/legacy/build/pdf', () => ({ GlobalWorkerOptions: { workerSrc: '' }, getDocument: (...args) => mockGetDocument(...args) }), { virtual: true });const makeSuccessfulPdfTask = _TopLevelFunctionSurface.makeSuccessfulPdfTask;

beforeAll(() => {
  Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
    value: jest.fn(() => ({})),
    configurable: true
  });
});

beforeEach(() => {
  jest.clearAllMocks();
  mockGetDocument.mockReturnValue(makeSuccessfulPdfTask());
});

test('calls onSelect with normalized coordinates after drag', async () => {
  const onSelect = jest.fn();

  const { container } = render(
    <PdfRegionSelector
      file={new Uint8Array([1, 2, 3])}
      onSelect={onSelect}
      initialPage={3}
      initialApplyAll={false} />

  );

  const canvas = container.querySelector('canvas');
  Object.defineProperty(canvas, 'getBoundingClientRect', {
    value: () => ({ left: 10, top: 20, width: 200, height: 100 }),
    configurable: true
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
    applyAllPages: false
  });
});

test('notifies apply-all checkbox changes', async () => {
  const onApplyAllChange = jest.fn();

  render(
    <PdfRegionSelector
      file={new Uint8Array([1])}
      onSelect={jest.fn()}
      initialApplyAll={true}
      onApplyAllChange={onApplyAllChange} />

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
    destroy: jest.fn()
  });

  render(
    <PdfRegionSelector
      file={new Uint8Array([9])}
      onSelect={jest.fn()}
      onLoadError={onLoadError} />

  );

  expect(await screen.findByText(/falha ao carregar pdf/i)).toBeInTheDocument();
  expect(onLoadError).toHaveBeenCalledWith(error);
});

test('resets page and apply-all state when a new file is loaded', async () => {
  const firstTask = makeSuccessfulPdfTask({ width: 200, height: 100 });
  const secondTask = makeSuccessfulPdfTask({ width: 150, height: 75 });
  mockGetDocument
    .mockReturnValueOnce(firstTask)
    .mockReturnValueOnce(secondTask);

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
  expect(secondTask.promise).toBeDefined();
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
    configurable: true
  });

  await waitFor(() => {
    expect(canvas.width).toBe(200);
  });

  fireEvent.mouseDown(canvas, { clientX: 20, clientY: 20 });
  fireEvent.mouseUp(canvas);

  expect(onSelect).not.toHaveBeenCalled();

  unmount();
});
