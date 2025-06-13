import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import LoadingOverlay from '../LoadingOverlay.jsx';

test('renders overlay when open', () => {
  render(<LoadingOverlay isOpen={true} message="Loading test" />);
  expect(screen.getByText('Loading test')).toBeInTheDocument();
  expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
});
