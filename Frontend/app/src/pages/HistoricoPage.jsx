// Frontend/app/src/pages/HistoricoPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import usoIAService from '../services/usoIAService';
import historicoService from '../services/historicoService';
import { useAuth } from '../contexts/AuthContext';
import { showErrorToast, showInfoToast } from '../utils/notifications';
import PaginationControls from '../components/common/PaginationControls';
import { format, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import logger from '../utils/logger';

function HistoricoPage() {
  const { user, isLoading: isAuthLoading } = useAuth();
  const [historico, setHistorico] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [limitPerPage] = useState(10);
  const [totalHistoricoCount, setTotalHistoricoCount] = useState(0);
  const [historicoSistema, setHistoricoSistema] = useState([]);
  const [totalHistoricoSistemaCount, setTotalHistoricoSistemaCount] = useState(0);
  const [filterTipoAcao, setFilterTipoAcao] = useState('');

  const totalPages = Math.ceil(totalHistoricoCount / limitPerPage);

  const fetchHistorico = useCallback(async () => {
    if (isAuthLoading) {
      logger.log("HistoricoPage: Auth está carregando, aguardando...");
      return;
    }

    if (!user) {
      logger.log("HistoricoPage: Usuário não autenticado, não buscando histórico.");
      setHistorico([]);
      setTotalHistoricoCount(0);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const params = {
        skip: currentPage * limitPerPage,
        limit: limitPerPage,
        tipo_acao: filterTipoAcao || undefined,
      };
      
      // FIX: Chamar usoIAService.getMeuHistoricoUsoIA
      const responseData = await usoIAService.getMeuHistoricoUsoIA(params);

      if (responseData && Array.isArray(responseData.items) && typeof responseData.total_items === 'number') {
        setHistorico(responseData.items);
        setTotalHistoricoCount(responseData.total_items);
        showInfoToast(`Histórico carregado: ${responseData.total_items} registros.`);
      } else {
        console.warn('HistoricoPage: Formato de dados inesperado recebido:', responseData);
        setHistorico([]);
        setTotalHistoricoCount(0);
      }
    } catch (err) {
      const errorMsg = (err && err.response && err.response.data && err.response.data.detail) 
                       ? err.response.data.detail 
                       : (err && err.message) 
                       ? err.message 
                       : 'Falha ao buscar histórico de uso de IA.';
      console.error('HistoricoPage: Erro ao buscar histórico:', err);
      setError(errorMsg);
      setHistorico([]);
      setTotalHistoricoCount(0);
      showErrorToast(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [user, isAuthLoading, currentPage, limitPerPage, filterTipoAcao]); // Adicionar dependências

  const fetchHistoricoSistema = useCallback(async () => {
    if (isAuthLoading || !user) return;
    try {
      const params = {
        skip: currentPage * limitPerPage,
        limit: limitPerPage,
      };
      const data = await historicoService.getHistorico(params);
      if (data && Array.isArray(data.items)) {
        setHistoricoSistema(data.items);
        setTotalHistoricoSistemaCount(data.total_items);
      }
    } catch (err) {
      console.error('Erro ao buscar histórico do sistema', err);
    }
  }, [user, isAuthLoading, currentPage, limitPerPage]);


  useEffect(() => {
    fetchHistorico();
    fetchHistoricoSistema();
  }, [fetchHistorico, fetchHistoricoSistema]);

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
  };

  const handleFilterChange = (event) => {
    setFilterTipoAcao(event.target.value);
    setCurrentPage(0); // Resetar para a primeira página ao mudar o filtro
  };

  return (
    <div className="historico-page">
      <div className="card">
        <div className="card-header">
          <h3>Histórico de Uso de IA</h3>
        </div>

        <div className="filters-container" style={{ marginBottom: '1rem' }}>
          <label htmlFor="filter-tipo-acao">Filtrar por Tipo de Ação:</label>
          <select
            id="filter-tipo-acao"
            value={filterTipoAcao}
            onChange={handleFilterChange}
            disabled={loading}
          >
            <option value="">Todos</option>
            <option value="geracao_titulo_produto">Geração Título Produto</option>
            <option value="geracao_descricao_produto">Geração Descrição Produto</option>
            <option value="enriquecimento_web_produto">Enriquecimento Web Produto</option>
            <option value="criacao_produto">Criação de Produto</option>
            {/* Adicione outras opções conforme as TipoAcaoIAEnum do seu backend */}
          </select>
        </div>

        {loading && <p>Carregando histórico...</p>}
        {error && <p style={{ color: 'red' }}>Erro ao carregar histórico: {error}</p>}

        {!loading && historico.length === 0 && !error && (
          <p>Nenhum registro de uso de IA encontrado.</p>
        )}

        {!loading && historico.length > 0 && (
          <div className="table-responsive">
            <table className="historico-table">
              <thead>
                <tr>
                  <th>ID Registro</th>
                  <th>Produto (ID)</th>
                  <th>Ação de IA</th>
                  <th>Resultado</th>
                  <th>Custos</th>
                  <th>Data/Hora</th>
                </tr>
              </thead>
              <tbody>
                {historico.map((registro) => (
                  <tr key={registro.id}>
                    <td>{registro.id}</td>
                    <td>{registro.produto_id ? registro.produto_id : 'N/A'}</td>
                    <td>{registro.tipo_acao.replace(/_/g, ' ')}</td>
                    <td>
                      <div className="resultado-cell" title={registro.resposta_ia}>
                        {registro.resposta_ia ? registro.resposta_ia.substring(0, 100) + '...' : 'N/A'}
                      </div>
                    </td>
                    <td>
                      {registro.tokens_prompt != null && registro.tokens_resposta != null
                        ? registro.tokens_prompt + registro.tokens_resposta
                        : 'N/A'}{' '}
                      tokens
                    </td>
                    <td>
                      {registro.created_at
                        ? format(parseISO(registro.created_at), 'dd/MM/yyyy HH:mm:ss', { locale: ptBR })
                        : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ marginTop: '2rem' }}>
          <h4>Eventos Recentes</h4>
          {!loading && historicoSistema.length === 0 && <p>Nenhum evento encontrado.</p>}
          {!loading && historicoSistema.length > 0 && (
            <div className="table-responsive">
              <table className="historico-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Entidade</th>
                    <th>Ação</th>
                    <th>Entity ID</th>
                    <th>Data/Hora</th>
                  </tr>
                </thead>
                <tbody>
                  {historicoSistema.map((reg) => (
                    <tr key={reg.id}>
                      <td>{reg.id}</td>
                      <td>{reg.entidade}</td>
                      <td>{reg.acao}</td>
                      <td>{reg.entity_id}</td>
                      <td>{reg.created_at ? format(parseISO(reg.created_at), 'dd/MM/yyyy HH:mm:ss', { locale: ptBR }) : 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {totalPages > 0 && !error && (
          <PaginationControls
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={handlePageChange}
            isLoading={loading}
          />
        )}
      </div>
    </div>
  );
}

export default HistoricoPage;
