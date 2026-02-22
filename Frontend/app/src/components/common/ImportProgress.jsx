import React, { useEffect, useRef, useState } from 'react';
import fornecedorService from '../../services/fornecedorService';

const POLL_INTERVAL_MS = 3000;
const MAX_RESULT_WAIT_MS = 60000;
const MAX_RESULT_ATTEMPTS = 20;

function ImportProgress({ fileId, onDone }) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');
  const pollingRunRef = useRef(0);

  useEffect(() => {
    if (!fileId) return undefined;

    let cancelled = false;
    let terminalDetectedAt = null;
    let resultAttempts = 0;
    const runId = Date.now();
    pollingRunRef.current = runId;

    const pollLoop = async () => {
      let keepPolling = true;
      try {
        while (keepPolling && !cancelled && pollingRunRef.current === runId) {
          const s = await fornecedorService.getImportacaoStatus(fileId);
          if (cancelled || pollingRunRef.current !== runId) return;

          setStatus(s);
          const terminalStatuses = new Set(['IMPORTED', 'DONE', 'PARTIAL', 'FAILED']);
          const statusNormalized = String(s?.status || '').trim().toUpperCase();
          const isTerminal = terminalStatuses.has(statusNormalized);

          if (isTerminal) {
            if (!terminalDetectedAt) {
              terminalDetectedAt = Date.now();
            }
            resultAttempts += 1;
            const elapsedMs = Date.now() - terminalDetectedAt;
            const timeoutExceeded =
              elapsedMs >= MAX_RESULT_WAIT_MS || resultAttempts >= MAX_RESULT_ATTEMPTS;
            const statusSignalsReady = Boolean(s?.result_ready);

            if (!statusSignalsReady && !timeoutExceeded) {
              keepPolling = true;
              continue;
            }

            if (!statusSignalsReady && timeoutExceeded) {
              if (!cancelled) {
                setError(
                  'Importação concluída, mas o resultado final ainda não foi consolidado. Tente novamente em instantes.'
                );
                if (onDone) onDone(null);
              }
              keepPolling = false;
              continue;
            }

            try {
              const result = await fornecedorService.getImportacaoResult(fileId);
              if (cancelled || pollingRunRef.current !== runId) return;
              if (result?.ready === false) {
                if (timeoutExceeded) {
                  setError(
                    'Resultado final ainda pendente após o tempo limite de espera. Atualize em instantes.'
                  );
                  if (onDone) onDone(null);
                  keepPolling = false;
                } else {
                  keepPolling = true;
                }
              } else {
                if (onDone) onDone(result);
                keepPolling = false;
              }
            } catch {
              if (!cancelled && onDone) onDone(null);
              keepPolling = false;
            }
          }

          if (keepPolling && !cancelled && pollingRunRef.current === runId) {
            await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
          }
        }
      } catch (e) {
        if (!cancelled) {
          setError(e.message || 'Erro ao consultar status');
          if (onDone) onDone(null);
        }
      }
    };

    pollLoop();

    return () => {
      cancelled = true;
      pollingRunRef.current += 1;
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
