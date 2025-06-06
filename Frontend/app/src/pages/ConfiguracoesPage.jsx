// Frontend/app/src/pages/ConfiguracoesPage.jsx
import React, { useState, useEffect } from 'react';
import authService from '../services/authService';
import { showSuccessToast, showErrorToast } from '../utils/notifications';
import ChangePasswordModal from '../components/user/ChangePasswordModal'; // Importar o novo modal

function ConfiguracoesPage() {
  const [profileData, setProfileData] = useState({
    nome: '',
    email: '',
    idioma_preferido: 'pt',
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
            nome: user.nome || '',
            email: user.email || '',
            idioma_preferido: user.idioma_preferido || 'pt',
            chave_openai_pessoal: user.chave_openai_pessoal || ''
          });
        }
        setInitialUserDataLoaded(true);
      } catch (error) {
        showErrorToast(error.message || error.detail || 'Falha ao carregar dados do usuário.');
        console.error("Erro ao buscar dados do usuário para config:", error);
      } finally {
        setLoadingProfile(false);
      }
    };
    fetchCurrentUser();
  }, []);

  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfileData(prev => ({ ...prev, [name]: value }));
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setLoadingProfile(true);
    try {
      const updatePayload = {
        nome: profileData.nome,
        idioma_preferido: profileData.idioma_preferido,
        chave_openai_pessoal: profileData.chave_openai_pessoal
      };
      
      const updatedUser = await authService.updateCurrentUser(updatePayload);
      showSuccessToast('Perfil atualizado com sucesso!');
      if (updatedUser) {
          setProfileData(prev => ({
            ...prev,
            nome: updatedUser.nome || '',
            idioma_preferido: updatedUser.idioma_preferido || 'pt',
            chave_openai_pessoal: updatedUser.chave_openai_pessoal || ''
          }));
      }
    } catch (error) {
      const errorMsg = error.message || error.detail || 'Falha ao atualizar perfil.';
      showErrorToast(Array.isArray(errorMsg) ? errorMsg.map(err => err.msg).join('; ') : errorMsg);
      console.error("Erro ao atualizar perfil:", error);
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

  // Estilos inline simples para esta página
  const formSectionStyle = {
    background: 'var(--card-bg)',
    padding: '1.5rem 2.1rem',
    borderRadius: 'var(--radius)',
    boxShadow: 'var(--shadow-sm)',
    marginBottom: '30px',
  };
  const inputGroupStyle = { marginBottom: '1rem' };
  const labelStyle = { display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#333' };
  const inputStyle = { width: '100%', padding: '0.75rem', border: '1px solid #ccc', borderRadius: '4px', boxSizing: 'border-box', fontSize: '1rem' };
  const buttonStyle = { marginTop: '1rem' };
  const smallTextStyle = { display: 'block', marginTop: '0.25rem', fontSize: '0.85em', color: '#666'};

  if (!initialUserDataLoaded && loadingProfile) {
      return <p>Carregando configurações...</p>;
  }

  return (
    <div className="configuracoes-page">
      <h1>Configurações</h1>

      <div style={formSectionStyle}>
        <h2>Perfil do Usuário</h2>
        <form onSubmit={handleProfileSubmit}>
          <div style={inputGroupStyle}>
            <label htmlFor="email" style={labelStyle}>Email</label>
            <input type="email" id="email" name="email" value={profileData.email} style={{...inputStyle, backgroundColor: '#f0f0f0', cursor: 'not-allowed' }} readOnly disabled />
          </div>
          <div style={inputGroupStyle}>
            <label htmlFor="nome" style={labelStyle}>Nome</label>
            <input type="text" id="nome" name="nome" value={profileData.nome} onChange={handleProfileChange} style={inputStyle} disabled={loadingProfile} />
          </div>
          <div style={inputGroupStyle}>
            <label htmlFor="idioma_preferido" style={labelStyle}>Idioma Preferido</label>
            <select id="idioma_preferido" name="idioma_preferido" value={profileData.idioma_preferido} onChange={handleProfileChange} style={inputStyle} disabled={loadingProfile}>
              <option value="pt">Português (pt)</option>
              <option value="en">Inglês (en)</option>
            </select>
          </div>
          <div style={inputGroupStyle}>
            <label htmlFor="chave_openai_pessoal" style={labelStyle}>Chave OpenAI Pessoal (Opcional)</label>
            <input 
              type="password"
              id="chave_openai_pessoal" 
              name="chave_openai_pessoal" 
              value={profileData.chave_openai_pessoal} 
              onChange={handleProfileChange} 
              style={inputStyle} 
              placeholder="sk-..."
              autoComplete="off"
              disabled={loadingProfile} 
            />
            <small style={smallTextStyle}>Se fornecida, esta chave será usada para as suas gerações. Deixe em branco para remover/usar a chave do sistema.</small>
          </div>
          <button type="submit" style={buttonStyle} className="login-button" disabled={loadingProfile}>
            {loadingProfile ? 'Salvando Perfil...' : 'Salvar Alterações do Perfil'}
          </button>
        </form>
      </div>

      <div style={formSectionStyle}>
        <h2>Segurança</h2>
        <button onClick={handleOpenChangePasswordModal} style={buttonStyle} className="login-button">
          Alterar Senha
        </button>
      </div>

      <ChangePasswordModal 
        isOpen={isChangePasswordModalOpen}
        onClose={handleCloseChangePasswordModal}
      />
    </div>
  );
}

export default ConfiguracoesPage;
