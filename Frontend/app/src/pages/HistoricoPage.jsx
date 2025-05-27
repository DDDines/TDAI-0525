// Frontend/app/src/pages/HistoricoPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import authService from '../services/authService';
import PaginationControls from '../components/common/PaginationControls';
import { showErrorToast } from '../utils/notifications';

function HistoricoPage() {
  const [historico, setHistorico] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [currentPage, setCurrentPage] = useState(0);
  const [limitPerPage] = useState(15);
  const [totalItems, setTotalItems] = useState(0);

  const totalPages = Math.ceil(totalItems / limitPerPage);

  const fetchHistorico = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        skip: currentPage * limitPerPage,
        limit: limitPerPage,
      };
      const responseData = await authService.getMeuHistoricoUsoIA(params);

      if (responseData && Array.isArray(responseData.items) && typeof responseData.total_items === 'number') {
        setHistorico(responseData.items);
        setTotalItems(responseData.total_items);
      } else {
        // Fallback caso a API ainda retorne uma lista direta ou formato inesperado
        if (Array.isArray(responseData)) {
            setHistorico(responseData);
            // Lógica paliativa simples para totalItems se for lista direta
            setTotalItems(currentPage * limitPerPage + responseData.length + (responseData.length === limitPerPage ? limitPerPage : 0) );
            console.warn('API /uso-ia/me/ retornou uma lista direta ou formato não paginado. A paginação pode ser imprecisa.');
        } else {
            console.warn('Formato de dados inesperado recebido para histórico:', responseData);
            setHistorico([]);
            setTotalItems(0);
            showErrorToast('Não foi possível carregar o histórico de uso ou formato de dados incorreto.');
        }
      }

    } catch (err) {
      const errorMsg = (err && err.message) ? err.message : 'Falha ao buscar histórico de uso.';
      setError(errorMsg);
      showErrorToast(errorMsg);
      setHistorico([]);
      setTotalItems(0);
    } finally {
      setLoading(false);
    }
  }, [currentPage, limitPerPage]);

  useEffect(() => {
    fetchHistorico();
  }, [fetchHistorico]);

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
  };

  if (loading && historico.length === 0) {
    return <div className="card"><p>Carregando histórico de uso...</p></div>;
  }

  if (error) {
    return <div className="card"><p style={{ color: 'red' }}>Erro ao carregar histórico: {error}</p></div>;
  }

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h3>Histórico de Uso da IA</h3>
        </div>

        {historico.length > 0 ? (
          <>
            <table className="hist-table" id="hist-table" style={{width: '100%'}}>
              <thead>
                <tr>
                  <th>Data/Hora</th>
                  <th>Tipo de Geração</th>
                  <th>Produto ID</th>
                  <th>Modelo IA</th>
                  <th>Resultado (início)</th>
                </tr>
              </thead>
              <tbody>
                {historico.map(item => (
                  <tr key={item.id}>
                    <td>{new Date(item.timestamp).toLocaleString()}</td>
                    <td>{item.tipo_geracao}</td>
                    <td>{item.produto_id || 'N/A'}</td>
                    <td>{item.modelo_ia_usado}</td>
                    <td title={item.resultado_gerado}>
                      {item.resultado_gerado ? `${item.resultado_gerado.substring(0, 70)}...` : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {totalPages > 1 && (
              <PaginationControls
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={handlePageChange}
                isLoading={loading}
              />
            )}
          </>
        ) : (
          !loading && <p>Nenhum histórico de uso encontrado.</p>
        )}
      </div>
    </div>
  );
}

export default HistoricoPage;