/**
 * Module import progress.
 *
 * Defines responsibilities and integration points for components common.
 */

import React, { useEffect, useRef, useState } from 'react';
import fornecedorService from '../../services/fornecedorService';

const POLL_INTERVAL_MS = 3000;
const MAX_RESULT_WAIT_MS = 60000;
const MAX_RESULT_ATTEMPTS = 20;
const TERMINAL_STATUSES = new Set(['IMPORTED', 'DONE', 'PARTIAL', 'FAILED']);

function ImportProgress({ fileId, onDone }) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState('');
  const pollingRunRef = useRef(0);
  const onDoneRef = useRef(onDone);

  useEffect(() => {
    onDoneRef.current = onDone;
  }, [onDone]);

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
          const nextStatus = await fornecedorService.getImportacaoStatus(fileId);
          if (cancelled || pollingRunRef.current !== runId) return;

          setStatus(nextStatus);
          const statusNormalized = String(nextStatus?.status || '').trim().toUpperCase();
          const isTerminal = TERMINAL_STATUSES.has(statusNormalized);

          if (isTerminal) {
            if (!terminalDetectedAt) {
              terminalDetectedAt = Date.now();
            }
            resultAttempts += 1;

            const elapsedMs = Date.now() - terminalDetectedAt;
            const timeoutExceeded =
              elapsedMs >= MAX_RESULT_WAIT_MS || resultAttempts >= MAX_RESULT_ATTEMPTS;
            const statusSignalsReady = Boolean(nextStatus?.result_ready);

            if (!statusSignalsReady && timeoutExceeded) {
              setError(
                'Importacao concluida, mas o resultado final ainda nao foi consolidado. Tente novamente em instantes.'
              );
              onDoneRef.current?.(null);
              keepPolling = false;
            } else if (statusSignalsReady || timeoutExceeded) {
              try {
                const result = await fornecedorService.getImportacaoResult(fileId);
                if (cancelled || pollingRunRef.current !== runId) return;

                if (result?.ready === false) {
                  if (timeoutExceeded) {
                    setError(
                      'Resultado final ainda pendente apos o tempo limite de espera. Atualize em instantes.'
                    );
                    onDoneRef.current?.(null);
                    keepPolling = false;
                  } else {
                    keepPolling = true;
                  }
                } else {
                  onDoneRef.current?.(result);
                  keepPolling = false;
                }
              } catch {
                if (!cancelled) {
                  onDoneRef.current?.(null);
                }
                keepPolling = false;
              }
            }
          }

          if (keepPolling && !cancelled && pollingRunRef.current === runId) {
            await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
          }
        }
      } catch (pollingError) {
        if (!cancelled) {
          setError(pollingError.message || 'Erro ao consultar status');
          onDoneRef.current?.(null);
        }
      }
    };

    pollLoop();

    return () => {
      cancelled = true;
      pollingRunRef.current += 1;
    };
  }, [fileId]);

  if (error) {
    return <p style={{ color: 'red' }}>{error}</p>;
  }

  if (!status) {
    return <p>Iniciando processamento...</p>;
  }

  const statusNormalized = String(status?.status || '').trim().toUpperCase();
  const isTerminal = TERMINAL_STATUSES.has(statusNormalized);
  const pagesProcessed = status?.pages_processed ?? 0;
  const pagesTotal = status?.pages_total ?? status?.total_pages ?? 0;

  return (
    <div>
      <p>
        Status: {status.status} |{' '}
        {isTerminal
          ? `Paginas: ${pagesProcessed}/${pagesTotal}`
          : `Processando ${pagesProcessed} de ${pagesTotal} paginas...`}
      </p>
    </div>
  );
}

export default ImportProgress;
