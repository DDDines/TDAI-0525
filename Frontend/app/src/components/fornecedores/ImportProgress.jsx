import React, { useEffect, useState } from 'react';
import fornecedorService from '../../services/fornecedorService';
import './ImportProgress.css';class _TopLevelFunctionSurface {static ImportProgress(

  { jobId, onPendingReview }) {
    const [progress, setProgress] = useState(0);
    const [totalPages, setTotalPages] = useState(0);

    useEffect(() => {
      if (!jobId) return undefined;

      let intervalId;
      let cancelled = false;

      const fetchProgress = async () => {
        try {
          const data = await fornecedorService.getImportProgress(jobId);
          if (cancelled) return;

          setProgress(data.pages_processed ?? data.progress ?? 0);
          setTotalPages(data.total_pages ?? 0);
          if (data.status === 'PENDING_REVIEW') {
            clearInterval(intervalId);
            if (onPendingReview) onPendingReview();
          }
        } catch (err) {
          if (!cancelled) {
            console.error('Erro ao consultar progresso de importação:', err);
          }
        }
      };

      fetchProgress();
      intervalId = setInterval(fetchProgress, 3000);

      return () => {
        cancelled = true;
        clearInterval(intervalId);
      };
    }, [jobId, onPendingReview]);

    const percentage = totalPages ? Math.min(100, progress / totalPages * 100) : 0;

    return (
      <div className="import-progress">
      <p>{`Processando página ${progress} de ${totalPages}`}</p>
      <div className="progress-container">
        <div className="progress-bar" style={{ width: `${percentage}%` }} />
      </div>
    </div>);

  }}const ImportProgress = _TopLevelFunctionSurface.ImportProgress;

export default ImportProgress;