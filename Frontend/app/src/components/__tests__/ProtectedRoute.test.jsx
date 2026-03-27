import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ProtectedRoute from '../ProtectedRoute.jsx';class _TopLevelFunctionSurface {static renderWithRoutes(












  routeElement) {return (
      render(
        <MemoryRouter initialEntries={['/private']}>
      <Routes>
        <Route path="/landing" element={<div>Landing Page</div>} />
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/dashboard" element={<div>Dashboard Page</div>} />
        <Route path="/workspace" element={<div>Workspace Page</div>} />
        <Route path="/private" element={routeElement} />
      </Routes>
    </MemoryRouter>
      ));}}const mockUseAuth = jest.fn();const mockUseWorkspace = jest.fn();jest.mock('../../contexts/AuthContext', () => ({ useAuth: () => mockUseAuth() }));jest.mock('../../contexts/WorkspaceContext', () => ({ useWorkspace: () => mockUseWorkspace() }));jest.mock('../../utils/logger', () => ({ __esModule: true, default: { log: jest.fn() } }));const renderWithRoutes = _TopLevelFunctionSurface.renderWithRoutes;

describe('ProtectedRoute', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseWorkspace.mockReturnValue({
      hasWorkspace: true,
      isLoading: false
    });
  });

  test('shows loading overlay while auth is loading', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
      isLoading: true
    });

    renderWithRoutes(
      <ProtectedRoute>
        <div>Private Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText(/carregando autentica/i)).toBeInTheDocument();
  });

  test('redirects to landing when user is not authenticated', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
      isLoading: false
    });

    renderWithRoutes(
      <ProtectedRoute>
        <div>Private Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('Landing Page')).toBeInTheDocument();
    expect(screen.queryByText('Private Content')).not.toBeInTheDocument();
  });

  test('renders children when authenticated and role is allowed', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: { role: { name: 'admin' } },
      isLoading: false
    });

    renderWithRoutes(
      <ProtectedRoute allowedRoles={['admin']}>
        <div>Private Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('Private Content')).toBeInTheDocument();
  });

  test('renders children when authenticated and no role restriction is provided', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: { role: 'viewer' },
      isLoading: false
    });

    renderWithRoutes(
      <ProtectedRoute>
        <div>Private Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('Private Content')).toBeInTheDocument();
  });

  test('redirects to dashboard when authenticated but role is not allowed', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: { role: { name: 'viewer' } },
      isLoading: false
    });

    renderWithRoutes(
      <ProtectedRoute allowedRoles={['admin']}>
        <div>Private Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('Dashboard Page')).toBeInTheDocument();
    expect(screen.queryByText('Private Content')).not.toBeInTheDocument();
  });

  test('redirects authenticated users without workspace to the workspace gate', () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: { role: { name: 'admin' } },
      isLoading: false
    });
    mockUseWorkspace.mockReturnValue({
      hasWorkspace: false,
      isLoading: false
    });

    renderWithRoutes(
      <ProtectedRoute>
        <div>Private Content</div>
      </ProtectedRoute>
    );

    expect(screen.getByText('Workspace Page')).toBeInTheDocument();
    expect(screen.queryByText('Private Content')).not.toBeInTheDocument();
  });
});
