// Frontend/app/src/components/user/ChangePasswordModal.jsx
import React, { useState } from 'react';
import authService from '../../services/authService'; // Ajuste o caminho se o seu authService estiver noutro local
import { showSuccessToast, showErrorToast } from '../../utils/notifications'; // Ajuste o caminho se necessário

function ChangePasswordModal({ isOpen, onClose }) {
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_new_password: ''
  });
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({ ...prev, [name]: value }));
  };

  const clearForm = () => {
    setPasswordData({ current_password: '', new_password: '', confirm_new_password: '' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (passwordData.new_password !== passwordData.confirm_new_password) {
      showErrorToast('A nova senha e a confirmação não coincidem.');
      return;
    }
    if (passwordData.new_password.length < 8) {
        showErrorToast('A nova senha deve ter pelo menos 8 caracteres.');
        return;
    }

    setLoading(true);
    let errorMessage = 'Falha ao alterar senha.';
    try {
      const payload = {
        current_password: passwordData.current_password,
        new_password: passwordData.new_password
      };
      const response = await authService.changePassword(payload);
      showSuccessToast(response.message || 'Senha alterada com sucesso!');
      clearForm();
      onClose(); // Fecha o modal após o sucesso
    } catch (error) {
      if (error && error.detail) {
        errorMessage = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail);
      } else if (error && error.message) {
        errorMessage = error.message;
      }
      showErrorToast(errorMessage);
      console.error("Erro ao alterar senha:", error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) {
    return null;
  }

  // Estilos inline simples para inputs e labels, ou use classes CSS
  const inputGroupStyle = { marginBottom: '1rem' };
  const labelStyle = { display: 'block', marginBottom: '0.5rem', fontWeight: '500', color: '#333' };
  const inputStyle = { width: '100%', padding: '0.75rem', border: '1px solid #ccc', borderRadius: '4px', boxSizing: 'border-box', fontSize: '1rem' };
  const buttonStyle = { marginTop: '1rem', width: '100%', padding: '0.75rem', fontSize: '1.05rem' };


  return (
    <div className="modal active" id="change-password-modal">
      <div className="modal-content">
        <button className="modal-close" onClick={onClose} disabled={loading}>×</button>
        <h2>Alterar Senha</h2>
        <form onSubmit={handleSubmit}>
          <div style={inputGroupStyle}>
            <label htmlFor="current_password_modal" style={labelStyle}>Senha Atual</label>
            <input type="password" id="current_password_modal" name="current_password" value={passwordData.current_password} onChange={handleChange} style={inputStyle} disabled={loading} required autoComplete="current-password" />
          </div>
          <div style={inputGroupStyle}>
            <label htmlFor="new_password_modal" style={labelStyle}>Nova Senha (mín. 8 caracteres)</label>
            <input type="password" id="new_password_modal" name="new_password" value={passwordData.new_password} onChange={handleChange} style={inputStyle} disabled={loading} required autoComplete="new-password" minLength="8" />
          </div>
          <div style={inputGroupStyle}>
            <label htmlFor="confirm_new_password_modal" style={labelStyle}>Confirmar Nova Senha</label>
            <input type="password" id="confirm_new_password_modal" name="confirm_new_password" value={passwordData.confirm_new_password} onChange={handleChange} style={inputStyle} disabled={loading} required autoComplete="new-password" minLength="8" />
          </div>
          <button type="submit" style={buttonStyle} className="login-button" disabled={loading}>
            {loading ? 'Alterando...' : 'Salvar Nova Senha'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default ChangePasswordModal;