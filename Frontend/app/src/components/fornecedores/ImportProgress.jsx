/**
 * Module import progress.
 *
 * Defines responsibilities and integration points for components fornecedores.
 */

import React, { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import fornecedorService from '../../services/fornecedorService';
import { queryKeys } from '../../lib/queryKeys.js';
import './ImportProgress.css';

function normalizeProgressPayload(data) {
  return {
    progress: data?.pages_processed ?? data?.progress ?? 0,
    totalPages: data?.total_pages ?? 0,
    status: data?.status ?? '',
  };
}

function formatEta(seconds) {
  if (!seconds || seconds <= 0) return null;
  if (seconds < 60) return `~${Math.ceil(seconds)}s restantes`;
  const mins = Math.round(seconds / 60);
  return `~${mins} min restante${mins !== 1 ? 's' : ''}`;
}

function ImportProgress({ jobId, onPendingReview }) {
  const startTimeRef = useRef(null);
  const progressQuery = useQuery({
    queryKey: queryKeys.fornecedorImportProgress(jobId),
    enabled: Boolean(jobId),
    queryFn: () => fornecedorService.getImportProgress(jobId),
    refetchInterval: (query) => {
      if (!jobId || query.state.error) {
        return false;
      }
      const status = String(query.state.data?.status || '').toUpperCase();
      return status === 'PENDING_REVIEW' ? false : 3000;
    },
  });

  useEffect(() => {
    if (String(progressQuery.data?.status || '').toUpperCase() === 'PENDING_REVIEW') {
      onPendingReview?.();
    }
  }, [onPendingReview, progressQuery.data?.status]);

  if (progressQuery.error) {
    console.error('Erro ao consultar progresso de importação:', progressQuery.error);
  }

  const { progress, totalPages } = normalizeProgressPayload(progressQuery.data);
  const percentage = totalPages ? Math.min(100, (progress / totalPages) * 100) : 0;

  // ETA calculation based on elapsed time and pages done
  if (progress > 0 && !startTimeRef.current) {
    startTimeRef.current = Date.now();
  }
  let etaLabel = null;
  if (startTimeRef.current && progress > 0 && totalPages > progress) {
    const elapsedSec = (Date.now() - startTimeRef.current) / 1000;
    const secsPerPage = elapsedSec / progress;
    const remaining = totalPages - progress;
    etaLabel = formatEta(secsPerPage * remaining);
  }

  return (
    <div className="import-progress">
      <p>{`Processando página ${progress} de ${totalPages}${etaLabel ? ` — ${etaLabel}` : ''}`}</p>
      <div className="progress-container">
        <div className="progress-bar" style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}

export default ImportProgress;
