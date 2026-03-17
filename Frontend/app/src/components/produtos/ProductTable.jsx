/**
 * Module product table.
 *
 * Defines responsibilities and integration points for components produtos.
 */

import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import {
  LuArrowDown,
  LuArrowUp,
  LuArrowUpDown,
  LuCircleCheck,
  LuCircleMinus,
  LuCircleX,
  LuClock3,
  LuFileText,
  LuGlobe,
  LuImage,
  LuListChecks,
  LuLoaderCircle,
  LuPencil,
  LuTriangleAlert,
  LuType,
} from 'react-icons/lu';
import logger from '../../utils/logger';
import './ProductTable.css';

const STATUS_CONFIG = {
  NAO_INICIADO: { class: 'grey', label: 'Nao iniciado', title: 'Nao iniciado', icon: LuCircleMinus },
  PENDENTE: { class: 'orange', label: 'Pendente', title: 'Pendente', icon: LuClock3 },
  EM_PROGRESSO: { class: 'blue', label: 'Em progresso', title: 'Em progresso', icon: LuLoaderCircle },
  CONCLUIDO: { class: 'green', label: 'Concluido', title: 'Concluido', icon: LuCircleCheck },
  CONCLUIDO_SUCESSO: { class: 'green', label: 'Concluido', title: 'Concluido', icon: LuCircleCheck },
  CONCLUIDO_COM_DADOS_PARCIAIS: {
    class: 'blue',
    label: 'Parcial',
    title: 'Concluido com dados parciais',
    icon: LuTriangleAlert,
  },
  FALHA: { class: 'red', label: 'Falha', title: 'Falha', icon: LuCircleX },
  FALHOU: { class: 'red', label: 'Falha', title: 'Falhou', icon: LuCircleX },
  FALHA_API_EXTERNA: { class: 'red', label: 'Falha API', title: 'Falha de API externa', icon: LuCircleX },
  FALHA_CONFIGURACAO_API_EXTERNA: {
    class: 'red',
    label: 'Config.',
    title: 'Falha de configuracao da API',
    icon: LuTriangleAlert,
  },
  NENHUMA_FONTE_ENCONTRADA: {
    class: 'red',
    label: 'Sem fonte',
    title: 'Nenhuma fonte encontrada',
    icon: LuCircleMinus,
  },
  NAO_APLICAVEL: { class: 'grey', label: 'Nao aplic.', title: 'Nao aplicavel', icon: LuCircleMinus },
};

const PROCESS_STATUS_CONFIG = [
  { key: 'status_enriquecimento_web', title: 'Enriquecimento web', icon: LuGlobe },
  { key: 'status_titulo_ia', title: 'Titulos', icon: LuType },
  { key: 'status_descricao_ia', title: 'Descricao', icon: LuFileText },
];

function QualityScoreBadge({ score }) {
  if (score == null) return <span className="quality-badge quality-badge--none">--</span>;
  const s = Math.round(score);
  const cls = s >= 75 ? 'quality-badge--high' : s >= 45 ? 'quality-badge--mid' : 'quality-badge--low';
  return <span className={`quality-badge ${cls}`} title={`Score de qualidade: ${s}/100`}>{s}</span>;
}

function normalizeStatusValue(status) {
  const rawStatus =
    typeof status === 'object' && status !== null && 'value' in status ? status.value : status;
  return String(rawStatus ?? '')
    .split('.')
    .pop()
    .toUpperCase();
}

function getStatusConfig(status) {
  const normalizedStatus = normalizeStatusValue(status);
  const cfg = STATUS_CONFIG[normalizedStatus] || {
    class: 'grey',
    label: 'Desconhecido',
    title: 'Desconhecido',
    icon: LuTriangleAlert,
  };
  return { normalizedStatus, cfg };
}

function extractWebFailureReason(produto) {
  const historico = Array.isArray(produto?.log_enriquecimento_web?.historico_mensagens)
    ? produto.log_enriquecimento_web.historico_mensagens
    : [];
  const relevantes = historico.filter((item) =>
    /falha|erro|alerta|nenhuma fonte|configuracao|api/i.test(String(item || ''))
  );
  return String(relevantes.at(-1) || historico.at(-1) || '').trim();
}

function extractGenerationFailureReason(produto, generationTitle) {
  const logEntries = Array.isArray(produto?.log_processamento) ? produto.log_processamento : [];
  const prefix = `IA ${generationTitle}`;
  const matchingEntry = [...logEntries].reverse().find((entry) => {
    const action = String(entry?.action || '');
    return action.includes(prefix) && /falha|erro/i.test(action);
  });
  return String(matchingEntry?.action || '').trim();
}

function resolveStatusReason(produto, processKey) {
  if (processKey === 'status_enriquecimento_web') {
    return extractWebFailureReason(produto);
  }
  if (processKey === 'status_titulo_ia') {
    return extractGenerationFailureReason(produto, 'Titulo');
  }
  if (processKey === 'status_descricao_ia') {
    return extractGenerationFailureReason(produto, 'Descricao');
  }
  return '';
}

function cleanTooltipNoise(text) {
  return String(text || '')
    .replace(/traceback[\s\S]*$/i, '')
    .replace(/file\s+["'][^"']+["'].*$/gim, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function extractUserFacingReason(rawReason) {
  const normalized = cleanTooltipNoise(rawReason)
    .replace(/^enriquecimento web:\s*/i, '')
    .replace(/^ia\s+(titulo|descricao):\s*/i, '')
    .replace(/^falhou?\.\s*/i, '')
    .replace(/^falha\s*(?:\(\d{3}\))?\s*[:.-]?\s*/i, '')
    .replace(/^erro critico inesperado no processo:\s*/i, '')
    .replace(/^erro critico inesperado\s*[:.-]?\s*/i, '')
    .replace(/^erro\s*[:.-]?\s*/i, '')
    .trim();

  if (!normalized) {
    return '';
  }

  const lowered = normalized.toLowerCase();

  if (/unexpected keyword argument ['"]api_key['"]/.test(normalized)) {
    return 'Falha interna na integracao de busca Google.';
  }
  if (/401|unauthorized|nao autorizado|não autorizado/.test(lowered)) {
    return 'Credencial invalida ou sem autorizacao.';
  }
  if (/403|forbidden|acesso negado/.test(lowered)) {
    return 'Acesso negado pela API configurada.';
  }
  if (/404|not found|nao encontrado|não encontrado/.test(lowered)) {
    return 'Fonte ou recurso nao encontrado.';
  }
  if (/409/.test(lowered)) {
    return 'Conflito ao processar a solicitacao.';
  }
  if (/422/.test(lowered)) {
    const detail = normalized
      .replace(/^falha\s*\(422\)\s*-\s*/i, '')
      .replace(/^422\s*[-: ]\s*/i, '')
      .trim();
    return detail || 'Entrada invalida para processar o conteudo.';
  }
  if (/429|rate limit|limite de requisi/.test(lowered)) {
    return 'Limite de requisicoes atingido. Tente novamente em instantes.';
  }
  if (/500|502|503|504|bad gateway|service unavailable|gateway timeout/.test(lowered)) {
    return 'Servico externo indisponivel no momento.';
  }
  if (/timeout|timed out|tempo limite/.test(lowered)) {
    return 'Tempo limite excedido ao consultar a fonte.';
  }
  if (/nenhuma fonte/.test(lowered)) {
    return 'Nenhuma fonte relevante foi encontrada.';
  }
  if (
    /nome_chat_api|dynamic_attributes|titulo_auto|desc_auto|id_auto|url da fonte|url_da_fonte/i.test(
      normalized
    )
  ) {
    return '';
  }
  if (/configura/.test(lowered) && /api|google|gemini|openai|cse/.test(lowered)) {
    return 'Configuracao da integracao incompleta ou invalida.';
  }

  const withoutPrefix = normalized
    .replace(/^\(?\d{3}\)?\s*[-: ]\s*/i, '')
    .replace(/^[A-Z_ ]+:\s*/i, '')
    .trim();

  return withoutPrefix || 'Falha ao processar esta etapa.';
}

function buildStatusTooltip(processInfo, cfgTitle, reason) {
  const humanReason = extractUserFacingReason(reason);
  const shouldExposeReason = /falha|falhou|erro|nenhuma fonte|config/i.test(
    String(cfgTitle || '').toLowerCase()
  );
  const isNoSource = /nenhuma fonte/i.test(String(cfgTitle || '').toLowerCase());

  if (isNoSource && !humanReason) {
    return `${processInfo.title}: Nenhuma fonte encontrada para este produto.`;
  }

  return shouldExposeReason && humanReason
    ? `${processInfo.title}: ${cfgTitle}. ${humanReason}`
    : `${processInfo.title}: ${cfgTitle}`;
}

function ProcessStatusIcon({ produto, processInfo, onAction }) {
  const { normalizedStatus, cfg } = getStatusConfig(produto?.[processInfo.key]);
  const reason = resolveStatusReason(produto, processInfo.key);
  const tooltip = buildStatusTooltip(processInfo, cfg.title, reason);
  const ProcessIcon = processInfo.icon;
  const isClickable = typeof onAction === 'function' && normalizedStatus !== 'EM_PROGRESSO';
  const content = (
    <span
      className={`status-process-indicator ${cfg.class}${isClickable ? ' is-actionable' : ''}`}
      title={isClickable ? undefined : tooltip}
      aria-label={isClickable ? undefined : tooltip}
      data-status-key={processInfo.key}
    >
      <ProcessIcon
        className={`status-process-icon ${normalizedStatus === 'EM_PROGRESSO' ? 'is-spinning' : ''}`}
        aria-hidden="true"
      />
    </span>
  );

  if (!isClickable) {
    return content;
  }

  return (
    <button
      type="button"
      className="status-process-trigger"
      title={tooltip}
      aria-label={tooltip}
      onClick={(event) => {
        event.stopPropagation();
        onAction(produto, processInfo.key);
      }}
    >
      {content}
    </button>
  );
}

function StatusSummary({ produto, showAiColumns, onProcessAction }) {
  const processes = showAiColumns ? PROCESS_STATUS_CONFIG : PROCESS_STATUS_CONFIG.slice(0, 1);
  return (
    <div className="status-summary">
      {processes.map((processInfo) => (
        <span key={`${produto?.id || 'produto'}-${processInfo.key}`} className="status-process-chip">
          <ProcessStatusIcon
            produto={produto}
            processInfo={processInfo}
            onAction={onProcessAction}
          />
        </span>
      ))}
    </div>
  );
}

function ProductMediaPreview({ produto }) {
  const imageUrl = String(produto?.imagem_principal_url || '').trim();
  const [isZoomOpen, setIsZoomOpen] = useState(false);
  const [isZoomPinned, setIsZoomPinned] = useState(false);
  const [flyoutPosition, setFlyoutPosition] = useState({ top: 0, left: 0 });
  const wrapperRef = useRef(null);
  const triggerRef = useRef(null);
  const flyoutRef = useRef(null);

  useEffect(() => {
    if (!isZoomOpen || !triggerRef.current) {
      return undefined;
    }

    const updateFlyoutPosition = () => {
      const rect = triggerRef.current?.getBoundingClientRect();
      const rowRect = triggerRef.current?.closest('tr')?.getBoundingClientRect();
      if (!rect) {
        return;
      }

      const flyoutWidth = 220;
      const flyoutHeight = 220;
      const gap = 14;
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      let left = rect.right + gap;
      if (left + flyoutWidth > viewportWidth - 12) {
        left = rect.left - flyoutWidth - gap;
      }
      if (left < 12) {
        left = Math.max(12, Math.min(viewportWidth - flyoutWidth - 12, rect.left));
      }

      const anchoredRowTop = rowRect ? rowRect.top + 6 : rect.top;
      let top = anchoredRowTop;
      if (top + flyoutHeight > viewportHeight - 12) {
        top = viewportHeight - flyoutHeight - 12;
      }
      if (top < 12) {
        top = 12;
      }

      if (viewportWidth <= 860) {
        left = Math.max(12, Math.min(viewportWidth - flyoutWidth - 12, rect.left + rect.width / 2 - flyoutWidth / 2));
        top = Math.min(viewportHeight - flyoutHeight - 12, rect.bottom + 12);
      }

      setFlyoutPosition({ top, left });
    };

    updateFlyoutPosition();
    window.addEventListener('scroll', updateFlyoutPosition, true);
    window.addEventListener('resize', updateFlyoutPosition);

    return () => {
      window.removeEventListener('scroll', updateFlyoutPosition, true);
      window.removeEventListener('resize', updateFlyoutPosition);
    };
  }, [isZoomOpen]);

  useEffect(() => {
    if (!isZoomPinned) {
      return undefined;
    }

    const handlePointerDown = (event) => {
      const target = event.target;
      if (wrapperRef.current?.contains(target) || flyoutRef.current?.contains(target)) {
        return;
      }
      setIsZoomPinned(false);
      setIsZoomOpen(false);
    };

    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        setIsZoomPinned(false);
        setIsZoomOpen(false);
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isZoomPinned]);

  const openPreview = () => setIsZoomOpen(true);
  const closePreview = () => {
    if (!isZoomPinned) {
      setIsZoomOpen(false);
    }
  };

  if (imageUrl) {
    return (
      <div
        ref={wrapperRef}
        className={`product-media-zoom${isZoomOpen ? ' is-open' : ''}`}
        onMouseEnter={openPreview}
        onMouseLeave={closePreview}
      >
        <button
          type="button"
          ref={triggerRef}
          className="product-media-trigger"
          title="Clique para ampliar a miniatura"
          aria-label={`Ampliar miniatura de ${produto?.nome_base || 'produto'}`}
          aria-expanded={isZoomOpen}
          onFocus={openPreview}
          onBlur={closePreview}
          onClick={(event) => {
            event.stopPropagation();
            const nextPinned = !isZoomPinned;
            setIsZoomPinned(nextPinned);
            setIsZoomOpen(nextPinned);
          }}
        >
          <div className="product-media-thumb">
            <img src={imageUrl} alt={`Miniatura de ${produto?.nome_base || 'produto'}`} loading="lazy" />
          </div>
        </button>

        {isZoomOpen
          ? createPortal(
              <div
                ref={flyoutRef}
                className="product-media-flyout"
                role="presentation"
                style={{ top: `${flyoutPosition.top}px`, left: `${flyoutPosition.left}px` }}
              >
                <div className="product-media-flyout-frame">
                  <img
                    src={imageUrl}
                    alt={`Preview ampliado de ${produto?.nome_base || 'produto'}`}
                    loading="lazy"
                  />
                </div>
              </div>,
              document.body
            )
          : null}
      </div>
    );
  }

  return (
    <div className="product-media-thumb is-empty" title="Produto sem miniatura">
      <LuImage aria-hidden="true" />
    </div>
  );
}

function ProductTable({
  produtos,
  onEdit,
  onSort,
  sortConfig,
  onViewContent,
  onSelectProduto,
  selectedProdutos,
  onSelectAllProdutos,
  selectionMenuItems = [],
  showAiColumns = true,
  loading,
  isLoading,
  onProcessAction,
}) {
  const tableLoading = Boolean(loading || isLoading);
  const totalColumns = 10;
  const [isSelectionMenuOpen, setIsSelectionMenuOpen] = useState(false);
  const selectionMenuRef = useRef(null);

  logger.log('ProductTable: produtos:', produtos);
  logger.log('ProductTable: loading:', tableLoading);
  logger.log('ProductTable: selectedProdutos:', selectedProdutos);

  const getSortDirectionIcon = (key) => {
    if (sortConfig?.key === key) {
      return sortConfig.direction === 'ascending' ? LuArrowUp : LuArrowDown;
    }
    return LuArrowUpDown;
  };

  const getSortDirectionState = (key) => {
    if (sortConfig?.key !== key) {
      return 'none';
    }
    return sortConfig.direction === 'ascending' ? 'ascending' : 'descending';
  };

  const renderSortableHeader = (key, label) => {
    const SortIcon = getSortDirectionIcon(key);
    const sortDirection = getSortDirectionState(key);

    return (
      <th onClick={() => onSort(key)} data-sort-direction={sortDirection}>
        <span className="sortable-header-content">
          <span>{label}</span>
          <SortIcon className={`sortable-header-icon is-${sortDirection}`} aria-hidden="true" />
        </span>
      </th>
    );
  };

  const safeProdutos = Array.isArray(produtos) ? produtos : [];
  const selectedSet = selectedProdutos instanceof Set ? selectedProdutos : new Set();
  const isAllSelected = safeProdutos.length > 0 && selectedSet.size === safeProdutos.length;
  const hasSelectionMenu = Array.isArray(selectionMenuItems) && selectionMenuItems.length > 0;

  useEffect(() => {
    if (!isSelectionMenuOpen) {
      return undefined;
    }

    const handlePointerDown = (event) => {
      if (selectionMenuRef.current && !selectionMenuRef.current.contains(event.target)) {
        setIsSelectionMenuOpen(false);
      }
    };

    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        setIsSelectionMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isSelectionMenuOpen]);

  const renderTableHeader = () => (
    <thead>
      <tr>
        <th className="selection-column-header">
          <div className="selection-header-controls">
            {hasSelectionMenu ? (
              <div className="selection-menu" ref={selectionMenuRef}>
                <button
                  type="button"
                  className={`selection-menu-trigger${selectedSet.size > 0 ? ' is-active' : ''}`}
                  aria-label="Opcoes de selecao"
                  aria-haspopup="menu"
                  aria-expanded={isSelectionMenuOpen}
                  disabled={safeProdutos.length === 0 || tableLoading}
                  onClick={() => setIsSelectionMenuOpen((current) => !current)}
                >
                  <LuListChecks aria-hidden="true" />
                </button>

                {isSelectionMenuOpen ? (
                  <div className="selection-menu-dropdown" role="menu" aria-label="Opcoes de selecao">
                    {selectionMenuItems.map((item) => (
                      <button
                        key={item.key}
                        type="button"
                        role="menuitem"
                        className={`selection-menu-item${item.tone === 'danger' ? ' is-danger' : ''}`}
                        onClick={() => {
                          setIsSelectionMenuOpen(false);
                          item.onClick?.();
                        }}
                        disabled={Boolean(item.disabled)}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              <label className="selection-header-toggle" title="Selecionar pagina atual">
                <input
                  type="checkbox"
                  aria-label="Selecionar pagina atual"
                  checked={isAllSelected}
                  onChange={(e) => onSelectAllProdutos(e.target.checked)}
                  disabled={safeProdutos.length === 0 || tableLoading}
                />
              </label>
            )}
          </div>
        </th>
        {renderSortableHeader('id', 'ID')}
        {renderSortableHeader('nome_base', 'Nome Base')}
        <th className="product-media-column-header" aria-label="Miniatura" />
        {renderSortableHeader('sku', 'SKU')}
        {renderSortableHeader('fornecedor_id', 'Fornecedor')}
        {renderSortableHeader('status_enriquecimento_web', 'Status')}
        <th title="Score de qualidade do import (0–100)">Qualidade</th>
        {renderSortableHeader('data_atualizacao', 'Atualizado Em')}
        <th>Acoes</th>
      </tr>
    </thead>
  );

  const renderTableBody = () => {
    if (tableLoading && safeProdutos.length === 0) {
      return (
        <tbody>
          <tr>
            <td colSpan={totalColumns} className="table-cell-message">
              <div className="table-inline-loading" role="status" aria-live="polite">
                <span className="table-inline-spinner" aria-hidden="true" />
                <span>Carregando produtos...</span>
              </div>
            </td>
          </tr>
        </tbody>
      );
    }

    if (safeProdutos.length === 0) {
      return (
        <tbody>
          <tr>
            <td colSpan={totalColumns} className="table-cell-message">
              Nenhum produto encontrado.
            </td>
          </tr>
        </tbody>
      );
    }

    return (
      <tbody>
        {safeProdutos.map((produto) => (
          <tr
            key={produto.id}
            className={`${selectedSet.has(produto.id) ? 'selected-row' : ''} ${typeof onViewContent === 'function' ? 'row-open-content' : ''}`}
            onDoubleClick={typeof onViewContent === 'function' ? () => onViewContent(produto) : undefined}
            title={typeof onViewContent === 'function' ? 'Duplo clique para abrir conteúdo gerado' : undefined}
          >
            <td>
              <input
                type="checkbox"
                checked={selectedSet.has(produto.id)}
                onClick={(event) => event.stopPropagation()}
                onChange={() => onSelectProduto(produto.id)}
              />
            </td>
            <td>{produto.id}</td>
            <td>{produto.nome_base || '--'}</td>
            <td className="product-media-column">
              <ProductMediaPreview produto={produto} />
            </td>
            <td>{produto.sku || '--'}</td>
            <td>{produto.fornecedor_id ? `ID: ${produto.fornecedor_id}` : '--'}</td>
            <td>
              <StatusSummary
                produto={produto}
                showAiColumns={showAiColumns}
                onProcessAction={onProcessAction}
              />
            </td>
            <td className="quality-score-column">
              <QualityScoreBadge score={produto.import_quality_score} />
            </td>
            <td>
              {produto.data_atualizacao
                ? format(new Date(produto.data_atualizacao), 'dd/MM/yyyy HH:mm', { locale: ptBR })
                : '--'}
            </td>
            <td>
              {typeof onViewContent === 'function' ? (
                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    onViewContent(produto);
                  }}
                  className="btn-icon btn-view-content"
                  title="Ver conteúdo gerado"
                >
                  <LuFileText />
                </button>
              ) : null}
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  onEdit(produto);
                }}
                className="btn-icon btn-edit"
                title="Editar produto"
              >
                <LuPencil />
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    );
  };

  return (
    <div className="table-responsive">
      <table className="product-table">
        {renderTableHeader()}
        {renderTableBody()}
      </table>
    </div>
  );
}

export default ProductTable;
