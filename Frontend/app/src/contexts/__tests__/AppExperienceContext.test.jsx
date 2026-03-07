import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AppExperienceProvider, useAppExperience } from '../AppExperienceContext.jsx';
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
});
