/**
 * Module workspace page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import {
  LuArrowRight,
  LuBadgeDollarSign,
  LuBuilding2,
  LuCheck,
  LuCreditCard,
  LuLogOut,
  LuMail,
  LuPencil,
  LuPlug,
  LuPlus,
  LuSettings2,
  LuTrash2,
  LuUsers,
  LuX,
} from 'react-icons/lu';
import { useAuth } from '../contexts/AuthContext';
import { useWorkspace } from '../contexts/WorkspaceContext';
import workspaceService from '../services/workspaceService';
import './WorkspacePage.css';

const WORKSPACE_TABS = [
  { id: 'empresa', label: 'Empresa', icon: LuBuilding2 },
  { id: 'usuarios', label: 'Usuários', icon: LuUsers },
  { id: 'financeiro', label: 'Financeiro', icon: LuCreditCard },
  { id: 'integracoes', label: 'Integrações', icon: LuPlug },
];

function extractErrorMessage(err, fallback) {
  return err?.response?.data?.detail || err?.detail || err?.message || fallback;
}

function WorkspacePage() {
  const { user } = useAuth();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    workspace,
    hasWorkspace,
    isLoading: isWorkspaceLoading,
    refreshWorkspace,
  } = useWorkspace();

  const [members, setMembers] = useState([]);
  const [invites, setInvites] = useState([]);
  const [pageLoading, setPageLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviting, setInviting] = useState(false);
  const [formData, setFormData] = useState({ nome: '', cnpj: '' });
  const [createData, setCreateData] = useState({ nome: '', cnpj: '' });
  const setupMode = useMemo(
    () => new URLSearchParams(location.search).get('setup') === '1',
    [location.search]
  );

  const requestedTab = searchParams.get('tab');
  const activeTab = WORKSPACE_TABS.some((tab) => tab.id === requestedTab) ? requestedTab : 'empresa';

  const selectTab = (tabId) => {
    const nextParams = new URLSearchParams(searchParams);
    if (tabId === 'empresa') {
      nextParams.delete('tab');
    } else {
      nextParams.set('tab', tabId);
    }
    setSearchParams(nextParams, { replace: true });
  };

  useEffect(() => {
    if (!hasWorkspace) {
      setMembers([]);
      setInvites([]);
      setPageLoading(false);
      return;
    }

    let cancelled = false;

    async function loadWorkspaceDetails() {
      setPageLoading(true);
      try {
        const [membersData, invitesData] = await Promise.all([
          workspaceService.getWorkspaceMembers(),
          workspaceService.listInvites().catch(() => []),
        ]);
        if (!cancelled) {
          setMembers(membersData);
          setInvites(invitesData);
        }
      } catch {
        if (!cancelled) {
          setMembers([]);
          setInvites([]);
        }
      } finally {
        if (!cancelled) {
          setPageLoading(false);
        }
      }
    }

    void loadWorkspaceDetails();

    return () => {
      cancelled = true;
    };
  }, [hasWorkspace, workspace?.id]);

  useEffect(() => {
    if (workspace) {
      setFormData({ nome: workspace.nome, cnpj: workspace.cnpj || '' });
    }
  }, [workspace]);

  const handleCreate = async (event) => {
    event.preventDefault();
    if (!createData.nome.trim()) {
      return;
    }

    setSaving(true);
    try {
      await workspaceService.createWorkspace({
        nome: createData.nome.trim(),
        cnpj: createData.cnpj.trim() || null,
      });
      await refreshWorkspace();
      setCreating(false);
      setCreateData({ nome: '', cnpj: '' });
      toast.success('Empresa criada com sucesso.');
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Erro ao criar empresa.'));
    } finally {
      setSaving(false);
    }
  };

  const handleSaveEdit = async (event) => {
    event.preventDefault();
    setSaving(true);
    try {
      await workspaceService.updateWorkspace({
        nome: formData.nome.trim() || undefined,
        cnpj: formData.cnpj.trim() || null,
      });
      await refreshWorkspace();
      setEditing(false);
      toast.success('Dados da empresa atualizados.');
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Erro ao atualizar empresa.'));
    } finally {
      setSaving(false);
    }
  };

  const handleLeave = async () => {
    if (!window.confirm('Tem certeza que deseja sair desta empresa?')) {
      return;
    }

    try {
      await workspaceService.leaveWorkspace();
      await refreshWorkspace();
      toast.info('Você saiu da empresa.');
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Erro ao sair da empresa.'));
    }
  };

  const handleInvite = async (event) => {
    event.preventDefault();
    if (!inviteEmail.trim()) {
      return;
    }

    setInviting(true);
    try {
      const invite = await workspaceService.createInvite(inviteEmail.trim());
      const link = `${window.location.origin}/invite/${invite.token}`;
      await navigator.clipboard.writeText(link).catch(() => {});
      setInviteEmail('');
      setInvites(await workspaceService.listInvites());
      toast.success('Convite criado. O link foi copiado para a área de transferência.');
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Erro ao criar convite.'));
    } finally {
      setInviting(false);
    }
  };

  const handleRevokeInvite = async (inviteId) => {
    if (!window.confirm('Revogar este convite?')) {
      return;
    }

    try {
      await workspaceService.revokeInvite(inviteId);
      setInvites((previous) => previous.filter((invite) => invite.id !== inviteId));
      toast.info('Convite revogado.');
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Erro ao revogar convite.'));
    }
  };

  if (isWorkspaceLoading || pageLoading) {
    return (
      <div className="wp-container">
        <div className="wp-loading">Carregando empresa...</div>
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="wp-container wp-setup-container">
        <div className="wp-header">
          <LuBuilding2 className="wp-header-icon" />
          <div>
            <h1 className="wp-title">Primeiro passo: configure sua empresa</h1>
            <p className="wp-subtitle">
              {setupMode
                ? 'Para continuar no CommerceFolio, você precisa criar uma empresa ou entrar com um convite.'
                : 'Você ainda não pertence a nenhuma empresa.'}
            </p>
          </div>
        </div>

        <div className="wp-setup-grid">
          <section className="wp-card">
            <h2 className="wp-card-title">Criar empresa</h2>
            <p className="wp-card-copy">
              Centralize catálogo, integrações, plano e membros em um único espaço de trabalho.
            </p>

            {!creating ? (
              <button className="wp-btn-primary" onClick={() => setCreating(true)}>
                <LuPlus /> Criar minha empresa
              </button>
            ) : (
              <form onSubmit={handleCreate} className="wp-form">
                <label className="wp-label">Nome da empresa *</label>
                <input
                  className="wp-input"
                  type="text"
                  placeholder="Ex: Minha Loja"
                  value={createData.nome}
                  onChange={(event) =>
                    setCreateData((current) => ({ ...current, nome: event.target.value }))
                  }
                  required
                />

                <label className="wp-label">CNPJ (opcional)</label>
                <input
                  className="wp-input"
                  type="text"
                  placeholder="00.000.000/0000-00"
                  value={createData.cnpj}
                  onChange={(event) =>
                    setCreateData((current) => ({ ...current, cnpj: event.target.value }))
                  }
                />

                <div className="wp-form-actions">
                  <button type="submit" className="wp-btn-primary" disabled={saving}>
                    {saving ? 'Criando...' : <><LuCheck /> Criar empresa</>}
                  </button>
                  <button
                    type="button"
                    className="wp-btn-ghost"
                    onClick={() => setCreating(false)}
                    disabled={saving}
                  >
                    <LuX /> Cancelar
                  </button>
                </div>
              </form>
            )}
          </section>

          <section className="wp-card">
            <h2 className="wp-card-title">Entrar com convite</h2>
            <p className="wp-card-copy">
              Se outra empresa já te convidou, use o link recebido por email para entrar direto no workspace.
            </p>
            <div className="wp-setup-invite-card">
              <LuMail className="wp-setup-invite-icon" />
              <div>
                <strong>Já recebeu convite?</strong>
                <p>Abra o link do convite e aceite a entrada na empresa para continuar.</p>
              </div>
            </div>
            <Link to="/landing" className="wp-inline-link">
              Voltar ao site <LuArrowRight />
            </Link>
          </section>
        </div>
      </div>
    );
  }

  const isCreator = workspace.criado_por_user_id === user?.id || user?.is_superuser;
  const currentPlanName = user?.plano?.nome || 'Sem plano ativo';
  const createdAtLabel = new Date(workspace.created_at).toLocaleDateString('pt-BR');
  const ownerLabel = isCreator ? 'Owner / admin principal' : 'Membro da empresa';

  const heroCards = [
    { label: 'Membros', value: members.length, tone: 'neutral' },
    { label: 'Convites pendentes', value: invites.length, tone: 'accent' },
    { label: 'Plano atual', value: currentPlanName, tone: 'soft' },
  ];

  return (
    <div className="wp-container wp-admin-container">
      <div className="wp-header wp-header-stack">
        <div className="wp-context-chip">{workspace.nome}</div>
        <div className="wp-header-row">
          <div>
            <h1 className="wp-title">Minha Empresa</h1>
            <p className="wp-subtitle">
              Administre identidade, acessos, plano e o ecossistema do workspace.
            </p>
          </div>
          <div className="wp-hero-meta">
            <span className="wp-meta-pill">{ownerLabel}</span>
            <span className="wp-meta-pill">Criada em {createdAtLabel}</span>
          </div>
        </div>
      </div>

      <section className="wp-card wp-hero-card">
        <div className="wp-hero-main">
          <div className="wp-hero-icon">
            <LuBuilding2 />
          </div>
          <div>
            <h2 className="wp-card-title">{workspace.nome}</h2>
            <p className="wp-card-copy">
              Tudo que é configurado aqui passa a orientar catálogo, membros, prompts, integrações e cobrança.
            </p>
          </div>
        </div>
        <div className="wp-hero-stats">
          {heroCards.map((item) => (
            <div key={item.label} className={`wp-stat-card ${item.tone}`}>
              <span className="wp-stat-label">{item.label}</span>
              <strong className="wp-stat-value">{item.value}</strong>
            </div>
          ))}
        </div>
      </section>

      <div className="wp-tabbar" role="tablist" aria-label="Navegação da empresa">
        {WORKSPACE_TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`wp-tab ${isActive ? 'active' : ''}`}
              onClick={() => selectTab(tab.id)}
            >
              <Icon />
              {tab.label}
            </button>
          );
        })}
      </div>

      {activeTab === 'empresa' ? (
        <div className="wp-tab-grid">
          <div className="wp-card">
            <div className="wp-card-header-row">
              <div>
                <h2 className="wp-card-title">Dados da empresa</h2>
                <p className="wp-card-copy">
                  Defina o nome e o identificador principal usados neste workspace.
                </p>
              </div>
              {isCreator && !editing ? (
                <button className="wp-btn-ghost wp-btn-sm" onClick={() => setEditing(true)}>
                  <LuPencil /> Editar
                </button>
              ) : null}
            </div>

            {editing ? (
              <form onSubmit={handleSaveEdit} className="wp-form">
                <label className="wp-label">Nome da empresa *</label>
                <input
                  className="wp-input"
                  type="text"
                  value={formData.nome}
                  onChange={(event) =>
                    setFormData((current) => ({ ...current, nome: event.target.value }))
                  }
                  required
                />

                <label className="wp-label">CNPJ (opcional)</label>
                <input
                  className="wp-input"
                  type="text"
                  placeholder="00.000.000/0000-00"
                  value={formData.cnpj}
                  onChange={(event) =>
                    setFormData((current) => ({ ...current, cnpj: event.target.value }))
                  }
                />

                <div className="wp-form-actions">
                  <button type="submit" className="wp-btn-primary" disabled={saving}>
                    {saving ? 'Salvando...' : <><LuCheck /> Salvar</>}
                  </button>
                  <button
                    type="button"
                    className="wp-btn-ghost"
                    onClick={() => {
                      setEditing(false);
                      setFormData({ nome: workspace.nome, cnpj: workspace.cnpj || '' });
                    }}
                    disabled={saving}
                  >
                    <LuX /> Cancelar
                  </button>
                </div>
              </form>
            ) : (
              <dl className="wp-info-list">
                <dt>Nome</dt>
                <dd>{workspace.nome}</dd>
                <dt>CNPJ</dt>
                <dd>{workspace.cnpj || <span className="wp-empty">Não informado</span>}</dd>
                <dt>Criada em</dt>
                <dd>{createdAtLabel}</dd>
                <dt>Gestão</dt>
                <dd>{ownerLabel}</dd>
              </dl>
            )}
          </div>

          <aside className="wp-card wp-side-panel">
            <h2 className="wp-card-title">Governança</h2>
            <div className="wp-side-list">
              <div className="wp-side-list-item">
                <span className="wp-side-label">Empresa ativa</span>
                <strong>{workspace.nome}</strong>
              </div>
              <div className="wp-side-list-item">
                <span className="wp-side-label">Plano</span>
                <strong>{currentPlanName}</strong>
              </div>
              <div className="wp-side-list-item">
                <span className="wp-side-label">Membros</span>
                <strong>{members.length}</strong>
              </div>
            </div>
            <div className="wp-shortcut-list">
              <Link to="/configuracoes?tab=credentials" className="wp-shortcut-card">
                <LuSettings2 />
                <div>
                  <strong>Configurar integrações</strong>
                  <span>Credenciais, fontes e provedores desta empresa.</span>
                </div>
              </Link>
              <Link to="/configuracoes?tab=ai" className="wp-shortcut-card">
                <LuPlug />
                <div>
                  <strong>Ajustar IA e templates</strong>
                  <span>Política, prompts e padrões de geração por empresa.</span>
                </div>
              </Link>
            </div>
          </aside>
        </div>
      ) : null}

      {activeTab === 'usuarios' ? (
        <div className="wp-tab-grid">
          <div className="wp-card">
            <div className="wp-card-header-row">
              <div>
                <h2 className="wp-card-title">
                  <LuUsers style={{ marginRight: 6 }} />
                  Membros ({members.length})
                </h2>
                <p className="wp-card-copy">
                  Pessoas que operam catálogo, configurações ou administração dentro desta empresa.
                </p>
              </div>
            </div>
            <table className="wp-members-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Nome</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => (
                  <tr key={member.id}>
                    <td>{member.email}</td>
                    <td>{member.nome_completo || <span className="wp-empty">—</span>}</td>
                    <td>
                      <span className={`wp-status-badge ${member.is_active ? 'active' : 'inactive'}`}>
                        {member.is_active ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                  </tr>
                ))}
                {members.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="wp-empty-row">
                      Nenhum membro encontrado.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>

          <aside className="wp-card wp-side-panel">
            <div className="wp-card-header-row">
              <div>
                <h2 className="wp-card-title">Convites</h2>
                <p className="wp-card-copy">
                  Convide membros por email para entrarem diretamente neste workspace.
                </p>
              </div>
            </div>

            {isCreator ? (
              <>
                <form onSubmit={handleInvite} className="wp-form">
                  <label className="wp-label">Email do novo membro</label>
                  <input
                    className="wp-input"
                    type="email"
                    placeholder="email@exemplo.com"
                    value={inviteEmail}
                    onChange={(event) => setInviteEmail(event.target.value)}
                    required
                  />
                  <button type="submit" className="wp-btn-primary" disabled={inviting}>
                    {inviting ? 'Enviando...' : <><LuPlus /> Enviar convite</>}
                  </button>
                </form>

                {invites.length > 0 ? (
                  <div className="wp-pending-list">
                    {invites.map((invite) => (
                      <div key={invite.id} className="wp-pending-item">
                        <div>
                          <strong>{invite.email}</strong>
                          <span>Expira em {new Date(invite.expires_at).toLocaleDateString('pt-BR')}</span>
                        </div>
                        <button
                          className="wp-btn-ghost wp-btn-sm"
                          title="Revogar convite"
                          onClick={() => handleRevokeInvite(invite.id)}
                        >
                          <LuTrash2 />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="wp-empty-copy">Nenhum convite pendente no momento.</p>
                )}
              </>
            ) : (
              <p className="wp-empty-copy">
                Somente o owner ou um superusuario pode enviar convites para esta empresa.
              </p>
            )}
          </aside>
        </div>
      ) : null}

      {activeTab === 'financeiro' ? (
        <div className="wp-tab-grid">
          <div className="wp-card">
            <div className="wp-card-header-row">
              <div>
                <h2 className="wp-card-title">
                  <LuBadgeDollarSign style={{ marginRight: 6 }} />
                  Financeiro e plano
                </h2>
                <p className="wp-card-copy">
                  O plano da empresa, créditos e cobrança devem ser administrados de forma centralizada.
                </p>
              </div>
            </div>

            <div className="wp-finance-grid">
              <div className="wp-stat-card soft">
                <span className="wp-stat-label">Plano atual</span>
                <strong className="wp-stat-value">{currentPlanName}</strong>
              </div>
              <div className="wp-stat-card neutral">
                <span className="wp-stat-label">Contexto</span>
                <strong className="wp-stat-value">Cobrado por empresa</strong>
              </div>
            </div>

            <div className="wp-callout">
              <p>
                O objetivo aqui e concentrar o financeiro no nivel da empresa, nao em contas pessoais soltas.
              </p>
              <div className="wp-form-actions">
                <Link to="/financeiro" className="wp-btn-primary wp-link-button">
                  <LuCreditCard /> Ir para plano e faturamento
                </Link>
                <Link to="/configuracoes?tab=plano" className="wp-btn-ghost wp-link-button">
                  <LuSettings2 /> Ver configuracoes de billing
                </Link>
              </div>
            </div>
          </div>

          <aside className="wp-card wp-side-panel">
            <h2 className="wp-card-title">Boas praticas</h2>
            <ul className="wp-check-list">
              <li>Centralizar upgrades e creditos no owner ou admin da empresa.</li>
              <li>Evitar credenciais de cobrança espalhadas por usuário.</li>
              <li>Associar consumo e limites ao workspace ativo.</li>
            </ul>
          </aside>
        </div>
      ) : null}

      {activeTab === 'integracoes' ? (
        <div className="wp-tab-grid">
          <div className="wp-card">
            <div className="wp-card-header-row">
              <div>
                <h2 className="wp-card-title">Integrações e automação</h2>
                <p className="wp-card-copy">
                  Organize o ecossistema da empresa por dominio de responsabilidade, em vez de um formulario unico.
                </p>
              </div>
            </div>

            <div className="wp-shortcut-grid">
              <Link to="/configuracoes?tab=credentials" className="wp-shortcut-card">
                <LuPlug />
                <div>
                  <strong>Loja e credenciais</strong>
                  <span>OpenAI, Gemini, CSE, LM Studio e overrides por empresa.</span>
                </div>
              </Link>
              <Link to="/configuracoes?tab=ai" className="wp-shortcut-card">
                <LuSettings2 />
                <div>
                  <strong>IA e templates</strong>
                  <span>Política, templates do modo básico e comportamento da geração.</span>
                </div>
              </Link>
              <Link to="/configuracoes?tab=importacao" className="wp-shortcut-card">
                <LuMail />
                <div>
                  <strong>Importação e aprendizado</strong>
                  <span>Regras aprendidas e revisões automáticas do pipeline.</span>
                </div>
              </Link>
              <Link to="/configuracoes?tab=plano" className="wp-shortcut-card">
                <LuCreditCard />
                <div>
                  <strong>Plano e billing</strong>
                  <span>Gestão de assinatura, consumo e cobrança por empresa.</span>
                </div>
              </Link>
            </div>
          </div>

          <aside className="wp-card wp-side-panel">
            <h2 className="wp-card-title">Contexto ativo</h2>
            <p className="wp-card-copy">
              Todas as integrações devem respeitar a empresa selecionada, para evitar mistura de dados e credenciais.
            </p>
            <div className="wp-side-list">
              <div className="wp-side-list-item">
                <span className="wp-side-label">Empresa</span>
                <strong>{workspace.nome}</strong>
              </div>
              <div className="wp-side-list-item">
                <span className="wp-side-label">Owner</span>
                <strong>{isCreator ? 'Você' : 'Outro admin'}</strong>
              </div>
            </div>
          </aside>
        </div>
      ) : null}

      <div className="wp-danger-zone">
        <h3 className="wp-danger-title">Zona de perigo</h3>
        <p className="wp-danger-text">
          Ao sair da empresa, você perde acesso aos recursos compartilhados até entrar em outra.
        </p>
        <button className="wp-btn-danger" onClick={handleLeave}>
          <LuLogOut /> Sair da Empresa
        </button>
      </div>
    </div>
  );
}

export default WorkspacePage;
