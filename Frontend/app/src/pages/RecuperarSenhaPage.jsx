import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import authService from '../services/authService';
import { showSuccessToast, showErrorToast } from '../utils/notifications';
import './LoginPage.css';

const RecuperarSenhaPage = () => {
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await authService.requestPasswordRecovery(email);
      showSuccessToast('Se o email existir, enviaremos instruções para redefinição.');
    } catch (error) {
      const msg = error?.detail || error.message || 'Falha ao solicitar recuperação de senha.';
      showErrorToast(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-page-wrapper">
      <div className="login-form-card">
        <h2>Recuperar Senha</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email cadastrado</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={isSubmitting}
            />
          </div>
          <button type="submit" className="login-button" disabled={isSubmitting}>
            {isSubmitting ? 'Enviando...' : 'Enviar link'}
          </button>
          <div className="login-links">
            <Link to="/login">Voltar para login</Link>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RecuperarSenhaPage;
