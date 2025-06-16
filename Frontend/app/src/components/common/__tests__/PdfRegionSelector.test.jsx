import { render } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import '@testing-library/jest-dom';
import PdfRegionSelector from '../PdfRegionSelector.jsx';

// Mock the legacy build used in the component
jest.mock('pdfjs-dist/legacy/build/pdf', () => ({
  GlobalWorkerOptions: { workerSrc: '' },
  getDocument: jest.fn(() => ({
    promise: Promise.resolve({
      getPage: jest.fn(() => Promise.resolve({
        getViewport: () => ({ width: 100, height: 100 }),
        render: () => ({ promise: Promise.resolve() }),
      })),
    }),
  })),
}));

test.skip('calls onSelect with coords after drag', () => {
  const onSelect = jest.fn();
  const file = new Uint8Array();
  const { container } = render(
    <PdfRegionSelector file={file} onSelect={onSelect} initialPage={3} />,
  );
  const canvas = container.querySelector('canvas');
  Object.defineProperty(canvas, 'getBoundingClientRect', {
    value: () => ({ left: 0, top: 0 })
  });
  act(() => {
    canvas.dispatchEvent(new MouseEvent('mousedown', { clientX: 5, clientY: 5, bubbles: true }));
    canvas.dispatchEvent(new MouseEvent('mousemove', { clientX: 15, clientY: 15, bubbles: true }));
    canvas.dispatchEvent(new MouseEvent('mouseup', { clientX: 15, clientY: 15, bubbles: true }));
  });
  expect(onSelect).toHaveBeenCalledWith(
    expect.objectContaining({ page: 3 }),
  );
});
