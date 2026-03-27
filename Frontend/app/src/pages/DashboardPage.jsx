/**
 * Dashboard page.
 */

import React, { useEffect, useMemo, useState } from 'react';
import {
  LuBadgeAlert,
  LuBox,
  LuClock3,
  LuSearch,
  LuZap,
} from 'react-icons/lu';
import adminService from '../services/adminService';
import authService from '../services/authService';
import dashboardService from '../services/dashboardService';
import LoadingOverlay from '../components/common/LoadingOverlay.jsx';
import PageHeader from '../components/PageHeader.jsx';
import { showErrorToast } from '../utils/notifications';
import { extractErrorMessage } from '../utils/errorDetails';
import './DashboardPage.css';

const STATUS_META = {
  NAO_INICIADO: { label: 'Não iniciado', tone: 'muted' },
  PENDENTE: { label: 'Pendente', tone: 'warn' },
  EM_PROGRESSO: { label: 'Em progresso', tone: 'info' },
  CONCLUIDO: { label: 'Concluído', tone: 'success' },
  CONCLUIDO_SUCESSO: { label: 'Concluído', tone: 'success' },
  CONCLUIDO_COM_DADOS_PARCIAIS: { label: 'Concluído com dados parciais', tone: 'warn' },
  FALHA: { label: 'Falha', tone: 'danger' },
  FALHOU: { label: 'Falha', tone: 'danger' },
  FALHA_API_EXTERNA: { label: 'Falha de API externa', tone: 'danger' },
  FALHA_CONFIGURACAO_API_EXTERNA: { label: 'Falha de configuração', tone: 'danger' },
  NENHUMA_FONTE_ENCONTRADA: { label: 'Nenhuma fonte encontrada', tone: 'muted' },
  NAO_APLICAVEL: { label: 'Não aplicável', tone: 'muted' },
};

const ENTITY_LABELS = {
  produto: 'Produto',
  produtos: 'Produtos',
  fornecedor: 'Fornecedor',
  fornecedores: 'Fornecedores',
  usuario: 'Usuário',
  user: 'Usuário',
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

function OverviewPanel({ items, className = '' }) {
  const normalizedItems = Array.isArray(items) ? items : [];

  return (
    <section className={`dashboard-section-card dashboard-overview-card ${className}`.trim()}>
      <div className="dashboard-section-head">
        <div>
          <h3>Visão geral</h3>
          <p>Resumo rápido do que precisa de atenção.</p>
        </div>
      </div>
      <div className="dashboard-overview-grid">
        {normalizedItems.map((item) => (
          <article key={item.label} className={`dashboard-overview-item tone-${item.tone || 'neutral'}`}>
            <span className="dashboard-overview-icon">{item.icon}</span>
            <div className="dashboard-overview-copy">
              <strong>{item.value}</strong>
              <span>{item.label}</span>
              {item.helper ? <small>{item.helper}</small> : null}
            </div>
          </article>
        ))}
      </div>
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
      label: 'Geração IA',
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
          <p>Uso atual para acompanhar espaço, busca e geração.</p>
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

const PERIOD_OPTIONS = [
  { label: '7D', days: 7 },
  { label: '30D', days: 30 },
  { label: '90D', days: 90 },
];

function DashboardPage() {
  const [currentUser, setCurrentUser] = useState(null);
  const [adminStats, setAdminStats] = useState(null);
  const [userDashboard, setUserDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadErrorMessage, setLoadErrorMessage] = useState('');
  const [statusCounts, setStatusCounts] = useState([]);
  const [recentActivities, setRecentActivities] = useState([]);
  const [reloadToken, setReloadToken] = useState(0);
  const [period, setPeriod] = useState(30);

  useEffect(() => {
    let cancelled = false;
    async function fetchData() {
      setLoading(true);
      setLoadErrorMessage('');
      try {
        const user = await authService.getCurrentUser();
        if (cancelled) return;
        setCurrentUser(user);

        if (user?.is_superuser) {
          try {
            const [counts, statusData, activities] = await Promise.all([
              adminService.getTotalCounts(),
              adminService.getProductStatusCounts(),
              adminService.getRecentHistorico(5),
            ]);
            if (cancelled) return;
            setAdminStats(counts);
            setStatusCounts(statusData);
            setRecentActivities(activities);
          } catch (innerErr) {
            console.error('Erro ao buscar dados adicionais do dashboard:', innerErr);
          }
          return;
        }

        const dashboardPayload = await dashboardService.getMyDashboard(period);
        if (cancelled) return;
        setUserDashboard(dashboardPayload);
      } catch (err) {
        const errorMsg = extractErrorMessage(err, 'Falha ao carregar dados do dashboard.');
        setLoadErrorMessage(errorMsg);
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
  }, [reloadToken, period]);

  const adminCounts = useMemo(() => ({
    failures: getTotalByStatus(statusCounts, 'FALHA', 'FALHOU', 'FALHA_API_EXTERNA', 'FALHA_CONFIGURACAO_API_EXTERNA'),
    partial: getTotalByStatus(statusCounts, 'CONCLUIDO_COM_DADOS_PARCIAIS', 'NENHUMA_FONTE_ENCONTRADA'),
    inProgress: getTotalByStatus(statusCounts, 'EM_PROGRESSO', 'PENDENTE'),
  }), [statusCounts]);

  const overviewItems = useMemo(() => {
    if (currentUser?.is_superuser) {
      return [
        {
          label: 'Total produtos',
          value: Number(adminStats?.total_produtos ?? 0),
          helper: 'Base operacional',
          icon: <LuBox />,
          tone: 'neutral',
        },
        {
          label: 'Em atenção',
          value: Number(adminCounts.failures) + Number(adminCounts.partial),
          helper: 'Falhas e dados incompletos',
          icon: <LuBadgeAlert />,
          tone: 'danger',
        },
        {
          label: 'Em andamento',
          value: Number(adminCounts.inProgress),
          helper: 'Fila ativa do catálogo',
          icon: <LuClock3 />,
          tone: 'info',
        },
      ];
    }

    return [
      {
        label: 'Produtos',
        value: Number(userDashboard?.totais?.produtos ?? 0),
        helper: 'Catálogo atual',
        icon: <LuBox />,
        tone: 'neutral',
      },
      {
        label: 'Busca web disponível',
        value: Math.max(
          Number(userDashboard?.limites?.enriquecimento_web ?? 0)
            - Number(userDashboard?.uso_mes_atual?.enriquecimento_web ?? 0),
          0
        ),
        helper: 'Operações restantes',
        icon: <LuSearch />,
        tone: 'info',
      },
      {
        label: 'IA disponível',
        value: Math.max(
          Number(userDashboard?.limites?.geracao_ia ?? 0)
            - Number(userDashboard?.uso_mes_atual?.geracao_ia ?? 0),
          0
        ),
        helper: 'Gerações restantes',
        icon: <LuZap />,
        tone: 'warn',
      },
    ];
  }, [adminCounts.failures, adminCounts.inProgress, adminCounts.partial, adminStats, currentUser?.is_superuser, userDashboard]);

  const userStatusCounts = useMemo(
    () => (userDashboard?.status_produtos || []).map((item) => ({
      status: item.status,
      total: item.total,
    })),
    [userDashboard]
  );
  if (loading) {
    return <LoadingOverlay isOpen={true} message="Carregando dashboard..." />;
  }

  if (loadErrorMessage && !currentUser && !userDashboard) {
    return (
      <div className="dashboard-error-state" role="alert">
        <p>{loadErrorMessage}</p>
        <button
          type="button"
          className="dashboard-error-retry"
          onClick={() => setReloadToken((value) => value + 1)}
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  const periodFilters = !currentUser?.is_superuser ? (
    PERIOD_OPTIONS.map((opt) => (
      <button
        key={opt.days}
        type="button"
        className={`dashboard-period-btn${period === opt.days ? ' active' : ''}`}
        onClick={() => setPeriod(opt.days)}
      >
        {opt.label}
      </button>
    ))
  ) : null;

  return (
    <div id="dashboard-pro-main" className="dashboard-page-shell">
      <PageHeader
        title="Dashboard"
        subtitle={currentUser?.is_superuser ? 'Visão operacional do sistema' : 'Resumo do seu catálogo e uso do plano'}
        filters={periodFilters}
      />
      <OverviewPanel items={overviewItems} className="dashboard-overview-strip" />

      <div className={`dashboard-main-grid ${currentUser?.is_superuser ? 'admin' : 'user'}`}>
        <StatusPanel
          title="Status dos produtos"
          helper={
            currentUser?.is_superuser
              ? 'Distribuição atual do pipeline e do backlog do catálogo.'
              : 'Como seus produtos estão distribuídos no fluxo atual.'
          }
          items={currentUser?.is_superuser ? statusCounts : userStatusCounts}
          emptyMessage="Sem dados de status para mostrar."
          className="dashboard-grid-panel dashboard-panel-status"
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
              ? 'Últimas alterações registradas na operação.'
              : 'Últimas movimentações na sua conta.'
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

