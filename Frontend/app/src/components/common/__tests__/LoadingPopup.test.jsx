import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import LoadingPopup from '../LoadingPopup.jsx';

test('renders popup when open', () => {
  render(<LoadingPopup isOpen={true} message="Loading test" />);
  expect(screen.getByText('Loading test')).toBeInTheDocument();
});
