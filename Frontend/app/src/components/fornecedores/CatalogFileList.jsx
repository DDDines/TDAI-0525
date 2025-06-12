import React from 'react';
import { format } from 'date-fns';
import getBackendBaseUrl from '../../utils/backend.js';

function CatalogFileList({ files = [], onReprocess, onDelete }) {
  const backendBaseUrl = getBackendBaseUrl();
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
          <th>Processado</th>
          {(onReprocess || onDelete) && <th>Ações</th>}
        </tr>
      </thead>
      <tbody>
        {files.map((f) => (
          <tr key={f.id}>
            <td>{f.original_filename}</td>
            <td>{f.status}</td>
            <td>{format(new Date(f.created_at), 'dd/MM/yyyy HH:mm')}</td>
            <td>
              <a
                href={`${backendBaseUrl}/static/uploads/catalogs/${f.stored_filename}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                {f.stored_filename}
              </a>
            </td>
            {(onReprocess || onDelete) && (
              <td>
                {onReprocess && (
                  <button onClick={() => onReprocess(f.id)}>Reprocessar</button>
                )}
                {onDelete && (
                  <button
                    onClick={() => onDelete(f.id)}
                    style={{ marginLeft: '0.5em' }}
                  >
                    Excluir
                  </button>
                )}
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default CatalogFileList;
