/**
 * Dashboard page.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LuArrowRight,
  LuBadgeAlert,
  LuBell,
  LuBox,
  LuCheckCheck,
  LuClock3,
  LuLayers,
  LuListTodo,
  LuSearch,
  LuSparkles,
  LuWorkflow,
  LuZap,
} from 'react-icons/lu';
import adminService from '../services/adminService';
import authService from '../services/authService';
import dashboardService from '../services/dashboardService';
import LoadingOverlay from '../components/common/LoadingOverlay.jsx';
import { showErrorToast } from '../utils/notifications';
import './DashboardPage.css';

const STATUS_META = {
  NAO_INICIADO: { label: 'Nao iniciado', tone: 'muted' },
  PENDENTE: { label: 'Pendente', tone: 'warn' },
  EM_PROGRESSO: { label: 'Em progresso', tone: 'info' },
  CONCLUIDO: { label: 'Concluido', tone: 'success' },
  CONCLUIDO_SUCESSO: { label: 'Concluido', tone: 'success' },
  CONCLUIDO_COM_DADOS_PARCIAIS: { label: 'Concluido com dados parciais', tone: 'warn' },
  FALHA: { label: 'Falha', tone: 'danger' },
  FALHOU: { label: 'Falha', tone: 'danger' },
  FALHA_API_EXTERNA: { label: 'Falha de API externa', tone: 'danger' },
  FALHA_CONFIGURACAO_API_EXTERNA: { label: 'Falha de configuracao', tone: 'danger' },
  NENHUMA_FONTE_ENCONTRADA: { label: 'Nenhuma fonte encontrada', tone: 'muted' },
  NAO_APLICAVEL: { label: 'Nao aplicavel', tone: 'muted' },
};

const ENTITY_LABELS = {
  produto: 'Produto',
  produtos: 'Produtos',
  fornecedor: 'Fornecedor',
  fornecedores: 'Fornecedores',
  usuario: 'Usuario',
  user: 'Usuario',
  tipo: 'Tipo de produto',
  product_type: 'Tipo de produto',
  tipo_de_produto: 'Tipo de produto',
};

const ACTION_LABELS = {
  CRIACAO: 'criado',
  CRIADO: 'criado',
  CREATE: 'criado',
  CREATED: 'criado',
  ATUALIZACAO: 'atualizado',
  ATUALIZADO: 'atualizado',
  UPDATE: 'atualizado',
  UPDATED: 'atualizado',
  DELECAO: 'removido',
  EXCLUSAO: 'removido',
  DELETE: 'removido',
  DELETED: 'removido',
  LOGIN: 'login realizado',
  ENRIQUECIMENTO: 'enriquecido',
  GERACAO_IA: 'processado com IA',
};

function normalizeStatusKey(value) {
  return String(value ?? '')
    .trim()
    .split('.')
    .pop()
    .toUpperCase();
}

function getStatusMeta(value) {
  return STATUS_META[normalizeStatusKey(value)] || { label: 'Desconhecido', tone: 'muted' };
}

function getTotalByStatus(items, ...keys) {
  const normalizedItems = Array.isArray(items) ? items : [];
  return normalizedItems.reduce((total, item) => (
    keys.includes(normalizeStatusKey(item?.status)) ? total + Number(item?.total || 0) : total
  ), 0);
}

function formatModeLabel(mode) {
  return String(mode || '').trim().toLowerCase() === 'complete' ? 'Completo' : 'Basico';
}

function formatActivityTimestamp(value) {
  if (!value) {
    return '';
  }
  try {
    return new Date(value).toLocaleString('pt-BR');
  } catch {
    return '';
  }
}

function formatEntityLabel(value) {
  const normalized = String(value || '').trim().toLowerCase();
  return ENTITY_LABELS[normalized] || 'Atividade';
}

function formatActionLabel(value) {
  const normalized = String(value || '').trim().toUpperCase();
  return ACTION_LABELS[normalized] || String(value || '').trim().toLowerCase() || 'registrado';
}

function pluralize(value, singular, plural) {
  return Number(value || 0) === 1 ? singular : plural;
}

function buildAdminHighlights(statusCounts) {
  const items = Array.isArray(statusCounts) ? statusCounts : [];
  const getTotal = (...keys) =>
    items.reduce((total, item) => (
      keys.includes(normalizeStatusKey(item?.status)) ? total + Number(item?.total || 0) : total
    ), 0);

  return [
    {
      title: 'Falhas para revisar',
      value: getTotal('FALHA', 'FALHOU', 'FALHA_API_EXTERNA', 'FALHA_CONFIGURACAO_API_EXTERNA'),
      helper: 'Produtos com erro no fluxo',
      tone: 'danger',
      icon: <LuBadgeAlert />,
      route: '/enriquecimento',
      actionLabel: 'Revisar',
    },
    {
      title: 'Em processamento',
      value: getTotal('EM_PROGRESSO', 'PENDENTE'),
      helper: 'Itens aguardando conclusao',
      tone: 'info',
      icon: <LuWorkflow />,
      route: '/produtos',
      actionLabel: 'Abrir fila',
    },
    {
      title: 'Concluidos',
      value: getTotal('CONCLUIDO', 'CONCLUIDO_SUCESSO'),
      helper: 'Produtos finalizados',
      tone: 'success',
      icon: <LuCheckCheck />,
      route: '/produtos',
      actionLabel: 'Ver itens',
    },
    {
      title: 'Dados incompletos',
      value: getTotal('CONCLUIDO_COM_DADOS_PARCIAIS', 'NENHUMA_FONTE_ENCONTRADA'),
      helper: 'Casos que ainda pedem ajuste',
      tone: 'warn',
      icon: <LuListTodo />,
      route: '/enriquecimento',
      actionLabel: 'Completar',
    },
  ];
}

function buildUserHighlights(userDashboard) {
  const productLimit = Number(userDashboard?.limites?.produtos ?? 0);
  const webLimit = Number(userDashboard?.limites?.enriquecimento_web ?? 0);
  const aiLimit = Number(userDashboard?.limites?.geracao_ia ?? 0);
  const webUsage = Number(userDashboard?.uso_mes_atual?.enriquecimento_web ?? 0);
  const aiUsage = Number(userDashboard?.uso_mes_atual?.geracao_ia ?? 0);

  return [
    {
      title: 'Espaco de catalogo',
      value: Math.max(productLimit - Number(userDashboard?.totais?.produtos ?? 0), 0),
      helper: 'Produtos ainda disponiveis no plano',
      tone: 'info',
      icon: <LuBox />,
      route: '/produtos',
      actionLabel: 'Ver catalogo',
    },
    {
      title: 'Busca web restante',
      value: Math.max(webLimit - webUsage, 0),
      helper: 'Enriquecimentos restantes neste mes',
      tone: webUsage >= webLimit && webLimit > 0 ? 'danger' : 'success',
      icon: <LuSearch />,
      route: '/enriquecimento',
      actionLabel: 'Usar agora',
    },
    {
      title: 'IA restante',
      value: Math.max(aiLimit - aiUsage, 0),
      helper: 'Geracoes disponiveis neste mes',
      tone: aiUsage >= aiLimit && aiLimit > 0 ? 'warn' : 'success',
      icon: <LuZap />,
      route: '/plano',
      actionLabel: 'Ver plano',
    },
  ];
}

function buildAdminSummaryLine(statusCounts) {
  const failures = getTotalByStatus(
    statusCounts,
    'FALHA',
    'FALHOU',
    'FALHA_API_EXTERNA',
    'FALHA_CONFIGURACAO_API_EXTERNA'
  );
  const partial = getTotalByStatus(statusCounts, 'CONCLUIDO_COM_DADOS_PARCIAIS', 'NENHUMA_FONTE_ENCONTRADA');
  const pending = getTotalByStatus(statusCounts, 'EM_PROGRESSO', 'PENDENTE');
  const notStarted = getTotalByStatus(statusCounts, 'NAO_INICIADO');

  return [
    `${failures} ${pluralize(failures, 'falha pede', 'falhas pedem')} revisao imediata`,
    `${partial} ${pluralize(partial, 'produto esta', 'produtos estao')} com dados incompletos`,
    `${pending} ${pluralize(pending, 'item segue', 'itens seguem')} em andamento`,
    `${notStarted} ${pluralize(notStarted, 'produto ainda nao foi iniciado', 'produtos ainda nao foram iniciados')}`,
  ].join('. ');
}

function buildUserSummaryLine(userDashboard, currentUser) {
  const planName = userDashboard?.plano_nome || currentUser?.plano?.nome || 'Gratuito';
  const productLimit = Number(userDashboard?.limites?.produtos ?? 0);
  const totalProducts = Number(userDashboard?.totais?.produtos ?? 0);
  const webLimit = Number(userDashboard?.limites?.enriquecimento_web ?? 0);
  const webUsage = Number(userDashboard?.uso_mes_atual?.enriquecimento_web ?? 0);
  const aiLimit = Number(userDashboard?.limites?.geracao_ia ?? 0);
  const aiUsage = Number(userDashboard?.uso_mes_atual?.geracao_ia ?? 0);

  return [
    `Plano ${planName}`,
    `${Math.max(productLimit - totalProducts, 0)} vagas livres para produtos`,
    `${Math.max(webLimit - webUsage, 0)} buscas web restantes`,
    `${Math.max(aiLimit - aiUsage, 0)} geracoes IA restantes`,
  ].join('. ');
}

function buildAdminHeroStats(adminStats) {
  if (!adminStats) {
    return [];
  }
  return [
    { label: 'Usuarios', value: adminStats.total_usuarios || 0 },
    { label: 'Fornecedores', value: adminStats.total_fornecedores || 0 },
    { label: 'Enriquecimentos no mes', value: adminStats.total_enriquecimentos_mes || 0 },
  ];
}

function MetricCard({ value, label, helper, icon, barColor, tone = 'neutral' }) {
  return (
    <article
      className={`pro-card-metric dashboard-metric-card tone-${tone}`}
      style={{ '--dashboard-metric-color': barColor }}
    >
      <div className="pro-metric-bar-bg">
        <div className="pro-metric-bar" style={{ width: '100%', background: 'var(--dashboard-metric-color)' }} />
      </div>
      <div className="pro-metric-icon">{icon}</div>
      <div className="pro-metric-value">{value}</div>
      <div className="pro-metric-label">{label}</div>
      {helper ? <div className="pro-metric-comp">{helper}</div> : null}
    </article>
  );
}

function HighlightsPanel({ title, helper, items, emptyMessage, onNavigate, className = '' }) {
  return (
    <section className={`dashboard-section-card dashboard-highlights-card ${className}`.trim()}>
      <div className="dashboard-section-head">
        <div>
          <h3>{title}</h3>
          {helper ? <p>{helper}</p> : null}
        </div>
      </div>
      {Array.isArray(items) && items.length > 0 ? (
        <div className="dashboard-highlight-grid">
          {items.map((item) => (
            <article key={item.title} className={`dashboard-highlight-item tone-${item.tone || 'muted'}`}>
              <span className="dashboard-highlight-icon">{item.icon}</span>
              <strong className="dashboard-highlight-value">{item.value}</strong>
              <span className="dashboard-highlight-title">{item.title}</span>
              {item.helper ? <span className="dashboard-highlight-helper">{item.helper}</span> : null}
              {item.route ? (
                <button
                  type="button"
                  className="dashboard-highlight-action"
                  onClick={() => onNavigate?.(item.route)}
                >
                  {item.actionLabel || 'Abrir'}
                  <LuArrowRight />
                </button>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <p className="dashboard-empty-note">{emptyMessage}</p>
      )}
    </section>
  );
}

function CommandCenter({ kicker, summary, pills, sideStats, badgeLabel }) {
  const hasSideContent = Boolean(badgeLabel) || (Array.isArray(sideStats) && sideStats.length > 0);
  return (
    <section className={`dashboard-command-card ${hasSideContent ? '' : 'without-side'}`.trim()}>
      <div className="dashboard-command-copy">
        <span className="dashboard-kicker">{kicker}</span>
        <p className="dashboard-command-summary">{summary}</p>
        <div className="dashboard-command-pill-row">
          {(pills || []).map((item) => (
            <article
              key={`${item.title}-${item.value}`}
              className={`dashboard-command-pill tone-${item.tone || 'muted'}`}
            >
              <span className="dashboard-command-pill-icon">{item.icon}</span>
              <div className="dashboard-command-pill-copy">
                <strong>{item.value}</strong>
                <span>{item.title}</span>
              </div>
            </article>
          ))}
        </div>
      </div>

      {hasSideContent ? (
        <aside className="dashboard-command-side">
          {badgeLabel ? <span className="dashboard-command-badge">{badgeLabel}</span> : null}
          <div className="dashboard-command-side-grid">
            {(sideStats || []).map((item) => (
              <article key={item.label} className="dashboard-side-stat">
                <span className="dashboard-side-stat-label">{item.label}</span>
                <strong className="dashboard-side-stat-value">{item.value}</strong>
              </article>
            ))}
          </div>
        </aside>
      ) : null}
    </section>
  );
}

function StatusPanel({ title, helper, items, emptyMessage, className = '' }) {
  const normalizedItems = Array.isArray(items) ? items : [];
  const maxValue = Math.max(1, ...(normalizedItems.map((item) => Number(item.total || 0)) || [1]));

  return (
    <section className={`pro-bar-chart dashboard-section-card ${className}`.trim()}>
      <div className="dashboard-section-head">
        <div>
          <h3>{title}</h3>
          {helper ? <p>{helper}</p> : null}
        </div>
      </div>
      {normalizedItems.length > 0 ? (
        normalizedItems.map((item) => {
          const meta = getStatusMeta(item.status);
          const total = Number(item.total || 0);
          const width = `${Math.max((total / maxValue) * 100, total > 0 ? 8 : 0)}%`;
          return (
            <div className="pro-bar-row" key={`${item.status}-${total}`}>
              <span className="pro-bar-label">{meta.label}</span>
              <div className="pro-bar-bg">
                <div className={`pro-bar dashboard-status-bar tone-${meta.tone}`} style={{ width }} />
              </div>
              <span className="pro-bar-value">{total}</span>
            </div>
          );
        })
      ) : (
        <p className="dashboard-empty-note">{emptyMessage}</p>
      )}
    </section>
  );
}

function ActivityFeed({ title, helper, items, emptyMessage, className = '' }) {
  return (
    <section className={`pro-feed-card dashboard-section-card ${className}`.trim()}>
      <div className="dashboard-section-head">
        <div>
          <h3>{title}</h3>
          {helper ? <p>{helper}</p> : null}
        </div>
      </div>
      {Array.isArray(items) && items.length > 0 ? (
        <ul className="pro-feed-list">
          {items.map((activity) => {
            const entity = formatEntityLabel(activity.entidade || activity.tipo || activity.type);
            const action = formatActionLabel(activity.tipo_acao || activity.acao || activity.status);
            return (
              <li
                className="pro-feed-item"
                key={`${activity.id || entity}-${activity.created_at || action}`}
              >
                <span className="pro-feed-ico">
                  <LuClock3 />
                </span>
                <div className="dashboard-feed-copy">
                  <span className="pro-feed-msg">
                    <strong>{entity}</strong>
                    {` ${action}`}
                  </span>
                  <span className="pro-feed-date">
                    {formatActivityTimestamp(activity.created_at)}
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="dashboard-empty-note">{emptyMessage}</p>
      )}
    </section>
  );
}

function PlanUsagePanel({ userDashboard, className = '' }) {
  const items = [
    {
      label: 'Produtos',
      used: Number(userDashboard?.totais?.produtos ?? 0),
      limit: Number(userDashboard?.limites?.produtos ?? 0),
      icon: <LuBox />,
    },
    {
      label: 'Enriquecimento web',
      used: Number(userDashboard?.uso_mes_atual?.enriquecimento_web ?? 0),
      limit: Number(userDashboard?.limites?.enriquecimento_web ?? 0),
      icon: <LuSearch />,
    },
    {
      label: 'Geracao IA',
      used: Number(userDashboard?.uso_mes_atual?.geracao_ia ?? 0),
      limit: Number(userDashboard?.limites?.geracao_ia ?? 0),
      icon: <LuZap />,
    },
  ];

  return (
    <section className={`dashboard-section-card dashboard-plan-card ${className}`.trim()}>
      <div className="dashboard-section-head">
        <div>
          <h3>Limites do plano</h3>
          <p>Uso atual para acompanhar espaco, busca e geracao.</p>
        </div>
      </div>
      <div className="dashboard-plan-list">
        {items.map((item) => {
          const progress = item.limit > 0 ? Math.min((item.used / item.limit) * 100, 100) : 0;
          return (
            <div key={item.label} className="dashboard-plan-item">
              <div className="dashboard-plan-row">
                <span className="dashboard-plan-label">
                  {item.icon}
                  <strong>{item.label}</strong>
                </span>
                <span className="dashboard-plan-value">{item.used} / {item.limit}</span>
              </div>
              <div className="dashboard-plan-track">
                <div className="dashboard-plan-fill" style={{ width: `${progress}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function DashboardPage() {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState(null);
  const [adminStats, setAdminStats] = useState(null);
  const [userDashboard, setUserDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusCounts, setStatusCounts] = useState([]);
  const [recentActivities, setRecentActivities] = useState([]);

  useEffect(() => {
    let cancelled = false;
    async function fetchData() {
      setLoading(true);
      try {
        const user = await authService.getCurrentUser();
        if (cancelled) return;
        setCurrentUser(user);

        if (user?.is_superuser) {
          const counts = await adminService.getTotalCounts();
          if (cancelled) return;
          setAdminStats(counts);

          try {
            const [statusData, activities] = await Promise.all([
              adminService.getProductStatusCounts(),
              adminService.getRecentHistorico(5),
            ]);
            if (cancelled) return;
            setStatusCounts(statusData);
            setRecentActivities(activities);
          } catch (innerErr) {
            console.error('Erro ao buscar dados adicionais do dashboard:', innerErr);
          }
          return;
        }

        const dashboardPayload = await dashboardService.getMyDashboard();
        if (cancelled) return;
        setUserDashboard(dashboardPayload);
      } catch (err) {
        const errorMsg = err.message || err.detail || 'Falha ao carregar dados do dashboard.';
        showErrorToast(errorMsg);
        console.error('Erro ao carregar dados do dashboard:', err);
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void fetchData();
    return () => {
      cancelled = true;
    };
  }, []);

  const adminCounts = useMemo(() => ({
    notStarted: getTotalByStatus(statusCounts, 'NAO_INICIADO'),
    failures: getTotalByStatus(statusCounts, 'FALHA', 'FALHOU', 'FALHA_API_EXTERNA', 'FALHA_CONFIGURACAO_API_EXTERNA'),
    partial: getTotalByStatus(statusCounts, 'CONCLUIDO_COM_DADOS_PARCIAIS', 'NENHUMA_FONTE_ENCONTRADA'),
  }), [statusCounts]);

  const adminCards = useMemo(() => {
    if (!adminStats) return [];
    return [
      {
        value: adminStats.total_produtos?.toString() || '0',
        label: 'Total Produtos',
        helper: 'Base operacional',
        icon: <LuBox />,
        barColor: '#111111',
        tone: 'neutral',
      },
      {
        value: adminCounts.notStarted?.toString() || '0',
        label: 'Aguardando inicio',
        helper: 'Fila bruta do catalogo',
        icon: <LuClock3 />,
        barColor: '#2563eb',
        tone: 'info',
      },
      {
        value: (adminCounts.failures + adminCounts.partial)?.toString() || '0',
        label: 'Em atencao',
        helper: 'Falhas e dados incompletos',
        icon: <LuBadgeAlert />,
        barColor: '#dc2626',
        tone: 'danger',
      },
      {
        value: adminStats.total_geracoes_ia_mes?.toString() || '0',
        label: 'Geracoes IA no mes',
        helper: 'Consumo atual',
        icon: <LuSparkles />,
        barColor: '#d97706',
        tone: 'warn',
      },
    ];
  }, [adminCounts.failures, adminCounts.notStarted, adminCounts.partial, adminStats]);

  const userCards = useMemo(() => {
    if (!userDashboard) return [];
    const productsRemaining = Math.max(
      Number(userDashboard?.limites?.produtos ?? 0) - Number(userDashboard?.totais?.produtos ?? 0),
      0
    );
    const webRemaining = Math.max(
      Number(userDashboard?.limites?.enriquecimento_web ?? 0) - Number(userDashboard?.uso_mes_atual?.enriquecimento_web ?? 0),
      0
    );
    const aiRemaining = Math.max(
      Number(userDashboard?.limites?.geracao_ia ?? 0) - Number(userDashboard?.uso_mes_atual?.geracao_ia ?? 0),
      0
    );

    return [
      {
        value: userDashboard?.totais?.produtos?.toString() || '0',
        label: 'Produtos',
        helper: 'Catalogo atual',
        icon: <LuBox />,
        barColor: '#111111',
        tone: 'neutral',
      },
      {
        value: productsRemaining.toString(),
        label: 'Produtos restantes',
        helper: 'Espaco ainda disponivel',
        icon: <LuLayers />,
        barColor: '#2563eb',
        tone: 'info',
      },
      {
        value: webRemaining.toString(),
        label: 'Busca web restante',
        helper: 'Operacoes disponiveis',
        icon: <LuBell />,
        barColor: '#059669',
        tone: 'success',
      },
      {
        value: aiRemaining.toString(),
        label: 'IA restante',
        helper: 'Geracoes disponiveis',
        icon: <LuZap />,
        barColor: '#d97706',
        tone: 'warn',
      },
    ];
  }, [userDashboard]);

  const dashboardMode = userDashboard?.product_experience_mode || currentUser?.product_experience_mode || 'basic';
  const userStatusCounts = useMemo(
    () => (userDashboard?.status_produtos || []).map((item) => ({
      status: item.status,
      total: item.total,
    })),
    [userDashboard]
  );
  const adminHighlights = useMemo(() => buildAdminHighlights(statusCounts), [statusCounts]);
  const userHighlights = useMemo(() => buildUserHighlights(userDashboard), [userDashboard]);
  const dashboardSubtitle = currentUser?.is_superuser
    ? buildAdminSummaryLine(statusCounts)
    : buildUserSummaryLine(userDashboard, currentUser);
  const dashboardHeroStats = currentUser?.is_superuser
    ? buildAdminHeroStats(adminStats)
    : [];

  if (loading) {
    return <LoadingOverlay isOpen={true} message="Carregando dashboard..." />;
  }

  return (
    <div id="dashboard-pro-main" className="dashboard-page-shell">
      <CommandCenter
        kicker={currentUser?.is_superuser ? 'Painel administrativo' : 'Painel do cliente'}
        summary={dashboardSubtitle}
        pills={(currentUser?.is_superuser ? adminHighlights : userHighlights).slice(0, 3)}
        sideStats={dashboardHeroStats}
        badgeLabel={
          currentUser?.is_superuser
            ? 'Operacao central'
            : null
        }
      />

      <section className="pro-stats-row">
        {(currentUser?.is_superuser ? adminCards : userCards).map((card) => (
          <MetricCard key={card.label} {...card} />
        ))}
      </section>

      <div className={`dashboard-main-grid ${currentUser?.is_superuser ? 'admin' : 'user'}`}>
        <StatusPanel
          title="Status dos produtos"
          helper={
            currentUser?.is_superuser
              ? 'Distribuicao atual do pipeline e do backlog do catalogo.'
              : 'Como seus produtos estao distribuidos no fluxo atual.'
          }
          items={currentUser?.is_superuser ? statusCounts : userStatusCounts}
          emptyMessage="Sem dados de status para mostrar."
          className="dashboard-grid-panel dashboard-panel-status"
        />

        <HighlightsPanel
          title={currentUser?.is_superuser ? 'Prioridades do dia' : 'Onde agir agora'}
          helper={
            currentUser?.is_superuser
              ? 'Cards com leitura direta e atalho para as areas que precisam de acao.'
              : 'Pontos do plano e do catalogo que valem sua proxima acao.'
          }
          items={currentUser?.is_superuser ? adminHighlights : userHighlights}
          emptyMessage="Ainda nao ha indicadores suficientes para destacar."
          onNavigate={navigate}
          className="dashboard-grid-panel dashboard-panel-priorities"
        />

        {currentUser?.is_superuser ? null : (
          <PlanUsagePanel
            userDashboard={userDashboard}
            className="dashboard-grid-panel dashboard-panel-plan"
          />
        )}

        <ActivityFeed
          title="Atividade recente"
          helper={
            currentUser?.is_superuser
              ? 'Ultimas alteracoes registradas na operacao.'
              : 'Ultimas movimentacoes na sua conta.'
          }
          items={currentUser?.is_superuser ? recentActivities : userDashboard?.atividade_recente || []}
          emptyMessage="Nenhuma atividade recente encontrada."
          className="dashboard-grid-panel dashboard-panel-activity"
        />
      </div>
    </div>
  );
}

export default DashboardPage;
