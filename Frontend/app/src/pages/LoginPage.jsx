// Frontend/app/src/pages/LoginPage.jsx
import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate, Link } from 'react-router-dom';
import './LoginPage.css'; 
import { showErrorToast } from '../utils/notifications';

function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);

    const loginData = new URLSearchParams();
    loginData.append('username', email); // O backend espera 'username' para o email no form OAuth2
    loginData.append('password', password);

    try {
      // Garante que a URL base da API está correta (pode vir de .env.local do frontend)
      const VITE_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      
      // CORREÇÃO DA URL AQUI:
      const response = await axios.post(`${VITE_API_BASE_URL}/api/v1/auth/token`, loginData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      if (response.data.access_token) {
        localStorage.setItem('accessToken', response.data.access_token);
        // Opcional: Decodificar o token para obter o nome do usuário ou buscar /users/me
        // e então navegar para o dashboard.
        // Por agora, apenas navega. O MainLayout/ProtectedRoute pode buscar o user.
        navigate('/dashboard'); 
      } else {
        showErrorToast('Resposta inesperada do servidor durante o login.');
      }
    } catch (err) {
      let errorMessage = 'Falha no login. Verifique suas credenciais ou tente novamente mais tarde.';
      if (err.response && err.response.data) {
        if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail;
        } else if (Array.isArray(err.response.data.detail)) { 
          errorMessage = err.response.data.detail.map(e => `${e.loc ? e.loc.join('.') + ': ' : ''}${e.msg}`).join('; ');
        } else if (err.response.data.message) { 
            errorMessage = err.response.data.message;
        } else if (typeof err.response.data === 'string') { 
            errorMessage = err.response.data;
        }
      } else if (err.message) { 
        errorMessage = err.message;
      }
      showErrorToast(errorMessage);
      console.error('Login error:', err.response || err.message || err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page-wrapper"> 
      <div className="login-form-card">
        <h2>Login TDAI</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email:</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
              autoComplete="username"
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">Senha:</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
              autoComplete="current-password"
            />
          </div>
          <button type="submit" className="login-button" disabled={loading}>
            {loading ? 'Entrando...' : 'Entrar'}
          </button>
        </form>
        <div className="login-links">
          {/* <Link to="/register">Não tem uma conta? Registre-se</Link> */}
          <Link to="/password-recovery">Esqueceu sua senha?</Link> 
        </div>
      </div>
    </div>
  );
}

export default LoginPage;