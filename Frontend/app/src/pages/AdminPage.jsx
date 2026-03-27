/**
 * Module admin page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import {
  LuShieldCheck,
  LuUsers,
  LuLayoutDashboard,
  LuRefreshCw,
} from 'react-icons/lu';
import adminService from '../services/adminService';
import PageHeader from '../components/PageHeader.jsx';
import './AdminPage.css';

const TABS = [
  { id: 'overview', label: 'Visão Geral', icon: <LuLayoutDashboard /> },
  { id: 'users', label: 'Usuários', icon: <LuUsers /> },
  { id: 'usage', label: 'Uso por Plano', icon: <LuShieldCheck /> },
];

function StatCard({ label, value, color }) {
  return (
    <div className="ap-stat-card" style={{ borderTopColor: color }}>
      <span className="ap-stat-value">{value ?? '—'}</span>
      <span className="ap-stat-label">{label}</span>
    </div>
  );
}

function OverviewTab() {
  const [counts, setCounts] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminService.getTotalCounts()
      .then(setCounts)
      .catch(() => toast.error('Erro ao carregar contagens.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="ap-tab-loading">Carregando...</div>;

  return (
    <div className="ap-stats-grid">
      <StatCard label="Usuários" value={counts?.total_usuarios} color="#6366f1" />
      <StatCard label="Produtos" value={counts?.total_produtos} color="#22c55e" />
      <StatCard label="Fornecedores" value={counts?.total_fornecedores} color="#f59e0b" />
      <StatCard label="Gerações IA (mês)" value={counts?.total_geracoes_ia_mes} color="#ec4899" />
      <StatCard label="Enriquecimentos (mês)" value={counts?.total_enriquecimentos_mes} color="#14b8a6" />
    </div>
  );
}

function UsersTab({ planos }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [changingPlano, setChangingPlano] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    adminService.getUserActivity(0, 200)
      .then(setUsers)
      .catch(() => toast.error('Erro ao carregar usuários.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleChangePlano = async (userId, planoId) => {
    setChangingPlano(userId);
    try {
      await adminService.changeUserPlano(userId, Number(planoId));
      toast.success('Plano atualizado com sucesso!');
      load();
    } catch (err) {
      toast.error(err?.detail || err?.message || 'Erro ao atualizar plano.');
    } finally {
      setChangingPlano(null);
    }
  };

  if (loading) return <div className="ap-tab-loading">Carregando...</div>;

  return (
    <div>
      <div className="ap-table-toolbar">
        <span className="ap-table-count">{users.length} usuários</span>
        <button className="ap-btn-ghost ap-btn-sm" onClick={load}>
          <LuRefreshCw /> Atualizar
        </button>
      </div>
      <div className="ap-table-wrap">
        <table className="ap-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Email</th>
              <th>Nome</th>
              <th>Cadastro</th>
              <th>Produtos</th>
              <th>Gerações (mês)</th>
              <th>Plano</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.user_id}>
                <td className="ap-td-id">{u.user_id}</td>
                <td>{u.email}</td>
                <td>{u.nome_completo || <span className="ap-empty">—</span>}</td>
                <td>{u.created_at ? new Date(u.created_at).toLocaleDateString('pt-BR') : '—'}</td>
                <td className="ap-td-num">{u.total_produtos ?? 0}</td>
                <td className="ap-td-num">{u.total_geracoes_ia_mes_corrente ?? 0}</td>
                <td>
                  <select
                    className="ap-plano-select"
                    disabled={changingPlano === u.user_id || !planos.length}
                    onChange={(e) => e.target.value && handleChangePlano(u.user_id, e.target.value)}
                    defaultValue=""
                  >
                    <option value="" disabled>{u.plano_nome || 'Sem plano'}</option>
                    {planos.map((p) => (
                      <option key={p.id} value={p.id}>{p.nome}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={7} className="ap-empty-row">Nenhum usuário encontrado.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function UsageTab() {
  const [usoPorPlano, setUsoPorPlano] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminService.getUsoIAPorPlano()
      .then(setUsoPorPlano)
      .catch(() => toast.error('Erro ao carregar uso por plano.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="ap-tab-loading">Carregando...</div>;

  const maxVal = Math.max(...usoPorPlano.map((p) => p.total_geracoes_ia_no_mes || 0), 1);

  return (
    <div className="ap-usage-section">
      <h3 className="ap-section-title">Gerações de IA por Plano (mês atual)</h3>
      {usoPorPlano.length === 0 && <p className="ap-empty">Nenhum dado disponível.</p>}
      {usoPorPlano.map((p) => (
        <div key={p.plano_id} className="ap-usage-row">
          <span className="ap-usage-label">{p.nome_plano}</span>
          <div className="ap-usage-bar-wrap">
            <div
              className="ap-usage-bar"
              style={{ width: `${(p.total_geracoes_ia_no_mes / maxVal) * 100}%` }}
            />
          </div>
          <span className="ap-usage-count">{p.total_geracoes_ia_no_mes}</span>
        </div>
      ))}
    </div>
  );
}

function AdminPage() {
  const [activeTab, setActiveTab] = useState('overview');
  const [planos, setPlanos] = useState([]);

  useEffect(() => {
    adminService.getPlanos().then(setPlanos).catch(() => {});
  }, []);

  return (
    <div className="ap-container">
      <PageHeader title="Admin" subtitle="Painel administrativo do sistema" />
      <div className="ap-header">
        <LuShieldCheck className="ap-header-icon" />
        <div>
          <h1 className="ap-title">Administração</h1>
          <p className="ap-subtitle">Visão geral do sistema e gestão de usuários.</p>
        </div>
      </div>

      <div className="ap-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`ap-tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      <div className="ap-tab-content">
        {activeTab === 'overview' && <OverviewTab />}
        {activeTab === 'users' && <UsersTab planos={planos} />}
        {activeTab === 'usage' && <UsageTab />}
      </div>
    </div>
  );
}

export default AdminPage;
