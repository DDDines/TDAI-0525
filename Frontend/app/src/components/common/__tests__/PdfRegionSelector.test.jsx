import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import PdfRegionSelector from '../PdfRegionSelector.jsx';

test('calls onSelect with coords after drag', () => {
  const onSelect = jest.fn();
  const file = new Uint8Array();
  const { container } = render(<PdfRegionSelector file={file} onSelect={onSelect} />);
  const canvas = container.querySelector('canvas');
  Object.defineProperty(canvas, 'getBoundingClientRect', {
    value: () => ({ left: 0, top: 0 })
  });
  canvas.dispatchEvent(new MouseEvent('mousedown', { clientX: 5, clientY: 5, bubbles: true }));
  canvas.dispatchEvent(new MouseEvent('mousemove', { clientX: 15, clientY: 15, bubbles: true }));
  canvas.dispatchEvent(new MouseEvent('mouseup', { clientX: 15, clientY: 15, bubbles: true }));
  expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ page: 1 }));
});
