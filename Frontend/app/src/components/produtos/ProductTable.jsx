// Frontend/app/src/components/produtos/ProductTable.jsx
import React from 'react';
import './ProductTable.css'; // Seu CSS para a tabela. Deve existir em src/components/produtos/ProductTable.css
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import logger from '../../utils/logger';

const STATUS_CONFIG = {
  NAO_INICIADO: { class: 'grey', text: '➖', title: 'Não Iniciado' },
  PENDENTE: { class: 'orange', text: '⏳', title: 'Pendente' },
  EM_PROGRESSO: { class: 'blue', text: '⚙️', title: 'Em Progresso' },
  CONCLUIDO: { class: 'green', text: '✔️', title: 'Concluído' },
  CONCLUIDO_SUCESSO: { class: 'green', text: '✔️', title: 'Concluído' },
  CONCLUIDO_COM_DADOS_PARCIAIS: { class: 'blue', text: '✔️', title: 'Parcial' },
  FALHA: { class: 'red', text: '❌', title: 'Falha' },
  FALHOU: { class: 'red', text: '❌', title: 'Falhou' },
  FALHA_API_EXTERNA: { class: 'red', text: '❌', title: 'Falha API Externa' },
  FALHA_CONFIGURACAO_API_EXTERNA: { class: 'red', text: '❌', title: 'Falha Configuração API' },
  NENHUMA_FONTE_ENCONTRADA: { class: 'grey', text: '➖', title: 'Fonte Não Encontrada' },
  NAO_APLICAVEL: { class: 'grey', text: '➖', title: 'Não Aplicável' },
};

const StatusIcon = ({ status }) => {
  const cfg = STATUS_CONFIG[status] || { class: 'grey', text: '?', title: 'Desconhecido' };
  const { class: colorClass, text, title } = cfg;
  return <span className={`status-icon ${colorClass}`} title={title}>{text}</span>;
};


function ProductTable({
  produtos,
  onEdit,
  onSort,
  sortConfig,
  onSelectProduto,
  selectedProdutos,
  onSelectAllProdutos, 
  loading, 
}) {
  logger.log('ProductTable: Props recebidos - produtos:', produtos);
  logger.log('ProductTable: Props recebidos - loading:', loading);
  logger.log('ProductTable: Props recebidos - selectedProdutos:', selectedProdutos);

  const getSortDirectionIcon = (key) => {
    if (sortConfig.key === key) {
      return sortConfig.direction === 'ascending' ? ' ▲' : ' ▼';
    }
    return ''; 
  };

  const isAllSelected = produtos && produtos.length > 0 && selectedProdutos.size === produtos.length;

  const renderTableHeader = () => (
    <thead>
      <tr>
        <th>
          <input 
            type="checkbox" 
            checked={isAllSelected}
            onChange={(e) => onSelectAllProdutos(e.target.checked)}
            disabled={!produtos || produtos.length === 0 || loading}
          />
        </th>
        <th onClick={() => onSort('id')}>ID {getSortDirectionIcon('id')}</th>
        <th onClick={() => onSort('nome_base')}>Nome Base {getSortDirectionIcon('nome_base')}</th>
        <th onClick={() => onSort('sku')}>SKU {getSortDirectionIcon('sku')}</th>
        <th onClick={() => onSort('fornecedor_id')}>Fornecedor {getSortDirectionIcon('fornecedor_id')}</th>
        <th onClick={() => onSort('status_enriquecimento_web')}>Status Web {getSortDirectionIcon('status_enriquecimento_web')}</th>
        <th onClick={() => onSort('status_titulo_ia')}>Status Título {getSortDirectionIcon('status_titulo_ia')}</th>
        <th onClick={() => onSort('status_descricao_ia')}>Status Desc. {getSortDirectionIcon('status_descricao_ia')}</th>
        <th onClick={() => onSort('data_atualizacao')}>Atualizado em {getSortDirectionIcon('data_atualizacao')}</th>
        <th>Ações</th>
      </tr>
    </thead>
  );

  const renderTableBody = () => {
    if (loading && (!produtos || produtos.length === 0)) { 
        return <tbody><tr><td colSpan="10" style={{ textAlign: 'center', padding: '20px' }}>Carregando produtos...</td></tr></tbody>;
    }
    if (!produtos || produtos.length === 0) {
      return <tbody><tr><td colSpan="10" style={{ textAlign: 'center', padding: '20px' }}>Nenhum produto encontrado.</td></tr></tbody>;
    }
    return (
      <tbody>
        {produtos.map((produto) => (
          <tr key={produto.id} className={selectedProdutos.has(produto.id) ? 'selected-row' : ''}>
            <td>
              <input 
                type="checkbox"
                checked={selectedProdutos.has(produto.id)}
                onChange={() => onSelectProduto(produto.id)}
              />
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
              <button onClick={() => onEdit(produto)} className="btn-icon btn-edit" title="Editar Produto">
                ✏️
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
