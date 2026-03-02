/**
 * Module configuracoes page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useState, useEffect } from 'react';
import authService from '../services/authService';
import { showSuccessToast, showErrorToast } from '../utils/notifications';
import ChangePasswordModal from '../components/user/ChangePasswordModal';
import { useAuth } from '../contexts/AuthContext';
import { useAppExperience } from '../contexts/AppExperienceContext';
import LoadingPopup from '../components/common/LoadingPopup.jsx';
import './ConfiguracoesPage.css';

function ConfiguracoesPage() {
  const { user } = useAuth();
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
    email: '',
    idioma_preferido: 'pt_BR',
    chave_openai_pessoal: '',
  });
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [initialUserDataLoaded, setInitialUserDataLoaded] = useState(false);
  const [isChangePasswordModalOpen, setIsChangePasswordModalOpen] = useState(false);

  useEffect(() => {
    const fetchCurrentUser = async () => {
      setLoadingProfile(true);
      try {
        const currentUser = await authService.getCurrentUser();
        if (currentUser) {
          setProfileData({
            nome_completo: currentUser.nome_completo || currentUser.nome || '',
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
        idioma_preferido: profileData.idioma_preferido,
        chave_openai_pessoal: profileData.chave_openai_pessoal,
      };

      const updatedUser = await authService.updateCurrentUser(updatePayload);
      showSuccessToast('Perfil atualizado com sucesso!');
      if (updatedUser) {
        setProfileData((prev) => ({
          ...prev,
          nome_completo: updatedUser.nome_completo || updatedUser.nome || '',
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

  if (!initialUserDataLoaded && loadingProfile) {
    return <LoadingPopup isOpen={true} message="Carregando configuracoes..." />;
  }

  return (
    <div className="settings-page-shell">
      <h1 className="settings-page-title">Configuracoes</h1>

      <section className="settings-section-card">
        <h2>Perfil do Usuario</h2>
        <form className="settings-form" onSubmit={handleProfileSubmit}>
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
      </section>

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

      <ChangePasswordModal
        isOpen={isChangePasswordModalOpen}
        onClose={handleCloseChangePasswordModal}
        userId={user?.id}
      />
    </div>
  );
}

export default ConfiguracoesPage;
