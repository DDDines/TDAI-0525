/**
 * Module workspace context.
 *
 * Centralizes the active company/workspace state so the authenticated shell can
 * enforce onboarding, permissions, and company-scoped navigation.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import workspaceService from '../services/workspaceService';
import { useAuth } from './AuthContext';

const WorkspaceContext = createContext(null);

function WorkspaceProvider({ children }) {
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const [workspace, setWorkspace] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const clearWorkspace = useCallback(() => {
    setWorkspace(null);
    setError(null);
    setIsLoading(false);
  }, []);

  const refreshWorkspace = useCallback(async () => {
    if (!isAuthenticated) {
      clearWorkspace();
      return null;
    }

    setIsLoading(true);
    try {
      const data = await workspaceService.getWorkspace();
      setWorkspace(data);
      setError(null);
      return data;
    } catch (err) {
      if (err?.response?.status === 404) {
        setWorkspace(null);
        setError(null);
        return null;
      }
      setWorkspace(null);
      setError(err);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [clearWorkspace, isAuthenticated]);

  useEffect(() => {
    if (isAuthLoading) {
      setIsLoading(true);
      return;
    }

    if (!isAuthenticated) {
      clearWorkspace();
      return;
    }

    void refreshWorkspace();
  }, [clearWorkspace, isAuthenticated, isAuthLoading, refreshWorkspace]);

  const value = useMemo(
    () => ({
      workspace,
      currentWorkspace: workspace,
      workspaceName: workspace?.nome || '',
      hasWorkspace: Boolean(workspace?.id),
      isLoading,
      error,
      setWorkspace,
      refreshWorkspace,
      clearWorkspace,
    }),
    [workspace, isLoading, error, refreshWorkspace, clearWorkspace]
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (context === undefined || context === null) {
    throw new Error('useWorkspace deve ser usado dentro de um WorkspaceProvider');
  }
  return context;
}

export { WorkspaceProvider, useWorkspace };
