// Frontend/app/src/components/produtos/ProductTable.jsx
import React from 'react';

function ProductTable({ produtos, onRowClick, onSelectRow, selectedIds, onSelectAllRows, isLoading }) {
  if (isLoading && (!produtos || produtos.length === 0)) {
    return <p>Carregando tabela de produtos...</p>;
  }
  return (
    <table id="prod-table" style={{ width: '100%' }}>
      <thead>
        <tr>
          <th className="select">
            <input
              type="checkbox"
              id="select-all-prod"
              onChange={onSelectAllRows}
              checked={produtos.length > 0 && selectedIds.length === produtos.length}
              disabled={produtos.length === 0}
            />
          </th>
          <th>Nome</th>
          <th>SKU</th>
          <th>Status Enriq.</th>
          <th>Descrição Gerada</th>
          <th>Data Criação</th>
        </tr>
      </thead>
      <tbody>
        {produtos.length > 0 ? produtos.map(produto => (
          <tr key={produto.id} onClick={() => onRowClick && onRowClick(produto)} style={{ cursor: 'pointer' }}>
            <td className="select" onClick={(e) => e.stopPropagation()} >
              <input
                type="checkbox"
                className="row-select-prod"
                checked={selectedIds.includes(produto.id)}
                onChange={() => {
                    onSelectRow(produto.id);
                }}
                onClick={(e) => e.stopPropagation()}
              />
            </td>
            <td className="name-cell">{produto.nome_base}</td>
            <td>{produto.dados_brutos?.sku_original || produto.dados_brutos?.codigo_original || 'N/A'}</td>
            <td>
              <span
                className={`status-dot ${
                  produto.status_enriquecimento_web === 'concluido_sucesso' ? 'status-completo' :
                  produto.status_enriquecimento_web === 'em_progresso' ? 'status-em-progresso' :
                  produto.status_enriquecimento_web === 'falhou' ? 'status-falhou' :
                  'status-pendente'
                }`}
              ></span>
              {produto.status_enriquecimento_web?.replace(/_/g, ' ') || 'pendente'}
            </td>
            <td className={produto.descricao_principal_gerada ? 'desc-ok' : 'desc-nao'}>
              {produto.descricao_principal_gerada ? 'Sim' : 'Não'}
            </td>
            <td>{new Date(produto.created_at).toLocaleDateString()}</td>
          </tr>
        )) : (
          <tr><td colSpan="6">Nenhum produto encontrado.</td></tr>
        )}
      </tbody>
    </table>
  );
}

export default ProductTable;