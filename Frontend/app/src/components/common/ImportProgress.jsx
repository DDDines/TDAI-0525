import React, { useEffect, useState } from 'react';
import fornecedorService from '../../services/fornecedorService';

function ImportProgress({ fileId, onDone }) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let timer;
    const poll = async () => {
      try {
        const s = await fornecedorService.getImportacaoStatus(fileId);
        setStatus(s);
        if (s.status === 'IMPORTED' || s.status === 'DONE') {
          clearInterval(timer);
          try {
            const result = await fornecedorService.getImportacaoResult(fileId);
            if (onDone) onDone(result);
          } catch (e) {
            if (onDone) onDone(null);
          }
        }
      } catch (e) {
        setError(e.message || 'Erro ao consultar status');
        clearInterval(timer);
      }
    };
    poll();
    timer = setInterval(poll, 3000);
    return () => clearInterval(timer);
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
        Processando {status.pages_processed} de {status.pages_total} páginas...
      </p>
    </div>
  );
}

export default ImportProgress;
