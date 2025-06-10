import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'react-toastify';
import './LoginPage.css';
import { FaGoogle, FaFacebookF } from 'react-icons/fa';
import logger from '../utils/logger';
import configService from '../services/configService';

const LoginPage = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [socialConfig, setSocialConfig] = useState({ google_enabled: false, facebook_enabled: false });
    const { login, isAuthenticated, isLoading: authIsLoading, user } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();

    // Redireciona se já estiver autenticado
    useEffect(() => {
        if (isAuthenticated && !authIsLoading) {
            logger.log("LoginPage: Usuário já autenticado, redirecionando...");
            const from = location.state?.from?.pathname || '/dashboard'; // Ou para a rota principal
            navigate(from, { replace: true });
        }
    }, [isAuthenticated, authIsLoading, navigate, location.state]);

    useEffect(() => {
        async function fetchSocialConfig() {
            try {
                const cfg = await configService.getSocialLoginConfig();
                setSocialConfig(cfg);
            } catch (err) {
                console.error('LoginPage: Erro ao obter config de social login', err);
            }
        }
        fetchSocialConfig();
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setIsSubmitting(true);
        try {
            await login(email, password);
            // O redirecionamento agora é tratado dentro da função login do AuthContext
            // ou pelo useEffect acima se a autenticação for detectada.
            toast.success(`Bem-vindo de volta, ${user?.nome_completo || email}!`);
        } catch (err) {
            const errorMessage = err.response?.data?.detail || err.message || "Erro desconhecido ao tentar fazer login.";
            setError(errorMessage);
            toast.error(`Falha no login: ${errorMessage}`);
            console.error("LoginPage: Erro no handleSubmit:", err);
        } finally {
            setIsSubmitting(false);
        }
    };

    // Se o AuthContext ainda está carregando a sessão, pode mostrar um loader
    if (authIsLoading && !isAuthenticated) { // Apenas mostra o loader se não estiver autenticado ainda
        return (
            <div className="login-page-wrapper">
                <div className="login-form-card">
                    <h2>Carregando...</h2>
                </div>
            </div>
        );
    }


    return (
        <div className="login-page-wrapper">
            <div className="login-form-card">
                <h2>Login CatalogAI</h2>
                <form onSubmit={handleSubmit}>
                    {error && <p className="error-message">{error}</p>}
                    <div className="form-group">
                        <label htmlFor="email">Email:</label>
                        <input
                            type="email"
                            id="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
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
                            required
                            disabled={isSubmitting}
                        />
                    </div>
                    <button type="submit" className="login-button" disabled={isSubmitting || authIsLoading}>
                        {isSubmitting ? 'Entrando...' : 'Entrar'}
                    </button>
                    <div className="social-login-buttons">
                        <a
                            href={socialConfig.google_enabled ? "/api/v1/auth/google/login" : undefined}
                            className={`social-login-button google-btn ${socialConfig.google_enabled ? '' : 'disabled'}`}
                            title={socialConfig.google_enabled ? "Entrar com Google" : "Login Google indisponível"}
                            onClick={(e) => { if (!socialConfig.google_enabled) e.preventDefault(); }}
                        >
                            <FaGoogle /> Entrar com Google
                        </a>
                        <a
                            href={socialConfig.facebook_enabled ? "/api/v1/auth/facebook/login" : undefined}
                            className={`social-login-button facebook-btn ${socialConfig.facebook_enabled ? '' : 'disabled'}`}
                            title={socialConfig.facebook_enabled ? "Entrar com Facebook" : "Login Facebook indisponível"}
                            onClick={(e) => { if (!socialConfig.facebook_enabled) e.preventDefault(); }}
                        >
                            <FaFacebookF /> Entrar com Facebook
                        </a>
                    </div>
                    <div className="login-links">
                        <Link to="/recuperar-senha">Esqueceu a senha?</Link>
                        {/* Adicionar link para registro se houver */}
                        {/* <Link to="/registrar">Não tem uma conta? Registre-se</Link> */}
                    </div>
                </form>
            </div>
        </div>
    );
};

export default LoginPage;

