/**
 * Module signup page.
 *
 * Provides the public self-serve registration flow and optional plan preselection
 * before redirecting the user into the authenticated dashboard.
 */

import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'react-toastify';
import { useAuth } from '../contexts/AuthContext';
import authService from '../services/authService';
import './LoginPage.css';

export default function SignupPage() {
  const [form, setForm] = useState({
    nome_completo: '',
    email: '',
    nome_empresa: '',
    password: '',
    confirmar: '',
  });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const nextPath = searchParams.get('next');

  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      navigate(nextPath || '/workspace?setup=1', { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate, nextPath]);

  const plano = searchParams.get('plano');
  const setField = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    if (form.password !== form.confirmar) {
      setError('As senhas não coincidem.');
      return;
    }

    if (form.password.length < 6) {
      setError('A senha deve ter pelo menos 6 caracteres.');
      return;
    }

    setIsSubmitting(true);
    try {
      await authService.register({
        email: form.email,
        password: form.password,
        nome_completo: form.nome_completo || undefined,
        nome_empresa: form.nome_empresa || undefined,
      });
      await login(form.email, form.password, {
        redirectPath: nextPath || '/workspace?setup=1',
      });
      toast.success(`Bem-vindo, ${form.nome_completo || form.email}!`);
    } catch (err) {
      const message = err?.detail || err?.message || 'Erro ao criar conta.';
      setError(message);
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-page-wrapper">
      <div className="login-form-card">
        <h2>Criar conta{plano === 'pro' ? ' — Pro' : ' grátis'}</h2>
        <form onSubmit={handleSubmit}>
          {error ? <p className="error-message">{error}</p> : null}

          <div className="form-group">
            <label htmlFor="nome_completo">Nome completo</label>
            <input
              type="text"
              id="nome_completo"
              value={form.nome_completo}
              onChange={setField('nome_completo')}
              placeholder="Seu nome"
              disabled={isSubmitting}
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email *</label>
            <input
              type="email"
              id="email"
              value={form.email}
              onChange={setField('email')}
              required
              autoComplete="email"
              disabled={isSubmitting}
            />
          </div>

          <div className="form-group">
            <label htmlFor="nome_empresa">Nome da empresa</label>
            <input
              type="text"
              id="nome_empresa"
              value={form.nome_empresa}
              onChange={setField('nome_empresa')}
              placeholder="Opcional"
              disabled={isSubmitting}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Senha *</label>
            <input
              type="password"
              id="password"
              value={form.password}
              onChange={setField('password')}
              required
              autoComplete="new-password"
              disabled={isSubmitting}
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmar">Confirmar senha *</label>
            <input
              type="password"
              id="confirmar"
              value={form.confirmar}
              onChange={setField('confirmar')}
              required
              autoComplete="new-password"
              disabled={isSubmitting}
            />
          </div>

          <button type="submit" className="login-button" disabled={isSubmitting}>
            {isSubmitting ? 'Criando conta...' : 'Criar conta'}
          </button>

          <div className="login-links">
            <Link to="/login">Já tenho conta — Entrar</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
