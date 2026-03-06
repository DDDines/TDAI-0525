/**
 * Module configuracoes page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useState, useEffect } from 'react';
import authService from '../services/authService';
import basicTemplateService from '../services/basicTemplateService';
import { showSuccessToast, showErrorToast } from '../utils/notifications';
import ChangePasswordModal from '../components/user/ChangePasswordModal';
import { useAuth } from '../contexts/AuthContext';
import { useAppExperience } from '../contexts/AppExperienceContext';
import LoadingPopup from '../components/common/LoadingPopup.jsx';
import './ConfiguracoesPage.css';

function ConfiguracoesPage() {
  const { user, setUser } = useAuth();
  const {
    effectiveMode,
    defaultMode,
    isAdmin,
    canAdminPreview,
    adminPreviewMode,
    setAdminPreviewMode,
    clearAdminPreviewMode,
  } = useAppExperience();
  const isCompleteMode = effectiveMode === 'complete';

  const [profileData, setProfileData] = useState({
    nome_completo: '',
    nome_empresa: '',
    avatar_url: '',
    email: '',
    idioma_preferido: 'pt_BR',
    chave_openai_pessoal: '',
  });
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [initialUserDataLoaded, setInitialUserDataLoaded] = useState(false);
  const [isChangePasswordModalOpen, setIsChangePasswordModalOpen] = useState(false);
  const [basicTemplates, setBasicTemplates] = useState(() =>
  basicTemplateService.getBasicGenerationTemplates()
  );
  const [savingTemplates, setSavingTemplates] = useState(false);

  useEffect(() => {
    const fetchCurrentUser = async () => {
      setLoadingProfile(true);
      try {
        const currentUser = await authService.getCurrentUser();
        if (currentUser) {
          setProfileData({
            nome_completo: currentUser.nome_completo || currentUser.nome || '',
            nome_empresa: currentUser.nome_empresa || '',
            avatar_url: currentUser.avatar_url || '',
            email: currentUser.email || '',
            idioma_preferido: currentUser.idioma_preferido || 'pt_BR',
            chave_openai_pessoal: currentUser.chave_openai_pessoal || '',
          });
        }
        setInitialUserDataLoaded(true);
      } catch (error) {
        showErrorToast(error.message || error.detail || 'Falha ao carregar dados do usuario.');
        console.error('Erro ao buscar dados do usuario para configuracoes:', error);
      } finally {
        setLoadingProfile(false);
      }
    };

    void fetchCurrentUser();
  }, []);

  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfileData((prev) => ({ ...prev, [name]: value }));
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setLoadingProfile(true);
    try {
      const updatePayload = {
        nome_completo: profileData.nome_completo,
        nome_empresa: profileData.nome_empresa,
        avatar_url: profileData.avatar_url,
        idioma_preferido: profileData.idioma_preferido,
        chave_openai_pessoal: profileData.chave_openai_pessoal,
      };

      const updatedUser = await authService.updateCurrentUser(updatePayload);
      showSuccessToast('Perfil atualizado com sucesso!');
      if (updatedUser) {
        setUser(updatedUser);
        setProfileData((prev) => ({
          ...prev,
          nome_completo: updatedUser.nome_completo || updatedUser.nome || '',
          nome_empresa: updatedUser.nome_empresa || '',
          avatar_url: updatedUser.avatar_url || '',
          idioma_preferido: updatedUser.idioma_preferido || 'pt_BR',
          chave_openai_pessoal: updatedUser.chave_openai_pessoal || '',
        }));
      }
    } catch (error) {
      const errorMsg = error.message || error.detail || 'Falha ao atualizar perfil.';
      showErrorToast(Array.isArray(errorMsg) ? errorMsg.map((err) => err.msg).join('; ') : errorMsg);
      console.error('Erro ao atualizar perfil:', error);
    } finally {
      setLoadingProfile(false);
    }
  };

  const handleOpenChangePasswordModal = () => {
    setIsChangePasswordModalOpen(true);
  };

  const handleCloseChangePasswordModal = () => {
    setIsChangePasswordModalOpen(false);
  };

  const handleBasicTemplateChange = (event) => {
    const { name, value } = event.target;
    setBasicTemplates((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSaveBasicTemplates = (event) => {
    event.preventDefault();
    setSavingTemplates(true);
    try {
      const savedTemplates = basicTemplateService.saveBasicGenerationTemplates({
        titleTemplate: basicTemplates.titleTemplate,
        descriptionTemplate: basicTemplates.descriptionTemplate,
      });
      setBasicTemplates(savedTemplates);
      showSuccessToast('Templates do modo basico salvos com sucesso.');
    } catch (error) {
      showErrorToast(error.message || 'Falha ao salvar templates do modo basico.');
    } finally {
      setSavingTemplates(false);
    }
  };

  const handleResetBasicTemplates = () => {
    const resetTemplates = basicTemplateService.resetBasicGenerationTemplates();
    setBasicTemplates(resetTemplates);
    showSuccessToast('Templates do modo basico restaurados para o padrao.');
  };

  const handleSelectExperienceMode = (mode) => {
    if (!isAdmin || !canAdminPreview) {
      return;
    }
    setAdminPreviewMode(mode);
    showSuccessToast(`Modo de visualizacao alterado para ${mode === 'complete' ? 'Completo' : 'Basico'}.`);
  };

  const handleResetExperienceMode = () => {
    if (!isAdmin || !canAdminPreview) {
      return;
    }
    clearAdminPreviewMode();
    showSuccessToast('Visualizacao voltou ao modo padrao da plataforma.');
  };

  const formatMembershipDate = (value) => {
    if (!value) {
      return '-';
    }
    const parsedDate = new Date(value);
    if (Number.isNaN(parsedDate.getTime())) {
      return '-';
    }
    return parsedDate.toLocaleDateString('pt-BR');
  };

  const userRoleDisplay = user?.is_superuser ? 'Administrador' : 'Usuario';
  const userPlanDisplay = user?.plano?.nome || 'Sem plano';
  const userCreatedAtDisplay = formatMembershipDate(user?.created_at);
  const profileAvatarFallback = (profileData.nome_completo || profileData.email || 'U')
    .slice(0, 1)
    .toUpperCase();

  if (!initialUserDataLoaded && loadingProfile) {
    return <LoadingPopup isOpen={true} message="Carregando configuracoes..." />;
  }

  return (
    <div className="settings-page-shell">
      <section className="settings-section-card">
        <h2>Perfil do Usuario</h2>
        <div className="settings-profile-layout">
          <form className="settings-form settings-form-main" onSubmit={handleProfileSubmit}>
            <div className="settings-field">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                name="email"
                value={profileData.email}
                readOnly
                disabled
                className="settings-input settings-input-readonly"
              />
            </div>

            <div className="settings-field">
              <label htmlFor="nome">Nome</label>
              <input
                type="text"
                id="nome"
                name="nome_completo"
                value={profileData.nome_completo}
                onChange={handleProfileChange}
                className="settings-input"
                disabled={loadingProfile}
              />
            </div>

            <div className="settings-field">
              <label htmlFor="nome_empresa">Empresa</label>
              <input
                type="text"
                id="nome_empresa"
                name="nome_empresa"
                value={profileData.nome_empresa}
                onChange={handleProfileChange}
                className="settings-input"
                disabled={loadingProfile}
              />
            </div>

            <div className="settings-field">
              <label htmlFor="avatar_url">Imagem do usuario (URL)</label>
              <input
                type="url"
                id="avatar_url"
                name="avatar_url"
                value={profileData.avatar_url}
                onChange={handleProfileChange}
                className="settings-input"
                placeholder="https://..."
                autoComplete="off"
                disabled={loadingProfile}
              />
              <small className="settings-help-text">
                Essa imagem vai aparecer no canto superior direito da plataforma.
              </small>
            </div>

            <div className="settings-field">
              <label htmlFor="idioma_preferido">Idioma preferido</label>
              <select
                id="idioma_preferido"
                name="idioma_preferido"
                value={profileData.idioma_preferido}
                onChange={handleProfileChange}
                className="settings-input"
                disabled={loadingProfile}
              >
                <option value="pt_BR">Portugues (pt-BR)</option>
                <option value="en">Ingles (en)</option>
              </select>
            </div>

            <div className="settings-field">
              <label htmlFor="chave_openai_pessoal">Chave OpenAI pessoal (opcional)</label>
              <input
                type="password"
                id="chave_openai_pessoal"
                name="chave_openai_pessoal"
                value={profileData.chave_openai_pessoal}
                onChange={handleProfileChange}
                className="settings-input"
                placeholder="sk-..."
                autoComplete="off"
                disabled={loadingProfile}
              />
              <small className="settings-help-text">
                Se fornecida, esta chave sera usada para suas geracoes no modo completo.
              </small>
            </div>

            <button type="submit" className="settings-primary-btn" disabled={loadingProfile}>
              {loadingProfile ? 'Salvando perfil...' : 'Salvar alteracoes do perfil'}
            </button>
          </form>

          <aside className="settings-profile-panel" aria-label="Informacoes pessoais">
            <div className="settings-profile-avatar-wrap">
              <div className="settings-profile-avatar" aria-hidden="true">
                {profileData.avatar_url ? (
                  <img src={profileData.avatar_url} alt="" referrerPolicy="no-referrer" />
                ) : (
                  <span>{profileAvatarFallback}</span>
                )}
              </div>
              <div className="settings-profile-heading">
                <h3>{profileData.nome_completo || 'Usuario sem nome'}</h3>
                <p>{profileData.nome_empresa || 'Empresa nao informada'}</p>
              </div>
            </div>

            <div className="settings-profile-divider" />

            <div className="settings-profile-details">
              <div className="settings-profile-detail-row">
                <span className="settings-profile-detail-label">Email</span>
                <span className="settings-profile-detail-value">{profileData.email || '-'}</span>
              </div>
              <div className="settings-profile-detail-row">
                <span className="settings-profile-detail-label">Perfil</span>
                <span className="settings-profile-detail-value">{userRoleDisplay}</span>
              </div>
              <div className="settings-profile-detail-row">
                <span className="settings-profile-detail-label">Plano</span>
                <span className="settings-profile-detail-value">{userPlanDisplay}</span>
              </div>
              <div className="settings-profile-detail-row">
                <span className="settings-profile-detail-label">Idioma</span>
                <span className="settings-profile-detail-value">
                  {profileData.idioma_preferido === 'en' ? 'Ingles' : 'Portugues'}
                </span>
              </div>
              <div className="settings-profile-detail-row">
                <span className="settings-profile-detail-label">Membro desde</span>
                <span className="settings-profile-detail-value">{userCreatedAtDisplay}</span>
              </div>
            </div>
          </aside>
        </div>
      </section>

      <div className="settings-secondary-grid">
        <section className="settings-section-card">
          <h2>Seguranca</h2>
          <button onClick={handleOpenChangePasswordModal} className="settings-primary-btn">
            Alterar Senha
          </button>
        </section>

        <section className="settings-section-card">
          <h2>Experiencia do Produto</h2>
          <div className="settings-experience-status">
            <span className="settings-field-label">Modo ativo para esta sessao:</span>
            <span className={`settings-mode-badge ${isCompleteMode ? 'complete' : 'basic'}`}>
              {isCompleteMode ? 'Completo (com IA)' : 'Basico (sem IA)'}
            </span>
          </div>

          <p className="settings-help-text">
            Modo padrao da plataforma: <strong>{defaultMode === 'complete' ? 'Completo' : 'Basico'}</strong>.
          </p>

          {isAdmin && canAdminPreview ? (
            <div className="settings-experience-controls">
              <button
                type="button"
                className={`settings-mode-btn ${effectiveMode === 'basic' ? 'active' : ''}`}
                onClick={() => handleSelectExperienceMode('basic')}
              >
                Visualizar Basico
              </button>
              <button
                type="button"
                className={`settings-mode-btn ${effectiveMode === 'complete' ? 'active' : ''}`}
                onClick={() => handleSelectExperienceMode('complete')}
              >
                Visualizar Completo
              </button>
              {adminPreviewMode ? (
                <button
                  type="button"
                  className="settings-mode-reset-btn"
                  onClick={handleResetExperienceMode}
                >
                  Voltar ao padrao
                </button>
              ) : null}
            </div>
          ) : (
            <p className="settings-help-text">
              Apenas administradores podem alternar o modo de visualizacao.
            </p>
          )}
        </section>

        <section className="settings-section-card">
          <h2>Templates do Modo Basico</h2>
          <p className="settings-help-text">
            Estes templates sao usados na geracao sem IA para titulos e descricoes de produto.
          </p>
          <form onSubmit={handleSaveBasicTemplates}>
            <div className="settings-field">
              <label htmlFor="titleTemplate">Template de Titulos</label>
              <textarea
                id="titleTemplate"
                name="titleTemplate"
                className="settings-input settings-textarea"
                rows={3}
                value={basicTemplates.titleTemplate}
                onChange={handleBasicTemplateChange}
                disabled={savingTemplates}
              />
            </div>

            <div className="settings-field">
              <label htmlFor="descriptionTemplate">Template de Descricao</label>
              <textarea
                id="descriptionTemplate"
                name="descriptionTemplate"
                className="settings-input settings-textarea"
                rows={8}
                value={basicTemplates.descriptionTemplate}
                onChange={handleBasicTemplateChange}
                disabled={savingTemplates}
              />
            </div>

            <small className="settings-help-text">
              Placeholders: nome_base, marca, modelo, sku, ean, categoria, keyword, descricao_web, specs, bullets, keywords, intro.
            </small>

            <div className="settings-template-actions">
              <button type="submit" className="settings-primary-btn" disabled={savingTemplates}>
                {savingTemplates ? 'Salvando templates...' : 'Salvar templates'}
              </button>
              <button
                type="button"
                className="settings-mode-reset-btn"
                onClick={handleResetBasicTemplates}
                disabled={savingTemplates}
              >
                Restaurar padrao
              </button>
            </div>
          </form>
        </section>
      </div>

      <ChangePasswordModal
        isOpen={isChangePasswordModalOpen}
        onClose={handleCloseChangePasswordModal}
        userId={user?.id}
      />
    </div>
  );
}

export default ConfiguracoesPage;
