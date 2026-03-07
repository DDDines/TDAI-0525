import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  AppExperienceProvider,
  loadStoredAdminPreviewMode,
  normalizeMode,
  persistAdminPreviewMode,
  removeStoredAdminPreviewMode,
  useAppExperience,
} from '../AppExperienceContext.jsx';
import configService from '../../services/configService';
import { useAuth } from '../AuthContext';

jest.mock('../../services/configService', () => ({
  __esModule: true,
  default: {
    getSocialLoginConfig: jest.fn(),
  },
}));

jest.mock('../AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
    error: jest.fn(),
  },
}));

function Probe() {
  const context = useAppExperience();
  return (
    <div>
      <div data-testid="loading">{String(context.isLoading)}</div>
      <div data-testid="effective-mode">{context.effectiveMode}</div>
      <div data-testid="default-mode">{context.defaultMode}</div>
      <div data-testid="admin-preview">{String(context.adminPreviewMode)}</div>
      <button onClick={() => context.setAdminPreviewMode('complete')}>preview-complete</button>
      <button onClick={() => context.clearAdminPreviewMode()}>clear-preview</button>
    </div>
  );
}

function DefaultProbe() {
  const context = useAppExperience();
  return (
    <div>
      <div data-testid="default-loading">{String(context.isLoading)}</div>
      <div data-testid="default-mode-fallback">{context.effectiveMode}</div>
      <button onClick={() => context.setAdminPreviewMode('complete')}>default-preview</button>
      <button onClick={() => context.clearAdminPreviewMode()}>default-clear</button>
    </div>
  );
}

describe('AppExperienceContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    useAuth.mockReturnValue({ user: null });
    configService.getSocialLoginConfig.mockResolvedValue({
      product_experience_default: 'complete',
      allow_admin_experience_preview: true,
    });
  });

  test('loads public config and exposes the default experience mode', async () => {
    render(
      <AppExperienceProvider>
        <Probe />
      </AppExperienceProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    expect(screen.getByTestId('default-mode')).toHaveTextContent('complete');
    expect(screen.getByTestId('effective-mode')).toHaveTextContent('complete');
  });

  test('allows admins to persist a preview mode override', async () => {
    useAuth.mockReturnValue({ user: { is_superuser: true } });
    configService.getSocialLoginConfig.mockResolvedValue({
      product_experience_default: 'basic',
      allow_admin_experience_preview: true,
    });

    render(
      <AppExperienceProvider>
        <Probe />
      </AppExperienceProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    expect(screen.getByTestId('effective-mode')).toHaveTextContent('basic');

    fireEvent.click(screen.getByText('preview-complete'));

    expect(screen.getByTestId('effective-mode')).toHaveTextContent('complete');
    expect(localStorage.getItem('catalogai_admin_preview_mode')).toBe('complete');

    fireEvent.click(screen.getByText('clear-preview'));

    expect(screen.getByTestId('effective-mode')).toHaveTextContent('basic');
    expect(localStorage.getItem('catalogai_admin_preview_mode')).toBeNull();
  });

  test('clears any stored admin preview when the user cannot use it', async () => {
    localStorage.setItem('catalogai_admin_preview_mode', 'complete');
    useAuth.mockReturnValue({ user: { is_superuser: false } });
    configService.getSocialLoginConfig.mockResolvedValue({
      product_experience_default: 'basic',
      allow_admin_experience_preview: true,
    });

    render(
      <AppExperienceProvider>
        <Probe />
      </AppExperienceProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    expect(screen.getByTestId('effective-mode')).toHaveTextContent('basic');
    expect(localStorage.getItem('catalogai_admin_preview_mode')).toBeNull();
  });

  test('ignores preview toggles for non-admin users and invalid stored preview values', async () => {
    localStorage.setItem('catalogai_admin_preview_mode', 'modo-invalido');
    useAuth.mockReturnValue({ user: { is_superuser: false } });
    configService.getSocialLoginConfig.mockResolvedValue({
      product_experience_default: 'basic',
      allow_admin_experience_preview: true,
    });

    render(
      <AppExperienceProvider>
        <Probe />
      </AppExperienceProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    fireEvent.click(screen.getByText('preview-complete'));

    expect(screen.getByTestId('admin-preview')).toHaveTextContent('null');
    expect(localStorage.getItem('catalogai_admin_preview_mode')).toBeNull();
  });

  test('falls back to safe defaults when config loading fails', async () => {
    configService.getSocialLoginConfig.mockRejectedValueOnce(new Error('offline'));

    render(
      <AppExperienceProvider>
        <Probe />
      </AppExperienceProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    expect(screen.getByTestId('default-mode')).toHaveTextContent('basic');
    expect(screen.getByTestId('effective-mode')).toHaveTextContent('basic');
  });

  test('normalizes invalid experience modes to basic', () => {
    expect(normalizeMode(' COMPLETE ')).toBe('complete');
    expect(normalizeMode('modo-invalido')).toBe('basic');
  });

  test('storage helpers are no-ops when window is unavailable', () => {
    const originalDescriptor = Object.getOwnPropertyDescriptor(window, 'localStorage');

    Object.defineProperty(window, 'localStorage', {
      value: undefined,
      configurable: true,
      writable: true,
    });

    expect(loadStoredAdminPreviewMode()).toBeNull();
    expect(() => persistAdminPreviewMode('complete')).not.toThrow();
    expect(() => removeStoredAdminPreviewMode()).not.toThrow();

    Object.defineProperty(window, 'localStorage', originalDescriptor);
  });

  test('ignores stored preview values that do not normalize exactly', () => {
    localStorage.setItem('catalogai_admin_preview_mode', ' COMPLETE ');

    expect(loadStoredAdminPreviewMode()).toBeNull();
  });

  test('exposes safe defaults even when used outside the provider', () => {
    render(<DefaultProbe />);

    expect(screen.getByTestId('default-loading')).toHaveTextContent('true');
    expect(screen.getByTestId('default-mode-fallback')).toHaveTextContent('basic');

    expect(() => fireEvent.click(screen.getByText('default-preview'))).not.toThrow();
    expect(() => fireEvent.click(screen.getByText('default-clear'))).not.toThrow();
  });
});
