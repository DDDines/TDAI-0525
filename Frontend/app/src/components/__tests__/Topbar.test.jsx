import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import Topbar from '../Topbar.jsx';
import { useAuth } from '../../contexts/AuthContext';

const mockNavigate = jest.fn();
const userMenuProps = [];

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
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
  });

  test('renders the topbar title and forwards sidebar toggle, logout and navigation handlers', async () => {
    const user = userEvent.setup();

    render(<Topbar viewTitle="Produtos" toggleSidebar={toggleSidebar} />);

    expect(screen.getByRole('heading', { name: 'Produtos' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Alternar menu/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'theme-toggle' })).toBeInTheDocument();
    expect(userMenuProps).toHaveLength(1);

    await user.click(screen.getByRole('button', { name: /Alternar menu/i }));
    expect(toggleSidebar).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: 'user-menu-nav' }));
    expect(mockNavigate).toHaveBeenCalledWith('/configuracoes');

    await user.click(screen.getByRole('button', { name: 'user-menu-logout' }));
    expect(logout).toHaveBeenCalledTimes(1);
  });
});
