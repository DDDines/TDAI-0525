/**
 * Module plano page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  LuArrowUpRight,
  LuBadgeCheck,
  LuBox,
  LuCable,
  LuChevronDown,
  LuHeadphones,
  LuLayers,
  LuSearch,
  LuShieldCheck,
  LuSparkles,
  LuZap,
} from 'react-icons/lu';
import authService from '../services/authService';
import dashboardService from '../services/dashboardService';
import planosService from '../services/planosService';
import { showErrorToast, showInfoToast, showSuccessToast } from '../utils/notifications';
import './PlanoPage.css';

const UNLIMITED_THRESHOLD = 999999;

function normalizeMode(value) {
  return String(value || '').trim().toLowerCase() === 'complete' ? 'complete' : 'basic';
}

function formatModeLabel(mode) {
  return normalizeMode(mode) === 'complete' ? 'Completo' : 'Basico';
}

function isUnlimited(limit) {
  return Number(limit) >= UNLIMITED_THRESHOLD;
}

function formatNumber(value) {
  return new Intl.NumberFormat('pt-BR').format(Number(value || 0));
}

function formatLimit(limit) {
  if (limit === null || limit === undefined || isUnlimited(limit)) {
    return 'Ilimitado';
  }
  return formatNumber(limit);
}

function buildResolvedPlan(currentUser, userDashboard) {
  const directPlan = currentUser?.plano;
  const mode = normalizeMode(
    currentUser?.product_experience_mode ?? userDashboard?.product_experience_mode ?? 'basic'
  );
  const modeFallback = mode === 'complete' ? 'Pro' : 'Gratuito';
  const planName = directPlan
    ? (directPlan?.nome || 'N/D')
    : (userDashboard?.plano_nome || modeFallback);
  const limiteProdutos =
    directPlan?.limite_produtos ??
    currentUser?.limite_produtos ??
    userDashboard?.limites?.produtos ??
    null;
  const limiteEnriquecimentoWeb =
    directPlan?.limite_enriquecimento_web ??
    currentUser?.limite_enriquecimento_web ??
    userDashboard?.limites?.enriquecimento_web ??
    null;
  const limiteGeracaoIa =
    directPlan?.limite_geracao_ia ??
    currentUser?.limite_geracao_ia ??
    userDashboard?.limites?.geracao_ia ??
    null;
  const inferredPrioritySupport =
    String(planName || '').trim().toLowerCase() === 'pro' || mode === 'complete';
  const inferredExternalApi = mode === 'complete';

  if (
    !planName &&
    limiteProdutos == null &&
    limiteEnriquecimentoWeb == null &&
    limiteGeracaoIa == null
  ) {
    return null;
  }

  return {
    nome: planName || 'N/D',
    mode,
    limite_produtos: limiteProdutos,
    limite_enriquecimento_web: limiteEnriquecimentoWeb,
    limite_geracao_ia: limiteGeracaoIa,
    suporte_prioritario: directPlan?.suporte_prioritario ?? inferredPrioritySupport,
    permite_api_externa: directPlan?.permite_api_externa ?? inferredExternalApi,
  };
}

function buildUsageCards(plan, userDashboard) {
  const totalProducts = Number(userDashboard?.totais?.produtos ?? 0);
  const totalFornecedores = Number(userDashboard?.totais?.fornecedores ?? 0);
  const webUsage = Number(userDashboard?.uso_mes_atual?.enriquecimento_web ?? 0);
  const aiUsage = Number(userDashboard?.uso_mes_atual?.geracao_ia ?? 0);

  const createUsageCard = (config) => {
    const unlimited = isUnlimited(config.limit);
    const remaining = unlimited ? null : Math.max(Number(config.limit || 0) - Number(config.used || 0), 0);
    const progress = unlimited || Number(config.limit || 0) <= 0
      ? 0
      : Math.min((Number(config.used || 0) / Number(config.limit || 0)) * 100, 100);

    return {
      ...config,
      unlimited,
      remaining,
      progress,
    };
  };

  return [
    createUsageCard({
      title: 'Catalogo ocupado',
      helper: 'Produtos ja cadastrados no seu espaco atual.',
      icon: <LuBox />,
      tone: 'neutral',
      used: totalProducts,
      usedLabel: `${formatNumber(totalProducts)} cadastrados`,
      remainingLabel: isUnlimited(plan?.limite_produtos)
        ? 'Sem limite de catalogo'
        : `${formatNumber(Math.max(Number(plan?.limite_produtos || 0) - totalProducts, 0))} espacos livres`,
      limit: plan?.limite_produtos,
    }),
    createUsageCard({
      title: 'Busca web no ciclo',
      helper: 'Consultas de enriquecimento usadas neste mes.',
      icon: <LuSearch />,
      tone: 'info',
      used: webUsage,
      usedLabel: `${formatNumber(webUsage)} utilizadas`,
      remainingLabel: isUnlimited(plan?.limite_enriquecimento_web)
        ? 'Sem teto mensal'
        : `${formatNumber(Math.max(Number(plan?.limite_enriquecimento_web || 0) - webUsage, 0))} restantes`,
      limit: plan?.limite_enriquecimento_web,
    }),
    createUsageCard({
      title: 'Geracao IA no ciclo',
      helper: 'Titulos e descricoes gerados neste mes.',
      icon: <LuZap />,
      tone: 'warn',
      used: aiUsage,
      usedLabel: `${formatNumber(aiUsage)} utilizadas`,
      remainingLabel: isUnlimited(plan?.limite_geracao_ia)
        ? 'Sem teto mensal'
        : `${formatNumber(Math.max(Number(plan?.limite_geracao_ia || 0) - aiUsage, 0))} restantes`,
      limit: plan?.limite_geracao_ia,
    }),
    {
      title: 'Base operacional',
      helper: 'Fornecedores conectados a esta conta.',
      icon: <LuLayers />,
      tone: 'success',
      used: totalFornecedores,
      usedLabel: `${formatNumber(totalFornecedores)} fornecedores`,
      remainingLabel: 'Prontos para alimentar o catalogo',
      limit: null,
      unlimited: true,
      remaining: null,
      progress: 0,
    },
  ];
}

function buildCoverageItems(plan) {
  const modeLabel = formatModeLabel(plan?.mode);
  const aiEnabled = Number(plan?.limite_geracao_ia ?? 0) > 0 || normalizeMode(plan?.mode) === 'complete';
  const webEnabled = Number(plan?.limite_enriquecimento_web ?? 0) > 0;

  return [
    {
      title: 'Modo do produto',
      value: modeLabel,
      helper:
        modeLabel === 'Completo'
          ? 'Fluxo completo com recursos de IA liberados.'
          : 'Fluxo enxuto com geracao basica como padrao.',
      icon: <LuSparkles />,
      tone: modeLabel === 'Completo' ? 'success' : 'neutral',
    },
    {
      title: 'Enriquecimento web',
      value: webEnabled ? 'Ativo' : 'Nao incluso',
      helper: webEnabled
        ? 'Pode buscar dados externos e revisar resultados.'
        : 'Disponivel apenas para planos com cota de busca.',
      icon: <LuSearch />,
      tone: webEnabled ? 'info' : 'muted',
    },
    {
      title: 'Geracao com IA',
      value: aiEnabled ? 'Disponivel' : 'Indisponivel',
      helper: aiEnabled
        ? 'Pode gerar titulos, descricoes e sugestoes assistidas.'
        : 'A tela continua funcional apenas com o modo basico.',
      icon: <LuZap />,
      tone: aiEnabled ? 'warn' : 'muted',
    },
    {
      title: 'Credenciais externas',
      value: plan?.permite_api_externa ? 'Permitidas' : 'Bloqueadas',
      helper: plan?.permite_api_externa
        ? 'Aceita chaves do cliente para Google, OpenAI e Gemini.'
        : 'Usa apenas as configuracoes padrao da plataforma.',
      icon: <LuCable />,
      tone: plan?.permite_api_externa ? 'success' : 'muted',
    },
    {
      title: 'Suporte',
      value: plan?.suporte_prioritario ? 'Prioritario' : 'Padrao',
      helper: plan?.suporte_prioritario
        ? 'Fila de suporte com atendimento prioritario.'
        : 'Atendimento padrao pelos canais ativos.',
      icon: <LuHeadphones />,
      tone: plan?.suporte_prioritario ? 'success' : 'neutral',
    },
    {
      title: 'Renovacao de limites',
      value: 'Mensal',
      helper: 'As cotas de uso sao acompanhadas por ciclo mensal.',
      icon: <LuShieldCheck />,
      tone: 'neutral',
    },
  ];
}

function getPlanSummary(plan, userDashboard) {
  const planName = String(plan?.nome || 'N/D').trim();
  const modeLabel = formatModeLabel(plan?.mode);
  const produtosLivres = isUnlimited(plan?.limite_produtos)
    ? 'catalogo ilimitado'
    : `${formatNumber(Math.max(Number(plan?.limite_produtos || 0) - Number(userDashboard?.totais?.produtos ?? 0), 0))} espacos livres`;
  const webDisponivel = Number(plan?.limite_enriquecimento_web ?? 0) > 0;
  const aiDisponivel = Number(plan?.limite_geracao_ia ?? 0) > 0 || normalizeMode(plan?.mode) === 'complete';

  return [
    `Plano ${planName}`,
    `Modo ${modeLabel}`,
    produtosLivres,
    webDisponivel ? 'busca web ativa' : 'sem busca web incluida',
    aiDisponivel ? 'geracao IA disponivel' : 'geracao IA indisponivel',
  ].join('. ');
}

function PlanUsageCard({ item }) {
  return (
    <article className={`plano-usage-card tone-${item.tone || 'neutral'}`}>
      <div className="plano-usage-head">
        <span className="plano-usage-icon">{item.icon}</span>
        <span className="plano-usage-limit">{formatLimit(item.limit)}</span>
      </div>
      <h3>{item.title}</h3>
      <p>{item.helper}</p>
      <div className="plano-usage-metric">{item.usedLabel}</div>
      <div className="plano-usage-remaining">{item.remainingLabel}</div>
      {item.unlimited ? (
        <div className="plano-usage-track plano-usage-track-static">
          <div className="plano-usage-fill plano-usage-fill-static" />
        </div>
      ) : (
        <div className="plano-usage-track">
          <div className="plano-usage-fill" style={{ width: `${item.progress}%` }} />
        </div>
      )}
    </article>
  );
}

function CoverageItem({ item }) {
  return (
    <article className={`plano-coverage-item tone-${item.tone || 'neutral'}`}>
      <span className="plano-coverage-icon">{item.icon}</span>
      <div className="plano-coverage-copy">
        <strong>{item.title}</strong>
        <span className="plano-coverage-value">{item.value}</span>
        <p>{item.helper}</p>
      </div>
    </article>
  );
}

function PlanoPage() {
  const [currentUser, setCurrentUser] = useState(null);
  const [userDashboard, setUserDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [planos, setPlanos] = useState([]);
  const [upgradingPlanoId, setUpgradingPlanoId] = useState(null);
  const [showPlanChooser, setShowPlanChooser] = useState(false);
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const fetchUserData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [user, dashboardPayload, planosPayload] = await Promise.allSettled([
          authService.getCurrentUser(),
          dashboardService.getMyDashboard(),
          planosService.listarPlanos(),
        ]);
        if (user.status !== 'fulfilled') {
          throw user.reason;
        }
        setCurrentUser(user.value);
        setUserDashboard(dashboardPayload.status === 'fulfilled' ? dashboardPayload.value : null);
        setPlanos(planosPayload.status === 'fulfilled' && Array.isArray(planosPayload.value) ? planosPayload.value : []);
      } catch (err) {
        const errorMsg = err && err.message ? err.message : 'Falha ao carregar dados do usuario e plano.';
        setError(errorMsg);
        showErrorToast(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    void fetchUserData();
  }, []);

  useEffect(() => {
    const checkout = searchParams.get('checkout');
    if (checkout === 'success') {
      showSuccessToast('Pagamento confirmado! Seu plano será atualizado em instantes.');
    } else if (checkout === 'cancel') {
      showInfoToast('Checkout cancelado.');
    }
  }, [searchParams]);

  const handleMudarPlano = async (plano) => {
    if (upgradingPlanoId) return;
    setUpgradingPlanoId(plano.id);
    try {
      if (plano.preco_mensal > 0) {
        // Plano pago → redireciona para Stripe Checkout
        const { checkout_url } = await planosService.criarCheckout(plano.id);
        window.location.href = checkout_url;
        return;
      }
      // Plano gratuito → muda diretamente
      const novoPlano = await planosService.mudarPlano(plano.id);
      setCurrentUser((prev) => prev ? { ...prev, plano: novoPlano, plano_id: novoPlano.id } : prev);
      showSuccessToast(`Plano alterado para ${novoPlano.nome} com sucesso.`);
      setShowPlanChooser(false);
    } catch (err) {
      showErrorToast(err?.response?.data?.detail || err?.message || 'Falha ao alterar plano.');
    } finally {
      setUpgradingPlanoId(null);
    }
  };

  const handleGerenciarAssinatura = async () => {
    try {
      const { portal_url } = await planosService.abrirPortal();
      window.location.href = portal_url;
    } catch (err) {
      showErrorToast(err?.response?.data?.detail || err?.message || 'Não foi possível abrir o portal.');
    }
  };

  const resolvedPlan = useMemo(
    () => buildResolvedPlan(currentUser, userDashboard),
    [currentUser, userDashboard]
  );
  const usageCards = useMemo(
    () => buildUsageCards(resolvedPlan, userDashboard),
    [resolvedPlan, userDashboard]
  );
  const coverageItems = useMemo(
    () => buildCoverageItems(resolvedPlan),
    [resolvedPlan]
  );

  if (loading) {
    return (
      <div className="plano-page-shell">
        <section className="plano-inline-card plano-loading-card">
          <span className="plano-inline-eyebrow">Carregando plano</span>
          <h2>Preparando sua visao de capacidade</h2>
          <p>Estamos consolidando limites, uso atual e cobertura ativa da sua conta.</p>
        </section>
      </div>
    );
  }

  if (error) {
    return (
      <div className="plano-page-shell">
        <section className="plano-inline-card plano-error-card">
          <span className="plano-inline-eyebrow">Falha ao carregar</span>
          <h2>Nao foi possivel montar a tela do seu plano</h2>
          <p className="plano-error">Erro ao carregar dados: {error}</p>
        </section>
      </div>
    );
  }

  if (!currentUser || !resolvedPlan) {
    return (
      <div className="plano-page-shell">
        <section className="plano-inline-card plano-empty-card">
          <span className="plano-inline-eyebrow">Plano indisponivel</span>
          <h2>Nao encontramos um plano ativo para esta conta</h2>
          <p>
            Revise o cadastro do usuario ou entre em contato com o suporte para liberar
            limites e recursos desta area.
          </p>
        </section>
      </div>
    );
  }

  const modeLabel = formatModeLabel(resolvedPlan.mode);
  const heroSummary = getPlanSummary(resolvedPlan, userDashboard);
  const totalProducts = Number(userDashboard?.totais?.produtos ?? 0);
  const totalFornecedores = Number(userDashboard?.totais?.fornecedores ?? 0);
  const allowsAi = Number(resolvedPlan?.limite_geracao_ia ?? 0) > 0 || normalizeMode(resolvedPlan.mode) === 'complete';

  const handleSupportClick = () => {
    showInfoToast('Suporte comercial ainda nao foi conectado nesta tela.');
  };

  return (
    <div className="plano-page-shell">
      <section className="plano-hero-card">
        <div className="plano-hero-copy">
          <span className="plano-inline-eyebrow">Visao do plano</span>
          <div className="plano-hero-title-row">
            <h1>{resolvedPlan.nome || 'N/D'}</h1>
            <span className={`plan-badge ${String(resolvedPlan.nome || '').trim().toLowerCase() || 'nd'}`}>
              {resolvedPlan.nome || 'N/D'}
            </span>
          </div>
          <p className="plano-hero-summary">{heroSummary}</p>
          <div className="plano-hero-pill-row">
            <span className="plano-hero-pill">
              <LuBadgeCheck />
              {modeLabel}
            </span>
            <span className="plano-hero-pill">
              <LuShieldCheck />
              Limites renovam mensalmente
            </span>
            <span className="plano-hero-pill">
              <LuCable />
              {resolvedPlan.permite_api_externa ? 'Credenciais do cliente liberadas' : 'Credenciais externas bloqueadas'}
            </span>
          </div>
        </div>

        <aside className="plano-hero-side">
          <div className="plano-hero-side-grid">
            <article className="plano-side-stat">
              <span className="plano-side-stat-label">Produtos ativos</span>
              <strong className="plano-side-stat-value">{formatNumber(totalProducts)}</strong>
            </article>
            <article className="plano-side-stat">
              <span className="plano-side-stat-label">Fornecedores</span>
              <strong className="plano-side-stat-value">{formatNumber(totalFornecedores)}</strong>
            </article>
            <article className="plano-side-stat">
              <span className="plano-side-stat-label">IA no plano</span>
              <strong className="plano-side-stat-value">{allowsAi ? 'Ativa' : 'Basica'}</strong>
            </article>
            <article className="plano-side-stat">
              <span className="plano-side-stat-label">Suporte</span>
              <strong className="plano-side-stat-value">
                {resolvedPlan.suporte_prioritario ? 'Prioritario' : 'Padrao'}
              </strong>
            </article>
          </div>
        </aside>
      </section>

      <section className="plano-section-card">
        <div className="plano-section-head">
          <div>
            <h2>Capacidade do plano</h2>
            <p>Leitura direta do que ja foi usado e do que ainda resta no ciclo atual.</p>
          </div>
        </div>
        <div className="plano-usage-grid">
          {usageCards.map((item) => (
            <PlanUsageCard key={item.title} item={item} />
          ))}
        </div>
      </section>

      <div className="plano-content-grid">
        <section className="plano-section-card">
          <div className="plano-section-head">
            <div>
              <h2>Cobertura incluida</h2>
              <p>O que este plano libera hoje na operacao do catalogo.</p>
            </div>
          </div>
          <div className="plano-coverage-grid">
            {coverageItems.map((item) => (
              <CoverageItem key={item.title} item={item} />
            ))}
          </div>
        </section>

        <section className="plano-section-card plano-actions-card">
          <div className="plano-section-head">
            <div>
              <h2>Acoes do plano</h2>
              <p>Atalhos uteis para revisar consumo, credenciais e proxima evolucao da conta.</p>
            </div>
          </div>

          <div className="plano-action-list">
            <a className="plano-action-link" href="/historico">
              <div>
                <strong>Ver historico de uso</strong>
                <span>Audite consumo de IA, eventos e operacoes recentes.</span>
              </div>
              <LuArrowUpRight />
            </a>

            <a className="plano-action-link" href="/configuracoes">
              <div>
                <strong>Configurar credenciais</strong>
                <span>Gerencie chaves pessoais e credenciais do cliente.</span>
              </div>
              <LuArrowUpRight />
            </a>

            <button type="button" className="plano-action-button" onClick={() => setShowPlanChooser((v) => !v)}>
              <div>
                <strong>Mudar de plano</strong>
                <span>Visualize e selecione um plano diferente para esta conta.</span>
              </div>
              {showPlanChooser ? <LuChevronDown style={{ transform: 'rotate(180deg)' }} /> : <LuArrowUpRight />}
            </button>

            {currentUser?.plano?.preco_mensal > 0 && (
              <button type="button" className="plano-action-button" onClick={handleGerenciarAssinatura}>
                <div>
                  <strong>Gerenciar assinatura</strong>
                  <span>Atualize forma de pagamento, faturas e cancelamento via Stripe.</span>
                </div>
                <LuArrowUpRight />
              </button>
            )}

            <button type="button" className="plano-action-button" onClick={handleSupportClick}>
              <div>
                <strong>Falar com suporte</strong>
                <span>Abra um canal para duvidas sobre plano, limites e cobranca.</span>
              </div>
              <LuArrowUpRight />
            </button>
          </div>
        </section>
      </div>

      {showPlanChooser && planos.length > 0 && (
        <section className="plano-section-card plano-chooser-card">
          <div className="plano-section-head">
            <div>
              <h2>Selecionar plano</h2>
              <p>Escolha o plano que melhor se adapta ao seu uso atual.</p>
            </div>
          </div>
          <div className="plano-chooser-grid">
            {planos.map((plano) => {
              const isCurrent = currentUser?.plano?.id === plano.id || currentUser?.plano_id === plano.id;
              const isUpgrading = upgradingPlanoId === plano.id;
              return (
                <article key={plano.id} className={`plano-chooser-plan${isCurrent ? ' is-current' : ''}`}>
                  <div className="plano-chooser-plan-header">
                    <span className="plano-chooser-plan-name">{plano.nome}</span>
                    {isCurrent && <span className="plano-chooser-plan-badge">Atual</span>}
                    <span className="plano-chooser-plan-price">
                      {plano.preco_mensal > 0
                        ? `R$ ${plano.preco_mensal.toFixed(2).replace('.', ',')}/mês`
                        : 'Grátis'}
                    </span>
                  </div>
                  <ul className="plano-chooser-plan-limits">
                    <li><span>Produtos</span><strong>{formatLimit(plano.limite_produtos)}</strong></li>
                    <li><span>Enriquecimento web/mês</span><strong>{formatLimit(plano.limite_enriquecimento_web)}</strong></li>
                    <li><span>Gerações IA/mês</span><strong>{formatLimit(plano.limite_geracao_ia)}</strong></li>
                    {plano.permite_api_externa && <li><span>API externa</span><strong>Sim</strong></li>}
                    {plano.suporte_prioritario && <li><span>Suporte prioritário</span><strong>Sim</strong></li>}
                  </ul>
                  {!isCurrent && (
                    <button
                      type="button"
                      className={`plano-chooser-select-btn${plano.preco_mensal > (currentUser?.plano?.preco_mensal ?? 0) ? ' is-upgrade' : ''}`}
                      disabled={!!upgradingPlanoId}
                      onClick={() => handleMudarPlano(plano)}
                    >
                      {isUpgrading
                        ? 'Alterando...'
                        : plano.preco_mensal > (currentUser?.plano?.preco_mensal ?? 0)
                          ? 'Fazer upgrade'
                          : 'Mudar para este plano'}
                    </button>
                  )}
                </article>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}

export default PlanoPage;
