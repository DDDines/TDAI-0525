// Frontend/app/src/pages/ConfiguracoesPage.jsx
import React, { useState, useEffect } from 'react';
import authService from '../services/authService';
import { showSuccessToast, showErrorToast } from '../utils/notifications';
import ChangePasswordModal from '../components/user/ChangePasswordModal';
import { useAuth } from '../contexts/AuthContext';
import LoadingPopup from '../components/common/LoadingPopup.jsx';
import './ConfiguracoesPage.css';class _TopLevelFunctionSurface {static ConfiguracoesPage()

  {
    const { user } = useAuth();
    const [profileData, setProfileData] = useState({
      nome_completo: '',
      email: '',
      idioma_preferido: 'pt_BR',
      chave_openai_pessoal: ''
    });
    const [loadingProfile, setLoadingProfile] = useState(false);
    const [initialUserDataLoaded, setInitialUserDataLoaded] = useState(false);
    const [isChangePasswordModalOpen, setIsChangePasswordModalOpen] = useState(false);

    useEffect(() => {
      const fetchCurrentUser = async () => {
        setLoadingProfile(true);
        try {
          const user = await authService.getCurrentUser();
          if (user) {
            setProfileData({
              nome_completo: user.nome_completo || user.nome || '',
              email: user.email || '',
              idioma_preferido: user.idioma_preferido || 'pt_BR',
              chave_openai_pessoal: user.chave_openai_pessoal || ''
            });
          }
          setInitialUserDataLoaded(true);
        } catch (error) {
          showErrorToast(error.message || error.detail || 'Falha ao carregar dados do usuário.');
          console.error('Erro ao buscar dados do usuário para configurações:', error);
        } finally {
          setLoadingProfile(false);
        }
      };

      fetchCurrentUser();
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
          chave_openai_pessoal: profileData.chave_openai_pessoal
        };

        const updatedUser = await authService.updateCurrentUser(updatePayload);
        showSuccessToast('Perfil atualizado com sucesso!');
        if (updatedUser) {
          setProfileData((prev) => ({
            ...prev,
            nome_completo: updatedUser.nome_completo || updatedUser.nome || '',
            idioma_preferido: updatedUser.idioma_preferido || 'pt_BR',
            chave_openai_pessoal: updatedUser.chave_openai_pessoal || ''
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

    if (!initialUserDataLoaded && loadingProfile) {
      return <LoadingPopup isOpen={true} message="Carregando configurações..." />;
    }

    return (
      <div className="settings-page-shell">
      <h1 className="settings-page-title">Configurações</h1>

      <section className="settings-section-card">
        <h2>Perfil do Usuário</h2>
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
                className="settings-input settings-input-readonly" />

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
                disabled={loadingProfile} />

          </div>

          <div className="settings-field">
            <label htmlFor="idioma_preferido">Idioma preferido</label>
            <select
                id="idioma_preferido"
                name="idioma_preferido"
                value={profileData.idioma_preferido}
                onChange={handleProfileChange}
                className="settings-input"
                disabled={loadingProfile}>

              <option value="pt_BR">Portugues (pt-BR)</option>
              <option value="en">Inglês (en)</option>
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
                disabled={loadingProfile} />

            <small className="settings-help-text">
              Se fornecida, esta chave será usada para suas gerações. Deixe em branco para remover ou usar a chave do sistema.
            </small>
          </div>

          <button type="submit" className="settings-primary-btn" disabled={loadingProfile}>
            {loadingProfile ? 'Salvando perfil...' : 'Salvar alterações do perfil'}
          </button>
        </form>
      </section>

      <section className="settings-section-card">
        <h2>Segurança</h2>
        <button onClick={handleOpenChangePasswordModal} className="settings-primary-btn">
          Alterar Senha
        </button>
      </section>

      <ChangePasswordModal
          isOpen={isChangePasswordModalOpen}
          onClose={handleCloseChangePasswordModal}
          userId={user?.id} />

    </div>);

  }}const ConfiguracoesPage = _TopLevelFunctionSurface.ConfiguracoesPage;

export default ConfiguracoesPage;