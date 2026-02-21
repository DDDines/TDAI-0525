import React, { useEffect, useState } from 'react';
import fornecedorService from '../../services/fornecedorService';

function ImportProgress({ fileId, onDone }) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!fileId) return undefined;

    let timer;
    let cancelled = false;

    const stopPolling = () => {
      if (timer) clearInterval(timer);
    };

    const poll = async () => {
      try {
        const s = await fornecedorService.getImportacaoStatus(fileId);
        if (cancelled) return;

        setStatus(s);
        if (
          s.status === 'IMPORTED' ||
          s.status === 'DONE' ||
          s.status === 'PARTIAL' ||
          s.status === 'FAILED'
        ) {
          stopPolling();
          try {
            const result = await fornecedorService.getImportacaoResult(fileId);
            if (!cancelled && onDone) onDone(result);
          } catch {
            if (!cancelled && onDone) onDone(null);
          }
        }
      } catch (e) {
        if (!cancelled) {
          setError(e.message || 'Erro ao consultar status');
        }
        stopPolling();
      }
    };

    poll();
    timer = setInterval(poll, 3000);

    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [fileId, onDone]);

  if (error) {
    return <p style={{ color: 'red' }}>{error}</p>;
  }
  if (!status) {
    return <p>Iniciando processamento...</p>;
  }
  return (
    <div>
      <p>
        Status: {status.status} | Processando {status.pages_processed} de {status.pages_total} páginas...
      </p>
    </div>
  );
}

export default ImportProgress;
