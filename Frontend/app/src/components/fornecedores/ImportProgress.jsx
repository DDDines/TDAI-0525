import React, { useEffect, useState } from 'react';
import fornecedorService from '../../services/fornecedorService';
import './ImportProgress.css';

function ImportProgress({ jobId, onPendingReview }) {
  const [progress, setProgress] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  useEffect(() => {
    if (!jobId) return undefined;
    let intervalId;

    const fetchProgress = async () => {
      try {
        const data = await fornecedorService.getImportProgress(jobId);
        setProgress(data.pages_processed ?? 0);
        setTotalPages(data.total_pages ?? 0);
        if (data.status === 'PENDING_REVIEW') {
          clearInterval(intervalId);
          if (onPendingReview) onPendingReview();
        }
      } catch (err) {
        console.error('Erro ao consultar progresso de importação:', err);
      }
    };

    fetchProgress();
    intervalId = setInterval(fetchProgress, 3000);

    return () => clearInterval(intervalId);
  }, [jobId, onPendingReview]);

  const percentage = totalPages ? Math.min(100, (progress / totalPages) * 100) : 0;

  return (
    <div className="import-progress">
      <p>{`Processando página ${progress} de ${totalPages}`}</p>
      <div className="progress-container">
        <div className="progress-bar" style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}

export default ImportProgress;
