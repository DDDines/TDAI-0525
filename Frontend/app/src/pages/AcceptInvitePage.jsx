/**
 * AcceptInvitePage — handles workspace invite token acceptance.
 */

import React, { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { toast } from 'react-toastify';
import { LuBuilding2, LuCheck, LuX } from 'react-icons/lu';
import workspaceService from '../services/workspaceService';
import { useAuth } from '../contexts/AuthContext';

function AcceptInvitePage() {
  const { token } = useParams();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [accepting, setAccepting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState(null);

  const handleAccept = async () => {
    setAccepting(true);
    setError(null);
    try {
      await workspaceService.acceptInvite(token);
      setDone(true);
      toast.success('Convite aceito! Você agora faz parte da empresa.');
      setTimeout(() => navigate('/workspace'), 2000);
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || 'Erro ao aceitar convite.';
      setError(msg);
      toast.error(msg);
    } finally {
      setAccepting(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="wp-container" style={{ maxWidth: 480, margin: '6rem auto', padding: '2rem' }}>
        <div className="wp-card" style={{ textAlign: 'center' }}>
          <LuBuilding2 size={48} style={{ color: 'var(--primary)', marginBottom: 16 }} />
          <h1 style={{ fontSize: '1.4rem', marginBottom: 8 }}>Convite de Workspace</h1>
          <p style={{ color: 'var(--text-color-light)', marginBottom: 24 }}>
            Você precisa estar logado para aceitar este convite.
          </p>
          <Link
            to={`/login?next=/invite/${token}`}
            style={{
              display: 'inline-block',
              padding: '0.6rem 1.5rem',
              background: 'var(--primary)',
              color: '#fff',
              borderRadius: 'var(--radius, 6px)',
              textDecoration: 'none',
              fontWeight: 600,
            }}
          >
            Fazer login
          </Link>
          <p style={{ marginTop: 12, fontSize: '0.9rem', color: 'var(--text-color-light)' }}>
            Não tem conta?{' '}
            <Link to={`/signup?next=/invite/${token}`}>Criar conta grátis</Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="wp-container" style={{ maxWidth: 480, margin: '6rem auto', padding: '2rem' }}>
      <div className="wp-card" style={{ textAlign: 'center' }}>
        <LuBuilding2 size={48} style={{ color: done ? '#059669' : 'var(--primary)', marginBottom: 16 }} />
        <h1 style={{ fontSize: '1.4rem', marginBottom: 8 }}>
          {done ? 'Convite aceito!' : 'Convite de Workspace'}
        </h1>

        {done ? (
          <p style={{ color: '#059669' }}>
            <LuCheck style={{ verticalAlign: 'middle', marginRight: 4 }} />
            Você foi adicionado à empresa. Redirecionando...
          </p>
        ) : (
          <>
            <p style={{ color: 'var(--text-color-light)', marginBottom: 24 }}>
              Você foi convidado para fazer parte de um workspace. Clique abaixo para aceitar.
            </p>

            {error && (
              <p style={{ color: '#dc2626', marginBottom: 16, fontSize: '0.9rem' }}>
                <LuX style={{ verticalAlign: 'middle', marginRight: 4 }} />
                {error}
              </p>
            )}

            <button
              onClick={handleAccept}
              disabled={accepting}
              style={{
                padding: '0.7rem 2rem',
                background: 'var(--primary)',
                color: '#fff',
                border: 'none',
                borderRadius: 'var(--radius, 6px)',
                fontWeight: 600,
                fontSize: '1rem',
                cursor: accepting ? 'not-allowed' : 'pointer',
                opacity: accepting ? 0.7 : 1,
              }}
            >
              {accepting ? 'Aceitando...' : 'Aceitar convite'}
            </button>

            <p style={{ marginTop: 16 }}>
              <Link to="/workspace" style={{ color: 'var(--text-color-light)', fontSize: '0.9rem' }}>
                Cancelar
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default AcceptInvitePage;
