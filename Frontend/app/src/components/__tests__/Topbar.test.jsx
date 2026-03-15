import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { fireEvent, waitFor } from '@testing-library/react';
import Topbar from '../Topbar.jsx';
import { useAuth } from '../../contexts/AuthContext';
import searchService from '../../services/searchService';

const mockNavigate = jest.fn();
const userMenuProps = [];

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

jest.mock('../../services/searchService', () => ({
  __esModule: true,
  default: {
    searchAll: jest.fn(),
  },
}));

jest.mock('../ThemeToggle.jsx', () => ({
  __esModule: true,
  default: () => <button type="button">theme-toggle</button>,
}));

jest.mock('../UserMenu.jsx', () => ({
  __esModule: true,
  default: (props) => {
    userMenuProps.push(props);
    return (
      <div>
        <button type="button" onClick={() => props.onNavigate('/configuracoes')}>
          user-menu-nav
        </button>
        <button type="button" onClick={props.onLogout}>
          user-menu-logout
        </button>
      </div>
    );
  },
}));

describe('Topbar', () => {
  const toggleSidebar = jest.fn();
  const logout = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    userMenuProps.length = 0;
    useAuth.mockReturnValue({ logout });
    searchService.searchAll.mockResolvedValue({ results: [] });
  });

  test('renders the topbar title and forwards sidebar toggle, logout and navigation handlers', async () => {
    const user = userEvent.setup();

    render(<Topbar viewTitle="Produtos" toggleSidebar={toggleSidebar} />);

    expect(screen.getByRole('heading', { name: 'Produtos' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Alternar menu/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'theme-toggle' })).toBeInTheDocument();
    expect(userMenuProps.length).toBeGreaterThan(0);

    await user.click(screen.getByRole('button', { name: /Alternar menu/i }));
    expect(toggleSidebar).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: 'user-menu-nav' }));
    expect(mockNavigate).toHaveBeenCalledWith('/configuracoes');

    await user.click(screen.getByRole('button', { name: 'user-menu-logout' }));
    expect(logout).toHaveBeenCalledTimes(1);
  });

  test('falls back to the default dashboard title when no explicit view title is provided', () => {
    render(<Topbar toggleSidebar={toggleSidebar} />);

    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
  });

  test('opens the quick search and renders matching results', async () => {
    const user = userEvent.setup();
    searchService.searchAll.mockResolvedValue({
      results: [{ type: 'produto', id: 42, name: 'Produto 42' }],
    });

    render(<Topbar viewTitle="Dashboard" toggleSidebar={toggleSidebar} />);

    fireEvent.mouseEnter(screen.getByLabelText(/Abrir busca rápida/i).closest('.topbar-quick-search'));
    const input = await screen.findByPlaceholderText(/Buscar no sistema/i);
    await user.type(input, 'produto');

    expect(await screen.findByRole('button', { name: /Produto 42/i })).toBeInTheDocument();
  });

  test('submits the first result on enter in the quick search', async () => {
    const user = userEvent.setup();
    searchService.searchAll.mockResolvedValue({
      results: [{ type: 'fornecedor', id: 8, name: 'Fornecedor XPTO' }],
    });

    render(<Topbar viewTitle="Dashboard" toggleSidebar={toggleSidebar} />);

    fireEvent.mouseEnter(screen.getByLabelText(/Abrir busca rápida/i).closest('.topbar-quick-search'));
    const input = await screen.findByPlaceholderText(/Buscar no sistema/i);
    await user.type(input, 'forn');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Fornecedor XPTO/i })).toBeInTheDocument();
    });

    await user.keyboard('{Enter}');
    expect(mockNavigate).toHaveBeenCalledWith('/fornecedores');
  });
});
