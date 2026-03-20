/**
 * Module workspace page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';
import { LuBuilding2, LuUsers, LuPencil, LuCheck, LuX, LuPlus, LuLogOut, LuMail, LuTrash2 } from 'react-icons/lu';
import workspaceService from '../services/workspaceService';
import { useAuth } from '../contexts/AuthContext';
import './WorkspacePage.css';

function WorkspacePage() {
  const { currentUser } = useAuth();
  const [workspace, setWorkspace] = useState(null);
  const [members, setMembers] = useState([]);
  const [invites, setInvites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviting, setInviting] = useState(false);

  const [formData, setFormData] = useState({ nome: '', cnpj: '' });
  const [createData, setCreateData] = useState({ nome: '', cnpj: '' });

  const loadWorkspace = useCallback(async () => {
    setLoading(true);
    try {
      const data = await workspaceService.getWorkspace();
      setWorkspace(data);
      setFormData({ nome: data.nome, cnpj: data.cnpj || '' });
      const [membersData, invitesData] = await Promise.all([
        workspaceService.getWorkspaceMembers(),
        workspaceService.listInvites().catch(() => []),
      ]);
      setMembers(membersData);
      setInvites(invitesData);
    } catch {
      setWorkspace(null);
      setMembers([]);
      setInvites([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWorkspace();
  }, [loadWorkspace]);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!createData.nome.trim()) return;
    setSaving(true);
    try {
      await workspaceService.createWorkspace({ nome: createData.nome.trim(), cnpj: createData.cnpj.trim() || null });
      toast.success('Empresa criada com sucesso!');
      setCreating(false);
      setCreateData({ nome: '', cnpj: '' });
      await loadWorkspace();
    } catch (err) {
      toast.error(err?.detail || err?.message || 'Erro ao criar empresa.');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await workspaceService.updateWorkspace({
        nome: formData.nome.trim() || undefined,
        cnpj: formData.cnpj.trim() || null,
      });
      setWorkspace(updated);
      setEditing(false);
      toast.success('Dados da empresa atualizados.');
    } catch (err) {
      toast.error(err?.detail || err?.message || 'Erro ao atualizar empresa.');
    } finally {
      setSaving(false);
    }
  };

  const handleLeave = async () => {
    if (!window.confirm('Tem certeza que deseja sair desta empresa?')) return;
    try {
      await workspaceService.leaveWorkspace();
      toast.info('Você saiu da empresa.');
      await loadWorkspace();
    } catch (err) {
      toast.error(err?.detail || err?.message || 'Erro ao sair da empresa.');
    }
  };

  const handleInvite = async (e) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setInviting(true);
    try {
      const invite = await workspaceService.createInvite(inviteEmail.trim());
      const link = `${window.location.origin}/invite/${invite.token}`;
      await navigator.clipboard.writeText(link).catch(() => {});
      toast.success(`Convite criado! Link copiado: ${link}`);
      setInviteEmail('');
      const invitesData = await workspaceService.listInvites();
      setInvites(invitesData);
    } catch (err) {
      toast.error(err?.response?.data?.detail || err?.message || 'Erro ao criar convite.');
    } finally {
      setInviting(false);
    }
  };

  const handleRevokeInvite = async (inviteId) => {
    if (!window.confirm('Revogar este convite?')) return;
    try {
      await workspaceService.revokeInvite(inviteId);
      setInvites((prev) => prev.filter((i) => i.id !== inviteId));
      toast.info('Convite revogado.');
    } catch (err) {
      toast.error(err?.response?.data?.detail || err?.message || 'Erro ao revogar convite.');
    }
  };

  if (loading) {
    return (
      <div className="wp-container">
        <div className="wp-loading">Carregando...</div>
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="wp-container">
        <div className="wp-header">
          <LuBuilding2 className="wp-header-icon" />
          <div>
            <h1 className="wp-title">Workspace</h1>
            <p className="wp-subtitle">Você ainda não pertence a nenhuma empresa.</p>
          </div>
        </div>

        {!creating ? (
          <button className="wp-btn-primary" onClick={() => setCreating(true)}>
            <LuPlus /> Criar Empresa
          </button>
        ) : (
          <div className="wp-card">
            <h2 className="wp-card-title">Nova Empresa</h2>
            <form onSubmit={handleCreate} className="wp-form">
              <label className="wp-label">Nome da empresa *</label>
              <input
                className="wp-input"
                type="text"
                placeholder="Ex: Minha Empresa Ltda"
                value={createData.nome}
                onChange={(e) => setCreateData((p) => ({ ...p, nome: e.target.value }))}
                required
              />
              <label className="wp-label">CNPJ (opcional)</label>
              <input
                className="wp-input"
                type="text"
                placeholder="00.000.000/0000-00"
                value={createData.cnpj}
                onChange={(e) => setCreateData((p) => ({ ...p, cnpj: e.target.value }))}
              />
              <div className="wp-form-actions">
                <button type="submit" className="wp-btn-primary" disabled={saving}>
                  {saving ? 'Criando...' : <><LuCheck /> Criar</>}
                </button>
                <button type="button" className="wp-btn-ghost" onClick={() => setCreating(false)}>
                  <LuX /> Cancelar
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    );
  }

  const isCreator = workspace.criado_por_user_id === currentUser?.id;

  return (
    <div className="wp-container">
      <div className="wp-header">
        <LuBuilding2 className="wp-header-icon" />
        <div>
          <h1 className="wp-title">Workspace</h1>
          <p className="wp-subtitle">Gerencie os dados da sua empresa.</p>
        </div>
      </div>

      <div className="wp-card">
        <div className="wp-card-header-row">
          <h2 className="wp-card-title">Dados da Empresa</h2>
          {isCreator && !editing && (
            <button className="wp-btn-ghost wp-btn-sm" onClick={() => setEditing(true)}>
              <LuPencil /> Editar
            </button>
          )}
        </div>

        {editing ? (
          <form onSubmit={handleSaveEdit} className="wp-form">
            <label className="wp-label">Nome da empresa *</label>
            <input
              className="wp-input"
              type="text"
              value={formData.nome}
              onChange={(e) => setFormData((p) => ({ ...p, nome: e.target.value }))}
              required
            />
            <label className="wp-label">CNPJ (opcional)</label>
            <input
              className="wp-input"
              type="text"
              placeholder="00.000.000/0000-00"
              value={formData.cnpj}
              onChange={(e) => setFormData((p) => ({ ...p, cnpj: e.target.value }))}
            />
            <div className="wp-form-actions">
              <button type="submit" className="wp-btn-primary" disabled={saving}>
                {saving ? 'Salvando...' : <><LuCheck /> Salvar</>}
              </button>
              <button type="button" className="wp-btn-ghost" onClick={() => { setEditing(false); setFormData({ nome: workspace.nome, cnpj: workspace.cnpj || '' }); }}>
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
            <dt>Criado em</dt>
            <dd>{new Date(workspace.created_at).toLocaleDateString('pt-BR')}</dd>
          </dl>
        )}
      </div>

      <div className="wp-card">
        <div className="wp-card-header-row">
          <h2 className="wp-card-title">
            <LuUsers style={{ marginRight: 6 }} />
            Membros ({members.length})
          </h2>
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
            {members.map((m) => (
              <tr key={m.id}>
                <td>{m.email}</td>
                <td>{m.nome_completo || <span className="wp-empty">—</span>}</td>
                <td>
                  <span className={`wp-status-badge ${m.is_active ? 'active' : 'inactive'}`}>
                    {m.is_active ? 'Ativo' : 'Inativo'}
                  </span>
                </td>
              </tr>
            ))}
            {members.length === 0 && (
              <tr>
                <td colSpan={3} className="wp-empty-row">Nenhum membro encontrado.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {isCreator && (
        <div className="wp-card">
          <div className="wp-card-header-row">
            <h2 className="wp-card-title">
              <LuMail style={{ marginRight: 6 }} />
              Convites Pendentes ({invites.length})
            </h2>
          </div>
          <form onSubmit={handleInvite} className="wp-invite-form">
            <input
              className="wp-input"
              type="email"
              placeholder="email@exemplo.com"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              required
            />
            <button type="submit" className="wp-btn-primary" disabled={inviting}>
              {inviting ? 'Enviando...' : <><LuPlus /> Convidar</>}
            </button>
          </form>
          {invites.length > 0 && (
            <table className="wp-members-table" style={{ marginTop: 12 }}>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Expira em</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {invites.map((inv) => (
                  <tr key={inv.id}>
                    <td>{inv.email}</td>
                    <td>{new Date(inv.expires_at).toLocaleDateString('pt-BR')}</td>
                    <td>
                      <button
                        className="wp-btn-ghost wp-btn-sm"
                        title="Revogar convite"
                        onClick={() => handleRevokeInvite(inv.id)}
                      >
                        <LuTrash2 />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      <div className="wp-danger-zone">
        <h3 className="wp-danger-title">Zona de Perigo</h3>
        <p className="wp-danger-text">Ao sair da empresa, você perderá o acesso aos recursos compartilhados.</p>
        <button className="wp-btn-danger" onClick={handleLeave}>
          <LuLogOut /> Sair da Empresa
        </button>
      </div>
    </div>
  );
}

export default WorkspacePage;
