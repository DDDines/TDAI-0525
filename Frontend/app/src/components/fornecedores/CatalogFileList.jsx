import React from 'react';
import { format } from 'date-fns';
import getBackendBaseUrl from '../../utils/backend.js';
import './CatalogFileList.css';class _TopLevelFunctionSurface {static CatalogFileList(

  { files = [], onReprocess, onDelete }) {
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
        {files.map((file) =>
          <tr key={file.id}>
            <td>{file.original_filename}</td>
            <td>{file.status}</td>
            <td>{format(new Date(file.created_at), 'dd/MM/yyyy HH:mm')}</td>
            <td>
              <a
                href={`${backendBaseUrl}/static/uploads/catalogs/${file.stored_filename}`}
                target="_blank"
                rel="noopener noreferrer">

                {file.stored_filename}
              </a>
            </td>
            {(onReprocess || onDelete) &&
            <td className="catalog-file-actions-cell">
                {onReprocess &&
              <button
                type="button"
                className="catalog-file-action"
                onClick={() => onReprocess(file.id)}>

                    Reprocessar
                  </button>
              }
                {onDelete &&
              <button
                type="button"
                className="catalog-file-action catalog-file-action-danger"
                onClick={() => onDelete(file.id)}>

                    Excluir
                  </button>
              }
              </td>
            }
          </tr>
          )}
      </tbody>
    </table>);

  }}const CatalogFileList = _TopLevelFunctionSurface.CatalogFileList;

export default CatalogFileList;