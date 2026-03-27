/**
 * Module login page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-toastify';
import './LoginPage.css';
import { FaGoogle, FaFacebookF } from 'react-icons/fa';
import logger from '../utils/logger';
import configService from '../services/configService';
import LoadingPopup from '../components/common/LoadingPopup.jsx';

function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [socialConfig, setSocialConfig] = useState({ google_enabled: false, facebook_enabled: false });
  const { login, isAuthenticated, isLoading: authIsLoading, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const nextPath = searchParams.get('next');

  useEffect(() => {
    if (isAuthenticated && !authIsLoading) {
      logger.log('LoginPage: Usuario ja autenticado, redirecionando...');
      const from = nextPath || location.state?.from?.pathname || '/dashboard';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, authIsLoading, navigate, location.state, nextPath]);

  useEffect(() => {
    async function fetchSocialConfig() {
      try {
        const cfg = await configService.getSocialLoginConfig();
        setSocialConfig(cfg);
      } catch (err) {
        console.error('LoginPage: Erro ao obter configuracao de social login', err);
      }
    }
    fetchSocialConfig();
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const oauthError = params.get('error');
    if (oauthError) {
      const messages = {
        oauth_not_configured: 'Login social não está configurado.',
        oauth_failed: 'Falha ao autenticar com o provedor.',
        oauth_user_failed: 'Não foi possível identificar o usuário.',
      };
      setError(messages[oauthError] || 'Erro durante o login social.');
    }
  }, [location.search]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await login(email, password, { redirectPath: nextPath || undefined });
      toast.success(`Bem-vindo de volta, ${user?.nome_completo || email}!`);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Erro desconhecido ao tentar fazer login.';
      setError(errorMessage);
      toast.error(`Falha no login: ${errorMessage}`);
      console.error('LoginPage: Erro no handleSubmit:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (authIsLoading && !isAuthenticated) {
    return <LoadingPopup isOpen={true} message="Carregando..." />;
  }

  return (
    <div className="login-page-wrapper">
      <div className="login-form-card">
        <h2>Entrar no CommerceFolio</h2>
        <form onSubmit={handleSubmit}>
          {error && <p className="error-message">{error}</p>}
          <div className="form-group">
            <label htmlFor="email">Email:</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              required
              disabled={isSubmitting}
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Senha:</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              disabled={isSubmitting}
            />
          </div>
          <button type="submit" className="login-button" disabled={isSubmitting || authIsLoading}>
            {isSubmitting ? 'Entrando...' : 'Entrar'}
          </button>

          <div className="social-login-buttons">
            <a
              href={socialConfig.google_enabled ? '/api/v1/auth/google/login' : undefined}
              className={`social-login-button google-btn ${socialConfig.google_enabled ? '' : 'disabled'}`}
              title={socialConfig.google_enabled ? 'Entrar com Google' : 'Login Google indisponível'}
              onClick={(e) => {
                if (!socialConfig.google_enabled) e.preventDefault();
              }}
            >
              <FaGoogle /> Entrar com Google
            </a>
            <a
              href={socialConfig.facebook_enabled ? '/api/v1/auth/facebook/login' : undefined}
              className={`social-login-button facebook-btn ${socialConfig.facebook_enabled ? '' : 'disabled'}`}
              title={socialConfig.facebook_enabled ? 'Entrar com Facebook' : 'Login Facebook indisponível'}
              onClick={(e) => {
                if (!socialConfig.facebook_enabled) e.preventDefault();
              }}
            >
              <FaFacebookF /> Entrar com Facebook
            </a>
          </div>

          <div className="login-links">
            <Link to="/recuperar-senha">Esqueceu a senha?</Link>
            <Link to="/signup">Não tem conta? Criar conta grátis</Link>
          </div>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;
