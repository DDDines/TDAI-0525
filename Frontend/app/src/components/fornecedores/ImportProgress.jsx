/**
 * Module import progress.
 *
 * Defines responsibilities and integration points for components fornecedores.
 */

import React, { useEffect } from 'react';
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

function ImportProgress({ jobId, onPendingReview }) {
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
    console.error('Erro ao consultar progresso de importacao:', progressQuery.error);
  }

  const { progress, totalPages } = normalizeProgressPayload(progressQuery.data);
  const percentage = totalPages ? Math.min(100, progress / totalPages * 100) : 0;

  return (
    <div className="import-progress">
      <p>{`Processando pÃ¡gina ${progress} de ${totalPages}`}</p>
      <div className="progress-container">
        <div className="progress-bar" style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}

export default ImportProgress;
