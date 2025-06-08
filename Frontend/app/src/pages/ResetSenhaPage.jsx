import React, { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import authService from '../services/authService';
import { showSuccessToast, showErrorToast } from '../utils/notifications';
import './LoginPage.css';

const ResetSenhaPage = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      showErrorToast('A senha e a confirmação não coincidem.');
      return;
    }
    if (!token) {
      showErrorToast('Token inválido.');
      return;
    }
    setIsSubmitting(true);
    try {
      await authService.resetPassword(token, password);
      showSuccessToast('Senha alterada com sucesso. Faça login.');
    } catch (error) {
      const msg = error?.detail || error.message || 'Falha ao redefinir senha.';
      showErrorToast(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-page-wrapper">
      <div className="login-form-card">
        <h2>Definir Nova Senha</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="new_password">Nova senha (mín. 8 caracteres)</label>
            <input
              type="password"
              id="new_password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          <div className="form-group">
            <label htmlFor="confirm_password">Confirmar nova senha</label>
            <input
              type="password"
              id="confirm_password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          <button type="submit" className="login-button" disabled={isSubmitting}>
            {isSubmitting ? 'Salvando...' : 'Alterar Senha'}
          </button>
          <div className="login-links">
            <Link to="/login">Voltar para login</Link>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ResetSenhaPage;
