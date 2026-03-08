/**
 * Module import progress.
 *
 * Defines responsibilities and integration points for components common.
 */

import React, { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import fornecedorService from '../../services/fornecedorService';
import { queryKeys } from '../../lib/queryKeys.js';

const POLL_INTERVAL_MS = 3000;
const MAX_RESULT_WAIT_MS = 60000;
const MAX_RESULT_ATTEMPTS = 20;
const TERMINAL_STATUSES = new Set(['IMPORTED', 'DONE', 'PARTIAL', 'FAILED']);

function normalizeStatus(statusPayload) {
  return String(statusPayload?.status || '').trim().toUpperCase();
}

function ImportProgress({ fileId, onDone }) {
  const [error, setError] = useState('');
  const [pollingEnabled, setPollingEnabled] = useState(Boolean(fileId));
  const queryClient = useQueryClient();
  const onDoneRef = useRef(onDone);
  const pollingRunRef = useRef(0);
  const terminalDetectedAtRef = useRef(null);
  const resultAttemptsRef = useRef(0);
  const completionNotifiedRef = useRef(false);

  useEffect(() => {
    onDoneRef.current = onDone;
  }, [onDone]);

  useEffect(() => {
    pollingRunRef.current += 1;
    terminalDetectedAtRef.current = null;
    resultAttemptsRef.current = 0;
    completionNotifiedRef.current = false;
    setError('');
    setPollingEnabled(Boolean(fileId));
    return () => {
      pollingRunRef.current += 1;
      completionNotifiedRef.current = true;
    };
  }, [fileId]);

  const statusQuery = useQuery({
    queryKey: queryKeys.catalogImportStatus(fileId),
    enabled: Boolean(fileId),
    queryFn: () => fornecedorService.getImportacaoStatus(fileId),
    refetchInterval: () => {
      if (!fileId || !pollingEnabled || completionNotifiedRef.current) {
        return false;
      }
      return POLL_INTERVAL_MS;
    },
  });

  useEffect(() => {
    if (!statusQuery.error || completionNotifiedRef.current) {
      return;
    }
    completionNotifiedRef.current = true;
    setPollingEnabled(false);
    setError(statusQuery.error.message || 'Erro ao consultar status');
    onDoneRef.current?.(null);
  }, [statusQuery.error]);

  useEffect(() => {
    const nextStatus = statusQuery.data;
    if (!fileId || !nextStatus || completionNotifiedRef.current) {
      return undefined;
    }

    const currentRun = pollingRunRef.current;
    const statusNormalized = normalizeStatus(nextStatus);
    const isTerminal = TERMINAL_STATUSES.has(statusNormalized);

    if (!isTerminal) {
      terminalDetectedAtRef.current = null;
      resultAttemptsRef.current = 0;
      return undefined;
    }

    if (!terminalDetectedAtRef.current) {
      terminalDetectedAtRef.current = Date.now();
    }
    resultAttemptsRef.current += 1;

    const elapsedMs = Date.now() - terminalDetectedAtRef.current;
    const timeoutExceeded =
      elapsedMs >= MAX_RESULT_WAIT_MS || resultAttemptsRef.current >= MAX_RESULT_ATTEMPTS;
    const statusSignalsReady = Boolean(nextStatus?.result_ready);

    if (!statusSignalsReady && timeoutExceeded) {
      completionNotifiedRef.current = true;
      setPollingEnabled(false);
      setError(
        'Importacao concluida, mas o resultado final ainda nao foi consolidado. Tente novamente em instantes.'
      );
      onDoneRef.current?.(null);
      return undefined;
    }

    if (!statusSignalsReady && !timeoutExceeded) {
      return undefined;
    }

    let cancelled = false;

    const fetchResult = async () => {
      try {
        const result = await fornecedorService.getImportacaoResult(fileId);
        if (cancelled || completionNotifiedRef.current || pollingRunRef.current !== currentRun) {
          return;
        }

        queryClient.setQueryData(queryKeys.catalogImportResult(fileId), result);

        if (result?.ready === false) {
          if (timeoutExceeded) {
            completionNotifiedRef.current = true;
            setPollingEnabled(false);
            setError(
              'Resultado final ainda pendente apos o tempo limite de espera. Atualize em instantes.'
            );
            onDoneRef.current?.(null);
          }
          return;
        }

        completionNotifiedRef.current = true;
        setPollingEnabled(false);
        onDoneRef.current?.(result);
      } catch {
        if (cancelled || completionNotifiedRef.current || pollingRunRef.current !== currentRun) {
          return;
        }
        completionNotifiedRef.current = true;
        setPollingEnabled(false);
        onDoneRef.current?.(null);
      }
    };

    void fetchResult();

    return () => {
      cancelled = true;
    };
  }, [fileId, queryClient, statusQuery.data, statusQuery.dataUpdatedAt]);

  const status = statusQuery.data;

  if (error) {
    return <p style={{ color: 'red' }}>{error}</p>;
  }

  if (!status) {
    return <p>Iniciando processamento...</p>;
  }

  const statusNormalized = normalizeStatus(status);
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
