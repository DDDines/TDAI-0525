// Frontend/app/src/pages/PlanoPage.jsx
import React, { useState, useEffect } from 'react';
import authService from '../services/authService';
import { showErrorToast, showInfoToast } from '../utils/notifications';
import './PlanoPage.css'; // Criaremos este arquivo para estilos específicos
import LoadingPopup from '../components/common/LoadingPopup.jsx';

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
        const errorMsg = (err && err.message) ? err.message : 'Falha ao carregar dados do usuário e plano.';
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
      <div className="plano-page-container">
        <div className="card">
          <p style={{ color: 'red' }}>Erro ao carregar dados: {error}</p>
        </div>
      </div>
    );
  }

  if (!currentUser || !currentUser.plano) {
    return (
      <div className="plano-page-container">
        <div className="card">
          <h1>Meu Plano</h1>
          <p>Não foi possível carregar as informações do seu plano ou você não possui um plano ativo.</p>
          <p>Entre em contato com o suporte para mais informações.</p>
        </div>
      </div>
    );
  }

  const { plano } = currentUser;
  // Os limites podem ser 0 para "ilimitado" ou um número específico.
  // A forma como "ilimitado" é representado (e.g., 0, -1, 9999999 ou null)
  // vem do backend (models.Plano e schemas.Plano).
  // O plano "Ilimitado" criado no startup usa 9999999.
const formatLimit = (limit) => {
  if (limit === null || limit === undefined || limit >= 999999) { // Considera valores grandes como ilimitado
    return "Ilimitado";
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
    <div className="plano-page-container">
      <div className="card">
        <div className="card-header">
          <h1>Meu Plano</h1>
        </div>
        <div className="plano-details-grid">
          <div className="plano-card current-plan-card">
            <div className="current-plan-header">
              <span className={`plan-badge ${plano.nome?.toLowerCase()}`}>{plano.nome || "N/D"}</span>
              <span className="current-plan-label">Plano Atual</span>
            </div>
            <ul className="plan-features">
              <li><strong>{formatLimit(plano.limite_produtos)}</strong> produtos</li>
              <li><strong>{formatLimit(plano.limite_enriquecimento_web)}</strong> enriquecimentos/mês</li>
              <li><strong>{formatLimit(plano.limite_geracao_ia)}</strong> gerações IA/mês</li>
              <li>Suporte via Email</li>
              {plano.nome?.toLowerCase() !== 'gratuito' && <li>Suporte Prioritário</li>}
            </ul>
            <div className="plan-renewal">
              {/* Data de renovação não está no modelo User/Plano ainda */}
              <strong>Próxima Renovação:</strong> A definir
            </div>
          </div>

          <div className="plano-actions-card">
            <h4>Gerenciar Assinatura</h4>
            <p>Gostaria de mais recursos ou precisa de menos? Explore outras opções.</p>
            <div className="plano-buttons">
              <button className="btn-upgrade" onClick={handleUpgradeClick}>Upgrade de Plano</button>
              <button className="btn-cancel" onClick={handleCancelSubscriptionClick}>Cancelar Assinatura</button>
            </div>
            <p className="billing-history-link" style={{marginTop: '1rem', textAlign: 'center'}}>
                <a href="#" onClick={handleBillingHistoryClick}>Ver Histórico de Cobrança</a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PlanoPage;
