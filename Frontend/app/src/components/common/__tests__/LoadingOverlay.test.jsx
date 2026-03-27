import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import LoadingOverlay from '../LoadingOverlay.jsx';

test('renders overlay when open', () => {
  render(<LoadingOverlay isOpen={true} message="Loading test" />);
  expect(screen.getByText('Loading test')).toBeInTheDocument();
  expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
  expect(screen.getByAltText(/CommerceFolio logo/i)).toBeInTheDocument();
});

test('uses the default message when open without a custom message', () => {
  render(<LoadingOverlay isOpen={true} />);

  expect(screen.getByText('Carregando...')).toBeInTheDocument();
  expect(screen.getByAltText(/CommerceFolio logo/i)).toBeInTheDocument();
});

test('renders nothing when the overlay is closed', () => {
  const { container } = render(<LoadingOverlay isOpen={false} message="Hidden" />);

  expect(container).toBeEmptyDOMElement();
});
