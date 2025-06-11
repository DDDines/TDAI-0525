import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;
import userEvent from '@testing-library/user-event';
import Topbar from '../../Topbar.jsx';
import { ThemeProvider } from '../../../contexts/ThemeContext.jsx';

jest.mock('../../../contexts/AuthContext.jsx', () => ({
  useAuth: () => ({ logout: jest.fn() })
}));

jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn()
}));

const renderWithTheme = () =>
  render(
    <ThemeProvider>
      <Topbar toggleSidebar={() => {}} />
    </ThemeProvider>
  );

test('applies theme from localStorage on mount', () => {
  localStorage.setItem('theme', 'dark');
  renderWithTheme();
  expect(document.body).toHaveClass('dark');
});

test('toggle button toggles dark class on body', async () => {
  localStorage.setItem('theme', 'light');
  const user = userEvent.setup();
  renderWithTheme();
  const button = screen.getByRole('button', { name: /alternar tema/i });
  await user.click(button);
  expect(document.body).toHaveClass('dark');
  await user.click(button);
  expect(document.body).not.toHaveClass('dark');
});
