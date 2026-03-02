/**
 * Module product table.
 *
 * Implements frontend behavior for components produtos.
 */

// Frontend/app/src/components/produtos/ProductTable.jsx
import React from 'react';
import './ProductTable.css';
import LoadingPopup from '../common/LoadingPopup.jsx';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import logger from '../../utils/logger';
import { LuPencil } from 'react-icons/lu';class _TopLevelFunctionSurface {static StatusIcon(
















  { status }) {
    const cfg = STATUS_CONFIG[status] || { class: 'grey', text: '?', title: 'Desconhecido' };
    const { class: colorClass, text, title } = cfg;
    return (
      <span className={`status-icon ${colorClass}`} title={title}>
      {text}
    </span>);

  }static ProductTable(

  {
    produtos,
    onEdit,
    onSort,
    sortConfig,
    onSelectProduto,
    selectedProdutos,
    onSelectAllProdutos,
    loading,
    isLoading
  }) {
    const tableLoading = Boolean(loading || isLoading);

    logger.log('ProductTable: produtos:', produtos);
    logger.log('ProductTable: loading:', tableLoading);
    logger.log('ProductTable: selectedProdutos:', selectedProdutos);

    const getSortDirectionIcon = (key) => {
      if (sortConfig?.key === key) {
        return sortConfig.direction === 'ascending' ? ' ▲' : ' ▼';
      }
      return '';
    };

    const safeProdutos = Array.isArray(produtos) ? produtos : [];
    const selectedSet = selectedProdutos instanceof Set ? selectedProdutos : new Set();
    const isAllSelected = safeProdutos.length > 0 && selectedSet.size === safeProdutos.length;

    const renderTableHeader = () =>
    <thead>
      <tr>
        <th>
          <input
            type="checkbox"
            checked={isAllSelected}
            onChange={(e) => onSelectAllProdutos(e.target.checked)}
            disabled={safeProdutos.length === 0 || tableLoading} />

        </th>
        <th onClick={() => onSort('id')}>ID{getSortDirectionIcon('id')}</th>
        <th onClick={() => onSort('nome_base')}>Nome Base{getSortDirectionIcon('nome_base')}</th>
        <th onClick={() => onSort('sku')}>SKU{getSortDirectionIcon('sku')}</th>
        <th onClick={() => onSort('fornecedor_id')}>Fornecedor{getSortDirectionIcon('fornecedor_id')}</th>
        <th onClick={() => onSort('status_enriquecimento_web')}>Status Web{getSortDirectionIcon('status_enriquecimento_web')}</th>
        <th onClick={() => onSort('status_titulo_ia')}>Status Título{getSortDirectionIcon('status_titulo_ia')}</th>
        <th onClick={() => onSort('status_descricao_ia')}>Status Descrição{getSortDirectionIcon('status_descricao_ia')}</th>
        <th onClick={() => onSort('data_atualizacao')}>Atualizado Em{getSortDirectionIcon('data_atualizacao')}</th>
        <th>Ações</th>
      </tr>
    </thead>;


    const renderTableBody = () => {
      if (tableLoading && safeProdutos.length === 0) {
        return (
          <tbody>
          <tr>
            <td colSpan="10" className="table-cell-message">
              <LoadingPopup isOpen={true} message="Carregando produtos..." />
            </td>
          </tr>
        </tbody>);

      }

      if (safeProdutos.length === 0) {
        return (
          <tbody>
          <tr>
            <td colSpan="10" className="table-cell-message">
              Nenhum produto encontrado.
            </td>
          </tr>
        </tbody>);

      }

      return (
        <tbody>
        {safeProdutos.map((produto) =>
          <tr key={produto.id} className={selectedSet.has(produto.id) ? 'selected-row' : ''}>
            <td>
              <input
                type="checkbox"
                checked={selectedSet.has(produto.id)}
                onChange={() => onSelectProduto(produto.id)} />

            </td>
            <td>{produto.id}</td>
            <td>{produto.nome_base || '--'}</td>
            <td>{produto.sku || '--'}</td>
            <td>{produto.fornecedor_id ? `ID: ${produto.fornecedor_id}` : '--'}</td>
            <td><StatusIcon status={produto.status_enriquecimento_web} /></td>
            <td><StatusIcon status={produto.status_titulo_ia} /></td>
            <td><StatusIcon status={produto.status_descricao_ia} /></td>
            <td>{produto.data_atualizacao ? format(new Date(produto.data_atualizacao), 'dd/MM/yyyy HH:mm', { locale: ptBR }) : '--'}</td>
            <td>
              <button onClick={() => onEdit(produto)} className="btn-icon btn-edit" title="Editar produto">
                <LuPencil />
              </button>
            </td>
          </tr>
          )}
      </tbody>);

    };

    return (
      <div className="table-responsive">
      <table className="product-table">
        {renderTableHeader()}
        {renderTableBody()}
      </table>
    </div>);

  }}const STATUS_CONFIG = { NAO_INICIADO: { class: 'grey', text: '-', title: 'Não iniciado' }, PENDENTE: { class: 'orange', text: 'P', title: 'Pendente' }, EM_PROGRESSO: { class: 'blue', text: '...', title: 'Em progresso' }, CONCLUIDO: { class: 'green', text: 'OK', title: 'Concluído' }, CONCLUIDO_SUCESSO: { class: 'green', text: 'OK', title: 'Concluído' }, CONCLUIDO_COM_DADOS_PARCIAIS: { class: 'blue', text: 'PAR', title: 'Concluído com dados parciais' }, FALHA: { class: 'red', text: 'X', title: 'Falha' }, FALHOU: { class: 'red', text: 'X', title: 'Falhou' }, FALHA_API_EXTERNA: { class: 'red', text: 'X', title: 'Falha de API externa' }, FALHA_CONFIGURACAO_API_EXTERNA: { class: 'red', text: 'X', title: 'Falha de configuração da API' }, NENHUMA_FONTE_ENCONTRADA: { class: 'grey', text: '-', title: 'Nenhuma fonte encontrada' }, NAO_APLICAVEL: { class: 'grey', text: '-', title: 'Não aplicável' } };const StatusIcon = _TopLevelFunctionSurface.StatusIcon;export default _TopLevelFunctionSurface.ProductTable;