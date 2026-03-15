/**
 * Module app experience context.
 *
 * Defines responsibilities and integration points for contexts.
 */

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useAuth } from './AuthContext';
import configService from '../services/configService';
import logger from '../utils/logger';

const EXPERIENCE_MODES = new Set(['basic', 'complete']);
const ADMIN_PREVIEW_STORAGE_KEY = 'catalogai_admin_preview_mode';
const DEFAULT_PUBLIC_CONFIG = {
  google_enabled: false,
  facebook_enabled: false,
  product_experience_default: 'basic',
  allow_admin_experience_preview: true,
};
const DEFAULT_CONTEXT_VALUE = {
  isLoading: true,
  effectiveMode: 'basic',
  defaultMode: 'basic',
  isAdmin: false,
  canAdminPreview: false,
  adminPreviewMode: null,
  setAdminPreviewMode: () => {},
  clearAdminPreviewMode: () => {},
};

const AppExperienceContext = createContext(DEFAULT_CONTEXT_VALUE);

function normalizeMode(value) {
  const normalized = String(value || '').trim().toLowerCase();
  return EXPERIENCE_MODES.has(normalized) ? normalized : 'basic';
}

function loadStoredAdminPreviewMode() {
  if (typeof window === 'undefined' || !window.localStorage) {
    return null;
  }
  const stored = window.localStorage.getItem(ADMIN_PREVIEW_STORAGE_KEY);
  if (!stored) {
    return null;
  }
  const normalized = normalizeMode(stored);
  return stored === normalized ? normalized : null;
}

function persistAdminPreviewMode(mode) {
  if (typeof window === 'undefined' || !window.localStorage) {
    return;
  }
  window.localStorage.setItem(ADMIN_PREVIEW_STORAGE_KEY, mode);
}

function removeStoredAdminPreviewMode() {
  if (typeof window === 'undefined' || !window.localStorage) {
    return;
  }
  window.localStorage.removeItem(ADMIN_PREVIEW_STORAGE_KEY);
}

function AppExperienceProvider({ children }) {
  const { user } = useAuth();
  const [publicConfig, setPublicConfig] = useState(DEFAULT_PUBLIC_CONFIG);
  const [isLoading, setIsLoading] = useState(true);
  const [adminPreviewMode, setAdminPreviewModeState] = useState(loadStoredAdminPreviewMode);

  useEffect(() => {
    let cancelled = false;
    async function loadConfig() {
      setIsLoading(true);
      try {
        const response = await configService.getSocialLoginConfig();
        if (!cancelled) {
          setPublicConfig({ ...DEFAULT_PUBLIC_CONFIG, ...(response || {}) });
        }
      } catch (error) {
        if (!cancelled) {
          logger.error('AppExperienceContext: fallback para config padrao.', error);
          setPublicConfig(DEFAULT_PUBLIC_CONFIG);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }
    void loadConfig();
    return () => {
      cancelled = true;
    };
  }, []);

  const isAdmin = Boolean(user?.is_superuser);
  const canAdminPreview = Boolean(publicConfig.allow_admin_experience_preview);
  const defaultMode = normalizeMode(publicConfig.product_experience_default);

  const effectiveMode = useMemo(() => {
    if (isAdmin && canAdminPreview && adminPreviewMode && EXPERIENCE_MODES.has(adminPreviewMode)) {
      return adminPreviewMode;
    }
    if (user?.product_experience_mode) {
      return normalizeMode(user.product_experience_mode);
    }
    return defaultMode;
  }, [adminPreviewMode, canAdminPreview, defaultMode, isAdmin, user?.product_experience_mode]);

  const setAdminPreviewMode = useCallback((mode) => {
    if (!isAdmin || !canAdminPreview) {
      return;
    }
    const normalized = normalizeMode(mode);
    setAdminPreviewModeState(normalized);
    persistAdminPreviewMode(normalized);
  }, [canAdminPreview, isAdmin]);

  const clearAdminPreviewMode = useCallback(() => {
    setAdminPreviewModeState(null);
    removeStoredAdminPreviewMode();
  }, []);

  useEffect(() => {
    if (!isAdmin || !canAdminPreview) {
      clearAdminPreviewMode();
    }
  }, [canAdminPreview, clearAdminPreviewMode, isAdmin]);

  const value = useMemo(() => ({
    isLoading,
    effectiveMode,
    defaultMode,
    isAdmin,
    canAdminPreview,
    adminPreviewMode,
    setAdminPreviewMode,
    clearAdminPreviewMode,
  }), [
    adminPreviewMode,
    canAdminPreview,
    clearAdminPreviewMode,
    defaultMode,
    effectiveMode,
    isAdmin,
    isLoading,
    setAdminPreviewMode,
  ]);

  return (
    <AppExperienceContext.Provider value={value}>
      {children}
    </AppExperienceContext.Provider>
  );
}

function useAppExperience() {
  return useContext(AppExperienceContext);
}

export {
  AppExperienceProvider,
  loadStoredAdminPreviewMode,
  normalizeMode,
  persistAdminPreviewMode,
  removeStoredAdminPreviewMode,
  useAppExperience,
};
