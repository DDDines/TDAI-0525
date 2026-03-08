/**
 * Module product table.
 *
 * Defines responsibilities and integration points for components produtos.
 */

import React from 'react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { LuFileText, LuPencil } from 'react-icons/lu';
import LoadingPopup from '../common/LoadingPopup.jsx';
import logger from '../../utils/logger';
import './ProductTable.css';

const STATUS_CONFIG = {
  NAO_INICIADO: { class: 'grey', text: '-', title: 'Nao iniciado' },
  PENDENTE: { class: 'orange', text: 'P', title: 'Pendente' },
  EM_PROGRESSO: { class: 'blue', text: '...', title: 'Em progresso' },
  CONCLUIDO: { class: 'green', text: 'OK', title: 'Concluido' },
  CONCLUIDO_SUCESSO: { class: 'green', text: 'OK', title: 'Concluido' },
  CONCLUIDO_COM_DADOS_PARCIAIS: { class: 'blue', text: 'PAR', title: 'Concluido com dados parciais' },
  FALHA: { class: 'red', text: 'X', title: 'Falha' },
  FALHOU: { class: 'red', text: 'X', title: 'Falhou' },
  FALHA_API_EXTERNA: { class: 'red', text: 'X', title: 'Falha de API externa' },
  FALHA_CONFIGURACAO_API_EXTERNA: { class: 'red', text: 'X', title: 'Falha de configuracao da API' },
  NENHUMA_FONTE_ENCONTRADA: { class: 'grey', text: '-', title: 'Nenhuma fonte encontrada' },
  NAO_APLICAVEL: { class: 'grey', text: '-', title: 'Nao aplicavel' },
};

const PROCESS_STATUS_CONFIG = [
  { key: 'status_enriquecimento_web', label: 'Web' },
  { key: 'status_titulo_ia', label: 'Tit' },
  { key: 'status_descricao_ia', label: 'Desc' },
];

function StatusIcon({ status }) {
  const rawStatus =
    typeof status === 'object' && status !== null && 'value' in status ? status.value : status;
  const normalizedStatus = String(rawStatus ?? '')
    .split('.')
    .pop()
    .toUpperCase();
  const cfg = STATUS_CONFIG[normalizedStatus] || { class: 'grey', text: '?', title: 'Desconhecido' };
  const { class: colorClass, text, title } = cfg;
  return (
    <span className={`status-icon ${colorClass}`} title={title}>
      {text}
    </span>
  );
}

function StatusSummary({ produto, showAiColumns }) {
  const processes = showAiColumns ? PROCESS_STATUS_CONFIG : PROCESS_STATUS_CONFIG.slice(0, 1);
  return (
    <div className="status-summary">
      {processes.map((processInfo) => (
        <span
          key={`${produto?.id || 'produto'}-${processInfo.key}`}
          className="status-process-chip"
          title={processInfo.label}
        >
          <span className="status-process-label">{processInfo.label}</span>
          <StatusIcon status={produto?.[processInfo.key]} />
        </span>
      ))}
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
  showAiColumns = true,
  loading,
  isLoading,
}) {
  const tableLoading = Boolean(loading || isLoading);
  const totalColumns = 8;

  logger.log('ProductTable: produtos:', produtos);
  logger.log('ProductTable: loading:', tableLoading);
  logger.log('ProductTable: selectedProdutos:', selectedProdutos);

  const getSortDirectionIcon = (key) => {
    if (sortConfig?.key === key) {
      return sortConfig.direction === 'ascending' ? ' ^' : ' v';
    }
    return '';
  };

  const safeProdutos = Array.isArray(produtos) ? produtos : [];
  const selectedSet = selectedProdutos instanceof Set ? selectedProdutos : new Set();
  const isAllSelected = safeProdutos.length > 0 && selectedSet.size === safeProdutos.length;

  const renderTableHeader = () => (
    <thead>
      <tr>
        <th>
          <input
            type="checkbox"
            checked={isAllSelected}
            onChange={(e) => onSelectAllProdutos(e.target.checked)}
            disabled={safeProdutos.length === 0 || tableLoading}
          />
        </th>
        <th onClick={() => onSort('id')}>ID</th>
        <th onClick={() => onSort('nome_base')}>Nome Base{getSortDirectionIcon('nome_base')}</th>
        <th onClick={() => onSort('sku')}>SKU{getSortDirectionIcon('sku')}</th>
        <th onClick={() => onSort('fornecedor_id')}>Fornecedor{getSortDirectionIcon('fornecedor_id')}</th>
        <th onClick={() => onSort('status_enriquecimento_web')}>Status{getSortDirectionIcon('status_enriquecimento_web')}</th>
        <th onClick={() => onSort('data_atualizacao')}>Atualizado Em{getSortDirectionIcon('data_atualizacao')}</th>
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
              <LoadingPopup isOpen={true} message="Carregando produtos..." />
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
            <td>{produto.sku || '--'}</td>
            <td>{produto.fornecedor_id ? `ID: ${produto.fornecedor_id}` : '--'}</td>
            <td>
              <StatusSummary produto={produto} showAiColumns={showAiColumns} />
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
