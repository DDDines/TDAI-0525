// Frontend/app/src/components/fornecedores/FornecedorTable.jsx
import React from 'react';

function FornecedorTable({ fornecedores, onRowClick, onSelectRow, selectedIds, onSelectAllRows, isLoading }) {
  if (isLoading && (!fornecedores || fornecedores.length === 0)) {
    return <p>Carregando tabela de fornecedores...</p>;
  }
  return (
    <table style={{ width: '100%' }} id="forn-table">
      <thead>
        <tr>
          <th className="select">
            <input 
              type="checkbox" 
              id="select-all-forn" // ID específico
              onChange={onSelectAllRows} 
              checked={fornecedores.length > 0 && selectedIds.length === fornecedores.length} 
              disabled={fornecedores.length === 0} 
            />
          </th>
          <th>Nome</th>
          <th>Site URL</th>
          <th>Data Criação</th>
        </tr>
      </thead>
      <tbody>
        {fornecedores.length > 0 ? fornecedores.map(f => (
          <tr key={f.id} onClick={() => onRowClick(f)} style={{ cursor: 'pointer' }}>
            <td className="select" onClick={(e) => e.stopPropagation()}>
              <input 
                type="checkbox" 
                className="row-select-forn" // Classe específica
                checked={selectedIds.includes(f.id)} 
                onChange={() => onSelectRow(f.id)} 
                onClick={(e) => e.stopPropagation()} 
              />
            </td>
            <td className="name-cell">{f.nome}</td>
            <td>{f.site_url ? <a href={f.site_url} target="_blank" rel="noopener noreferrer">{f.site_url}</a> : 'N/A'}</td>
            <td>{new Date(f.created_at).toLocaleDateString()}</td>
          </tr>
        )) : (
          <tr><td colSpan="4">Nenhum fornecedor encontrado.</td></tr>
        )}
      </tbody>
    </table>
  );
}

export default FornecedorTable;
