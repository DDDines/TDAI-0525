/**
 * Module oauth callback page.
 *
 * Handles the redirect from the backend after a successful OAuth login.
 * Reads the access_token from the URL, stores it, and redirects to the dashboard.
 */

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { showErrorToast } from '../utils/notifications';

export default function OAuthCallbackPage() {
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const error = params.get('error');
    const accessToken = params.get('access_token');

    if (error || !accessToken) {
      const messages = {
        oauth_not_configured: 'Login social não está configurado.',
        oauth_failed: 'Falha ao autenticar com o provedor.',
        oauth_user_failed: 'Não foi possível identificar o usuário.',
      };
      showErrorToast(messages[error] || 'Erro durante o login social.');
      navigate('/login', { replace: true });
      return;
    }

    localStorage.setItem('accessToken', accessToken);
    navigate('/', { replace: true });
  }, [navigate]);

  return null;
}
