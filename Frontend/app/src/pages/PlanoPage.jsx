/**
 * Module plano page.
 *
 * Implements frontend behavior for pages.
 */

// Frontend/app/src/pages/PlanoPage.jsx
import React, { useState, useEffect } from 'react';
import authService from '../services/authService';
import { showErrorToast, showInfoToast } from '../utils/notifications';
import './PlanoPage.css';
import LoadingPopup from '../components/common/LoadingPopup.jsx';class _TopLevelFunctionSurface {static PlanoPage()

  {
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
          const errorMsg = err && err.message ? err.message : 'Falha ao carregar dados do usuário e plano.';
          setError(errorMsg);
          showErrorToast(errorMsg);
        } finally {
          setLoading(false);
        }
      };

      fetchUserData();
    }, []);

    if (loading) {
      return <LoadingPopup isOpen={true} message="Carregando informações do plano..." />;
    }

    if (error) {
      return (
        <div className="plano-page-shell">
        <div className="plano-card-box">
          <p className="plano-error">Erro ao carregar dados: {error}</p>
        </div>
      </div>);

    }

    if (!currentUser || !currentUser.plano) {
      return (
        <div className="plano-page-shell">
        <div className="plano-card-box">
          <h1 className="plano-page-title">Meu Plano</h1>
          <p>Não foi possível carregar as informações do seu plano ou você não possui um plano ativo.</p>
          <p>Entre em contato com o suporte para mais informações.</p>
        </div>
      </div>);

    }

    const { plano } = currentUser;

    const formatLimit = (limit) => {
      if (limit === null || limit === undefined || limit >= 999999) {
        return 'Ilimitado';
      }
      return new Intl.NumberFormat('pt-BR').format(limit);
    };

    const handleUpgradeClick = () => {
      showInfoToast('Recurso de upgrade ainda não disponível.');
    };

    const handleCancelSubscriptionClick = () => {
      showInfoToast('Funcionalidade de cancelamento ainda não disponível.');
    };

    const handleBillingHistoryClick = (e) => {
      e.preventDefault();
      showInfoToast('Histórico de cobrança ainda não disponível.');
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
                <strong>{formatLimit(plano.limite_enriquecimento_web)}</strong> enriquecimentos/mês
              </li>
              <li>
                <strong>{formatLimit(plano.limite_geracao_ia)}</strong> gerações IA/mês
              </li>
              <li>Suporte via email</li>
              {plano.nome?.toLowerCase() !== 'gratuito' && <li>Suporte prioritário</li>}
            </ul>

            <div className="plan-renewal">
              <strong>Próxima renovação:</strong> A definir
            </div>
          </section>

          <section className="plano-actions-card">
            <h2>Gerenciar assinatura</h2>
            <p>Gostaria de mais recursos ou precisa de menos? Explore outras opções.</p>

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
                Ver Histórico de Cobrança
              </a>
            </p>
          </section>
        </div>
      </div>
    </div>);

  }}export default _TopLevelFunctionSurface.PlanoPage;