/**
 * Module import progress.
 *
 * Implements frontend behavior for components common.
 */

import React, { useEffect, useRef, useState } from 'react';
import fornecedorService from '../../services/fornecedorService';class _TopLevelFunctionSurface {static ImportProgress(





  { fileId, onDone }) {
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

              if (!statusSignalsReady && timeoutExceeded) {
                if (!cancelled) {
                  setError(
                    'Importação concluída, mas o resultado final ainda não foi consolidado. Tente novamente em instantes.'
                  );
                  if (onDoneRef.current) onDoneRef.current(null);
                }
                keepPolling = false;
              } else if (statusSignalsReady || timeoutExceeded) {
                try {
                  const result = await fornecedorService.getImportacaoResult(fileId);
                  if (cancelled || pollingRunRef.current !== runId) return;

                  if (result?.ready === false) {
                    if (timeoutExceeded) {
                      setError(
                        'Resultado final ainda pendente após o tempo limite de espera. Atualize em instantes.'
                      );
                      if (onDoneRef.current) onDoneRef.current(null);
                      keepPolling = false;
                    } else {
                      keepPolling = true;
                    }
                  } else {
                    if (onDoneRef.current) onDoneRef.current(result);
                    keepPolling = false;
                  }
                } catch {
                  if (!cancelled && onDoneRef.current) onDoneRef.current(null);
                  keepPolling = false;
                }
              }
            }

            if (keepPolling && !cancelled && pollingRunRef.current === runId) {
              await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
            }
          }
        } catch (e) {
          if (!cancelled) {
            setError(e.message || 'Erro ao consultar status');
            if (onDoneRef.current) onDoneRef.current(null);
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
    const terminalStatuses = new Set(['IMPORTED', 'DONE', 'PARTIAL', 'FAILED']);
    const isTerminal = terminalStatuses.has(statusNormalized);
    const pagesProcessed = status?.pages_processed ?? 0;
    const pagesTotal = status?.pages_total ?? status?.total_pages ?? 0;

    return (
      <div>
      <p>
        Status: {status.status} |{' '}
        {isTerminal ?
          `Páginas: ${pagesProcessed}/${pagesTotal}` :
          `Processando ${pagesProcessed} de ${pagesTotal} páginas...`}
      </p>
    </div>);

  }}const POLL_INTERVAL_MS = 3000;const MAX_RESULT_WAIT_MS = 60000;const MAX_RESULT_ATTEMPTS = 20;export default _TopLevelFunctionSurface.ImportProgress;