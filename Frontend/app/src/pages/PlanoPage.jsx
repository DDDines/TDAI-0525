/**
 * Module plano page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useEffect, useState } from 'react';
import authService from '../services/authService';
import { showErrorToast, showInfoToast } from '../utils/notifications';
import LoadingPopup from '../components/common/LoadingPopup.jsx';
import './PlanoPage.css';

function PlanoPage() {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchUserData = async () => {
      setLoading(true);
      setError(null);
      try {
        const user = await authService.getCurrentUser();
        setCurrentUser(user);
      } catch (err) {
        const errorMsg = err && err.message ? err.message : 'Falha ao carregar dados do usuario e plano.';
        setError(errorMsg);
        showErrorToast(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    fetchUserData();
  }, []);

  if (loading) {
    return <LoadingPopup isOpen={true} message="Carregando informacoes do plano..." />;
  }

  if (error) {
    return (
      <div className="plano-page-shell">
        <div className="plano-card-box">
          <p className="plano-error">Erro ao carregar dados: {error}</p>
        </div>
      </div>
    );
  }

  if (!currentUser || !currentUser.plano) {
    return (
      <div className="plano-page-shell">
        <div className="plano-card-box">
          <h1 className="plano-page-title">Meu Plano</h1>
          <p>Nao foi possivel carregar as informacoes do seu plano ou voce nao possui um plano ativo.</p>
          <p>Entre em contato com o suporte para mais informacoes.</p>
        </div>
      </div>
    );
  }

  const { plano } = currentUser;

  const formatLimit = (limit) => {
    if (limit === null || limit === undefined || limit >= 999999) {
      return 'Ilimitado';
    }
    return new Intl.NumberFormat('pt-BR').format(limit);
  };

  const hasPrioritySupport = Boolean(plano.nome) && plano.nome.toLowerCase() !== 'gratuito';

  const handleUpgradeClick = () => {
    showInfoToast('Recurso de upgrade ainda nao disponivel.');
  };

  const handleCancelSubscriptionClick = () => {
    showInfoToast('Funcionalidade de cancelamento ainda nao disponivel.');
  };

  const handleBillingHistoryClick = (event) => {
    event.preventDefault();
    showInfoToast('Historico de cobranca ainda nao disponivel.');
  };

  return (
    <div className="plano-page-shell">
      <div className="plano-card-box">
        <h1 className="plano-page-title">Meu Plano</h1>

        <div className="plano-details-grid">
          <section className="plano-info-card">
            <div className="current-plan-header">
              <span className={`plan-badge ${plano.nome?.toLowerCase()}`}>{plano.nome || 'N/D'}</span>
              <span className="current-plan-label">Plano atual</span>
            </div>

            <ul className="plan-features">
              <li>
                <strong>{formatLimit(plano.limite_produtos)}</strong> produtos
              </li>
              <li>
                <strong>{formatLimit(plano.limite_enriquecimento_web)}</strong> enriquecimentos/mes
              </li>
              <li>
                <strong>{formatLimit(plano.limite_geracao_ia)}</strong> geracoes IA/mes
              </li>
              <li>Suporte via email</li>
              {hasPrioritySupport && <li>Suporte prioritario</li>}
            </ul>

            <div className="plan-renewal">
              <strong>Proxima renovacao:</strong> A definir
            </div>
          </section>

          <section className="plano-actions-card">
            <h2>Gerenciar assinatura</h2>
            <p>Gostaria de mais recursos ou precisa de menos? Explore outras opcoes.</p>

            <div className="plano-buttons">
              <button className="btn-upgrade" onClick={handleUpgradeClick}>
                Upgrade de Plano
              </button>
              <button className="btn-cancel" onClick={handleCancelSubscriptionClick}>
                Cancelar Assinatura
              </button>
            </div>

            <p className="billing-history-link">
              <a href="#" onClick={handleBillingHistoryClick}>
                Ver Historico de Cobranca
              </a>
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}

export default PlanoPage;
