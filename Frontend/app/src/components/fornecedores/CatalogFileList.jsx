import React from 'react';
import { format } from 'date-fns';

function CatalogFileList({ files = [], onReprocess }) {
  if (!files || files.length === 0) {
    return <p>Nenhum arquivo encontrado.</p>;
  }

  return (
    <table className="catalog-file-table">
      <thead>
        <tr>
          <th>Arquivo</th>
          <th>Status</th>
          <th>Enviado em</th>
          {onReprocess && <th>Ações</th>}
        </tr>
      </thead>
      <tbody>
        {files.map((f) => (
          <tr key={f.id}>
            <td>{f.original_filename}</td>
            <td>{f.status}</td>
            <td>{format(new Date(f.created_at), 'dd/MM/yyyy HH:mm')}</td>
            {onReprocess && (
              <td>
                <button onClick={() => onReprocess(f.id)}>Reprocessar</button>
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default CatalogFileList;
