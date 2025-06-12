import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import CatalogFileList from '../CatalogFileList.jsx';

jest.mock('../../../utils/backend.js', () => ({
  __esModule: true,
  default: () => 'http://backend',
  getBackendBaseUrl: () => 'http://backend'
}));

const files = [
  {
    id: 1,
    original_filename: 'file1.csv',
    stored_filename: 'stored1.csv',
    status: 'IMPORTED',
    created_at: '2024-01-01T00:00:00Z'
  },
  {
    id: 2,
    original_filename: 'file2.csv',
    stored_filename: 'stored2.csv',
    status: 'IMPORTED',
    created_at: '2024-01-02T00:00:00Z'
  }
];

test('renders link to stored file for each entry', () => {
  render(<CatalogFileList files={files} />);
  const links = screen.getAllByRole('link');
  expect(links).toHaveLength(files.length);
  expect(links[0]).toHaveAttribute(
    'href',
    'http://backend/static/uploads/catalogs/stored1.csv'
  );
});
