import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import ThemeToggle from '../../ThemeToggle.jsx';
import { useTheme } from '../../../contexts/ThemeContext.jsx';

jest.mock('../../../contexts/ThemeContext.jsx', () => ({
  useTheme: jest.fn(),
}));

describe('ThemeToggle', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders the dark-mode transition affordance and toggles the theme', async () => {
    const toggleTheme = jest.fn();
    useTheme.mockReturnValue({ mode: 'dark', toggleTheme });

    render(<ThemeToggle className="theme-button" />);

    const button = screen.getByRole('button', { name: /ir para claro/i });
    expect(button).toHaveClass('theme-button');
    expect(screen.getByText(/Tema atual: escuro/i)).toBeInTheDocument();
    expect(screen.getByRole('img', { hidden: true })).toBeInTheDocument();

    await userEvent.click(button);
    expect(toggleTheme).toHaveBeenCalled();
  });

  test('renders the light-mode transition affordance', () => {
    useTheme.mockReturnValue({ mode: 'light', toggleTheme: jest.fn() });

    render(<ThemeToggle />);

    expect(screen.getByRole('button', { name: /ir para escuro/i })).toBeInTheDocument();
    expect(screen.getByText(/Tema atual: claro/i)).toBeInTheDocument();
  });
});
