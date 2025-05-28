// Frontend/app/src/components/produtos/ProductTable.jsx
import React from 'react';

// Função auxiliar para formatar os valores dos Enums (opcional, mas melhora a leitura)
const formatStatusEnumValue = (value) => {
  if (!value) return 'N/D'; // Não definido ou Não disponível
  // Converte para string antes de chamar replace, para o caso de não ser string (ex: se vier null do DB e não for tratado antes)
  return String(value).replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()); // Ex: "CONCLUIDO_SUCESSO" -> "Concluido Sucesso"
};

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
          <th>Marca</th>
          <th>Status Enriq. Web</th>
          <th>Status Títulos IA</th>
          <th>Status Descrição IA</th>
          <th>Descrição Gerada (IA)</th>
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
            <td>{produto.marca || 'N/A'}</td>
            <td>
              <span
                className={`status-dot ${
                  produto.status_enriquecimento_web === 'CONCLUIDO_SUCESSO' ? 'status-completo' :
                  produto.status_enriquecimento_web === 'EM_PROGRESSO' ? 'status-em-progresso' :
                  produto.status_enriquecimento_web === 'FALHOU' ? 'status-falhou' :
                  'status-pendente'
                }`}
              ></span>
              {formatStatusEnumValue(produto.status_enriquecimento_web || 'PENDENTE')} {/* Passa um default para formatStatusEnumValue */}
            </td>
            <td>{formatStatusEnumValue(produto.status_titulo_ia)}</td>
            <td>{formatStatusEnumValue(produto.status_descricao_ia)}</td>
            <td className={produto.descricao_principal_gerada ? 'desc-ok' : 'desc-nao'}>
              {produto.descricao_principal_gerada ? 'Sim' : 'Não'}
            </td>
            <td>{new Date(produto.created_at).toLocaleDateString()}</td>
          </tr>
        )) : (
          <tr><td colSpan="9">Nenhum produto encontrado.</td></tr> // Comentário removido daqui ou movido para fora
        )}
      </tbody>
    </table>
  );
}

export default ProductTable;