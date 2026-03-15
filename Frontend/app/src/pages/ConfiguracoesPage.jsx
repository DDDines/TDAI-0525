/**
 * Configuracoes page.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import authService from '../services/authService';
import basicTemplateService from '../services/basicTemplateService';
import credentialsService from '../services/credentialsService';
import { showErrorToast, showSuccessToast } from '../utils/notifications';
import ChangePasswordModal from '../components/user/ChangePasswordModal';
import { useAuth } from '../contexts/AuthContext';
import { useAppExperience } from '../contexts/AppExperienceContext';
import LoadingOverlay from '../components/common/LoadingOverlay.jsx';
import './ConfiguracoesPage.css';

const PROVIDER_DEFINITIONS = [
  {
    provider: 'openai',
    label: 'OpenAI',
    description: 'API key para geracao e operacoes LLM remotas.',
    fields: [{ key: 'secret_value', label: 'API key', placeholder: 'sk-...' }],
  },
  {
    provider: 'google_gemini',
    label: 'Google Gemini',
    description: 'API key para Gemini e sugestoes assistidas.',
    fields: [{ key: 'secret_value', label: 'API key', placeholder: 'AIza...' }],
  },
  {
    provider: 'google_cse',
    label: 'Google CSE',
    description: 'Credenciais para busca web do cliente com faturamento proprio.',
    fields: [
      { key: 'secret_value', label: 'API key', placeholder: 'AIza...' },
      { key: 'search_engine_id', label: 'Search Engine ID', placeholder: '5684ee...' },
    ],
  },
];

function emptyCredentialDraft() {
  return {
    secret_value: '',
    search_engine_id: '',
    description: '',
    is_active: true,
  };
}

function buildInitialDrafts() {
  return PROVIDER_DEFINITIONS.reduce((accumulator, providerDef) => {
    accumulator.company[providerDef.provider] = emptyCredentialDraft();
    accumulator.user[providerDef.provider] = emptyCredentialDraft();
    return accumulator;
  }, { company: {}, user: {} });
}

function buildCredentialPayload(scope, provider, draft) {
  return {
    scope_type: scope,
    provider,
    secret_value: draft.secret_value || undefined,
    description: draft.description || undefined,
    is_active: Boolean(draft.is_active),
    config_json:
      provider === 'google_cse'
        ? {
            search_engine_id: draft.search_engine_id || '',
          }
        : undefined,
  };
}

function formatEffectiveSourceLabel(source) {
  const normalized = String(source || '').trim().toLowerCase();
  const labels = {
    company: 'Empresa',
    none: 'Nao configurado',
    system: 'Sistema',
    user: 'Pessoal',
  };
  return labels[normalized] || 'Desconhecido';
}

function ConfiguracoesPage() {
  const { user, setUser } = useAuth();
  const {
    effectiveMode,
    defaultMode,
    isAdmin,
    canAdminPreview,
    adminPreviewMode,
    setAdminPreviewMode,
    clearAdminPreviewMode,
  } = useAppExperience();
  const isCompleteMode = effectiveMode === 'complete';

  const [profileData, setProfileData] = useState({
    nome_completo: '',
    nome_empresa: '',
    avatar_url: '',
    email: '',
    idioma_preferido: 'pt_BR',
  });
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [initialUserDataLoaded, setInitialUserDataLoaded] = useState(false);
  const [isChangePasswordModalOpen, setIsChangePasswordModalOpen] = useState(false);
  const [basicTemplates, setBasicTemplates] = useState(() =>
    basicTemplateService.getBasicGenerationTemplates()
  );
  const [savingTemplates, setSavingTemplates] = useState(false);
  const [credentialsOverview, setCredentialsOverview] = useState(null);
  const [credentialDrafts, setCredentialDrafts] = useState(buildInitialDrafts);
  const [loadingCredentials, setLoadingCredentials] = useState(false);
  const [savingCredentialKey, setSavingCredentialKey] = useState('');
  const [validatingCredentialKey, setValidatingCredentialKey] = useState('');

  const loadCredentialsOverview = useCallback(async () => {
    setLoadingCredentials(true);
    try {
      const overview = await credentialsService.getOverview();
      setCredentialsOverview(overview);
      setCredentialDrafts((prev) => {
        const nextDrafts = buildInitialDrafts();
        ['company', 'user'].forEach((scope) => {
          const sourceList = Array.isArray(overview?.[`${scope}_credentials`])
            ? overview[`${scope}_credentials`]
            : [];
          sourceList.forEach((item) => {
            nextDrafts[scope][item.provider] = {
              secret_value: '',
              search_engine_id: item?.config_json?.search_engine_id || '',
              description: item?.description || '',
              is_active: item?.is_active !== false,
            };
          });
        });
        return { ...prev, ...nextDrafts };
      });
    } catch (error) {
      showErrorToast(error.message || error.detail || 'Falha ao carregar credenciais.');
    } finally {
      setLoadingCredentials(false);
    }
  }, []);

  useEffect(() => {
    const fetchCurrentUser = async () => {
      setLoadingProfile(true);
      try {
        const currentUser = await authService.getCurrentUser();
        if (currentUser) {
          setProfileData({
            nome_completo: currentUser.nome_completo || currentUser.nome || '',
            nome_empresa: currentUser.nome_empresa || '',
            avatar_url: currentUser.avatar_url || '',
            email: currentUser.email || '',
            idioma_preferido: currentUser.idioma_preferido || 'pt_BR',
          });
        }
        setInitialUserDataLoaded(true);
      } catch (error) {
        showErrorToast(error.message || error.detail || 'Falha ao carregar dados do usuario.');
      } finally {
        setLoadingProfile(false);
      }
    };

    void fetchCurrentUser();
    void loadCredentialsOverview();
  }, [loadCredentialsOverview]);

  const handleProfileChange = (event) => {
    const { name, value } = event.target;
    setProfileData((prev) => ({ ...prev, [name]: value }));
  };

  const handleProfileSubmit = async (event) => {
    event.preventDefault();
    setLoadingProfile(true);
    try {
      const updatedUser = await authService.updateCurrentUser({
        nome_completo: profileData.nome_completo,
        nome_empresa: profileData.nome_empresa,
        avatar_url: profileData.avatar_url,
        idioma_preferido: profileData.idioma_preferido,
      });
      showSuccessToast('Perfil atualizado com sucesso.');
      if (updatedUser) {
        setUser(updatedUser);
      }
      await loadCredentialsOverview();
    } catch (error) {
      const errorMsg = error.message || error.detail || 'Falha ao atualizar perfil.';
      showErrorToast(Array.isArray(errorMsg) ? errorMsg.join('; ') : errorMsg);
    } finally {
      setLoadingProfile(false);
    }
  };

  const handleBasicTemplateChange = (event) => {
    const { name, value } = event.target;
    setBasicTemplates((prev) => ({ ...prev, [name]: value }));
  };

  const handleSaveBasicTemplates = async (event) => {
    event.preventDefault();
    setSavingTemplates(true);
    try {
      const savedTemplates = await basicTemplateService.saveBasicGenerationTemplates({
        titleTemplate: basicTemplates.titleTemplate,
        descriptionTemplate: basicTemplates.descriptionTemplate,
      });
      setBasicTemplates(savedTemplates);
      showSuccessToast('Templates do modo basico salvos com sucesso.');
    } catch (error) {
      showErrorToast(error.message || 'Falha ao salvar templates do modo basico.');
    } finally {
      setSavingTemplates(false);
    }
  };

  const handleResetBasicTemplates = () => {
    const resetTemplates = basicTemplateService.resetBasicGenerationTemplates();
    setBasicTemplates(resetTemplates);
    showSuccessToast('Templates do modo basico restaurados para o padrao.');
  };

  const handleSelectExperienceMode = (mode) => {
    setAdminPreviewMode(mode);
    showSuccessToast(`Modo de visualizacao alterado para ${mode === 'complete' ? 'Completo' : 'Basico'}.`);
  };

  const handleResetExperienceMode = () => {
    clearAdminPreviewMode();
    showSuccessToast('Visualizacao voltou ao modo padrao da plataforma.');
  };

  const handleCredentialDraftChange = (scope, provider, field, value) => {
    setCredentialDrafts((prev) => ({
      ...prev,
      [scope]: {
        ...prev[scope],
        [provider]: {
          ...prev[scope][provider],
          [field]: value,
        },
      },
    }));
  };

  const handleSaveCredential = async (scope, provider) => {
    const draft = credentialDrafts?.[scope]?.[provider] || emptyCredentialDraft();
    const payload = buildCredentialPayload(scope, provider, draft);
    setSavingCredentialKey(`${scope}:${provider}`);
    try {
      const validation = await credentialsService.validateCredential(payload);
      if (!validation.valid) {
        throw new Error((validation.errors || []).join('; '));
      }
      await credentialsService.upsertCredential(payload);
      showSuccessToast('Credencial salva com sucesso.');
      await loadCredentialsOverview();
      handleCredentialDraftChange(scope, provider, 'secret_value', '');
    } catch (error) {
      showErrorToast(error.message || error.detail || 'Falha ao salvar credencial.');
    } finally {
      setSavingCredentialKey('');
    }
  };

  const handleValidateCredential = async (scope, provider) => {
    const draft = credentialDrafts?.[scope]?.[provider] || emptyCredentialDraft();
    const payload = buildCredentialPayload(scope, provider, draft);
    const providerLabel = PROVIDER_DEFINITIONS.find((item) => item.provider === provider)?.label || provider;
    setValidatingCredentialKey(`${scope}:${provider}`);
    try {
      const validation = await credentialsService.validateCredential(payload);
      if (!validation.valid) {
        throw new Error((validation.errors || []).join('; '));
      }
      showSuccessToast(`${providerLabel} validado com sucesso.`);
    } catch (error) {
      showErrorToast(error.message || error.detail || `Falha ao validar ${providerLabel}.`);
    } finally {
      setValidatingCredentialKey('');
    }
  };

  const handleDeleteCredential = async (scope, provider) => {
    setSavingCredentialKey(`${scope}:${provider}`);
    try {
      await credentialsService.deleteCredential(scope, provider);
      showSuccessToast('Credencial removida com sucesso.');
      await loadCredentialsOverview();
      setCredentialDrafts((prev) => ({
        ...prev,
        [scope]: {
          ...prev[scope],
          [provider]: emptyCredentialDraft(),
        },
      }));
    } catch (error) {
      showErrorToast(error.message || error.detail || 'Falha ao remover credencial.');
    } finally {
      setSavingCredentialKey('');
    }
  };

  const effectiveSourcesByProvider = useMemo(() => {
    const map = {};
    (credentialsOverview?.effective_sources || []).forEach((item) => {
      map[item.provider] = item;
    });
    return map;
  }, [credentialsOverview]);

  const companyCredentialsByProvider = useMemo(() => {
    const map = {};
    (credentialsOverview?.company_credentials || []).forEach((item) => {
      map[item.provider] = item;
    });
    return map;
  }, [credentialsOverview]);

  const userCredentialsByProvider = useMemo(() => {
    const map = {};
    (credentialsOverview?.user_credentials || []).forEach((item) => {
      map[item.provider] = item;
    });
    return map;
  }, [credentialsOverview]);

  const formatMembershipDate = (value) => {
    if (!value) return '-';
    const parsedDate = new Date(value);
    if (Number.isNaN(parsedDate.getTime())) return '-';
    return parsedDate.toLocaleDateString('pt-BR');
  };

  const userRoleDisplay = user?.is_superuser ? 'Administrador' : 'Usuario';
  const userPlanDisplay = user?.plano?.nome || 'Sem plano';
  const userCreatedAtDisplay = formatMembershipDate(user?.created_at);
  const profileAvatarFallback = (profileData.nome_completo || profileData.email || 'U')
    .slice(0, 1)
    .toUpperCase();

  if (!initialUserDataLoaded && loadingProfile) {
    return <LoadingOverlay isOpen={true} message="Carregando configuracoes..." />;
  }

  return (
    <div className="settings-page-shell">
      <section className="settings-section-card">
        <h2>Perfil do Usuario</h2>
        <div className="settings-profile-layout">
          <form className="settings-form settings-form-main" onSubmit={handleProfileSubmit}>
            <div className="settings-field">
              <label htmlFor="email">Email</label>
              <input type="email" id="email" name="email" value={profileData.email} readOnly disabled className="settings-input settings-input-readonly" />
            </div>
            <div className="settings-field">
              <label htmlFor="nome">Nome</label>
              <input type="text" id="nome" name="nome_completo" value={profileData.nome_completo} onChange={handleProfileChange} className="settings-input" disabled={loadingProfile} />
            </div>
            <div className="settings-field">
              <label htmlFor="nome_empresa">Empresa</label>
              <input type="text" id="nome_empresa" name="nome_empresa" value={profileData.nome_empresa} onChange={handleProfileChange} className="settings-input" disabled={loadingProfile} />
            </div>
            <div className="settings-field">
              <label htmlFor="avatar_url">Imagem do usuario (URL)</label>
              <input type="url" id="avatar_url" name="avatar_url" value={profileData.avatar_url} onChange={handleProfileChange} className="settings-input" placeholder="https://..." autoComplete="off" disabled={loadingProfile} />
            </div>
            <div className="settings-field">
              <label htmlFor="idioma_preferido">Idioma preferido</label>
              <select id="idioma_preferido" name="idioma_preferido" value={profileData.idioma_preferido} onChange={handleProfileChange} className="settings-input" disabled={loadingProfile}>
                <option value="pt_BR">Portugues (pt-BR)</option>
                <option value="en">Ingles (en)</option>
              </select>
            </div>
            <button type="submit" className="settings-primary-btn" disabled={loadingProfile}>
              {loadingProfile ? 'Salvando perfil...' : 'Salvar alteracoes do perfil'}
            </button>
          </form>

          <aside className="settings-profile-panel" aria-label="Informacoes pessoais">
            <div className="settings-profile-avatar-wrap">
              <div className="settings-profile-avatar" aria-hidden="true">
                {profileData.avatar_url ? <img src={profileData.avatar_url} alt="" referrerPolicy="no-referrer" /> : <span>{profileAvatarFallback}</span>}
              </div>
              <div className="settings-profile-heading">
                <h3>{profileData.nome_completo || 'Usuario sem nome'}</h3>
                <p>{profileData.nome_empresa || 'Empresa nao informada'}</p>
              </div>
            </div>
            <div className="settings-profile-divider" />
            <div className="settings-profile-details">
              <div className="settings-profile-detail-row"><span className="settings-profile-detail-label">Email</span><span className="settings-profile-detail-value">{profileData.email || '-'}</span></div>
              <div className="settings-profile-detail-row"><span className="settings-profile-detail-label">Perfil</span><span className="settings-profile-detail-value">{userRoleDisplay}</span></div>
              <div className="settings-profile-detail-row"><span className="settings-profile-detail-label">Plano</span><span className="settings-profile-detail-value">{userPlanDisplay}</span></div>
              <div className="settings-profile-detail-row"><span className="settings-profile-detail-label">Modo do produto</span><span className="settings-profile-detail-value">{isCompleteMode ? 'Completo' : 'Basico'}</span></div>
              <div className="settings-profile-detail-row"><span className="settings-profile-detail-label">Membro desde</span><span className="settings-profile-detail-value">{userCreatedAtDisplay}</span></div>
            </div>
          </aside>
        </div>
      </section>

      <div className="settings-secondary-grid">
        <section className="settings-section-card settings-compact-card settings-security-card">
          <div className="settings-card-header">
            <h2>Seguranca</h2>
            <p className="settings-help-text">
              Proteja seu acesso e atualize sua senha quando precisar.
            </p>
          </div>
          <button
            onClick={() => setIsChangePasswordModalOpen(true)}
            className="settings-primary-btn settings-inline-btn"
          >
            Alterar Senha
          </button>
        </section>

        <section className="settings-section-card settings-compact-card settings-experience-card">
          <div className="settings-card-header">
            <h2>Experiencia do Produto</h2>
            <p className="settings-help-text">
              Veja qual modo esta guiando esta sessao e como a plataforma se comporta para o seu perfil.
            </p>
          </div>
          <div className="settings-experience-summary">
            <div className="settings-experience-row">
              <span className="settings-field-label">Modo ativo para esta sessao:</span>
              <span className={`settings-mode-badge ${isCompleteMode ? 'complete' : 'basic'}`}>
                {isCompleteMode ? 'Completo (com IA)' : 'Basico (sem IA)'}
              </span>
            </div>
            <div className="settings-experience-row">
              <span className="settings-field-label">Modo padrao da plataforma:</span>
              <strong className="settings-experience-value">
                {defaultMode === 'complete' ? 'Completo' : 'Basico'}
              </strong>
            </div>
          </div>
          {isAdmin && canAdminPreview ? (
            <div className="settings-experience-controls">
              <button type="button" className={`settings-mode-btn ${effectiveMode === 'basic' ? 'active' : ''}`} onClick={() => handleSelectExperienceMode('basic')}>
                Visualizar Basico
              </button>
              <button type="button" className={`settings-mode-btn ${effectiveMode === 'complete' ? 'active' : ''}`} onClick={() => handleSelectExperienceMode('complete')}>
                Visualizar Completo
              </button>
              {adminPreviewMode ? (
                <button type="button" className="settings-mode-reset-btn" onClick={handleResetExperienceMode}>
                  Voltar ao padrao
                </button>
              ) : null}
            </div>
          ) : (
            <p className="settings-help-text settings-experience-footnote">Seu modo real vem do plano ativo e do seu perfil.</p>
          )}
        </section>

        <section className="settings-section-card settings-templates-card">
          <div className="settings-card-header">
            <h2>Templates do Modo Basico</h2>
            <p className="settings-help-text">
              Ajuste o formato padrao de titulo e descricao para o fluxo sem IA.
            </p>
          </div>
          <form onSubmit={handleSaveBasicTemplates}>
            <div className="settings-field">
              <label htmlFor="titleTemplate">Template de Titulos</label>
              <textarea id="titleTemplate" name="titleTemplate" className="settings-input settings-textarea" rows={3} value={basicTemplates.titleTemplate} onChange={handleBasicTemplateChange} disabled={savingTemplates} />
            </div>
            <div className="settings-field">
              <label htmlFor="descriptionTemplate">Template de Descricao</label>
              <textarea id="descriptionTemplate" name="descriptionTemplate" className="settings-input settings-textarea" rows={8} value={basicTemplates.descriptionTemplate} onChange={handleBasicTemplateChange} disabled={savingTemplates} />
            </div>
            <small className="settings-help-text">
              Placeholders: nome_base, marca, modelo, sku, ean, categoria, keyword, descricao_web, specs, bullets, keywords, intro.
            </small>
            <div className="settings-template-actions">
              <button type="submit" className="settings-primary-btn" disabled={savingTemplates}>
                {savingTemplates ? 'Salvando templates...' : 'Salvar templates'}
              </button>
              <button type="button" className="settings-mode-reset-btn" onClick={handleResetBasicTemplates} disabled={savingTemplates}>
                Restaurar padrao
              </button>
            </div>
          </form>
        </section>
      </div>

      <section className="settings-section-card">
        <h2>Credenciais e Integracoes</h2>
        <p className="settings-help-text">
          As credenciais do cliente seguem esta precedencia: <strong>Pessoal &gt; Empresa &gt; Sistema</strong>.
        </p>
        {loadingCredentials ? (
          <div className="settings-inline-loading" role="status" aria-live="polite">
            <span className="settings-inline-loading-spinner" aria-hidden="true" />
            <span>Carregando credenciais...</span>
          </div>
        ) : (
          <div className="settings-secondary-grid">
            {isAdmin ? (
              <section className="settings-section-card">
                <h3>Credenciais da Empresa</h3>
                <p className="settings-help-text">
                  Empresa atual: <strong>{credentialsOverview?.company_identifier || 'nao definida'}</strong>.
                </p>
                {PROVIDER_DEFINITIONS.map((providerDef) => {
                  const provider = providerDef.provider;
                  const existing = companyCredentialsByProvider[provider];
                  const draft = credentialDrafts.company[provider] || emptyCredentialDraft();
                  const effectiveSource = effectiveSourcesByProvider[provider];
                  const saving = savingCredentialKey === `company:${provider}`;
                  const validating = validatingCredentialKey === `company:${provider}`;
                  return (
                    <form
                      key={`company-${provider}`}
                      className="settings-section-card"
                      onSubmit={(event) => {
                        event.preventDefault();
                        handleSaveCredential('company', provider);
                      }}
                    >
                      <input
                        type="text"
                        name={`company-${provider}-credential-context`}
                        autoComplete="username"
                        value={`company:${provider}`}
                        readOnly
                        hidden
                        tabIndex={-1}
                      />
                      <h4>{providerDef.label}</h4>
                      <p className="settings-help-text">{providerDef.description}</p>
                      <p className="settings-help-text">
                        Origem efetiva em uso: <strong>{effectiveSource?.source_label || formatEffectiveSourceLabel(effectiveSource?.source)}</strong>
                      </p>
                      {providerDef.fields.map((field) => (
                        <div key={field.key} className="settings-field">
                          <label htmlFor={`company-${provider}-${field.key}`}>{field.label}</label>
                          <input
                            id={`company-${provider}-${field.key}`}
                            name={`company-${provider}-${field.key}`}
                            type="text"
                            className="settings-input settings-secret-input"
                            value={draft[field.key] || ''}
                            placeholder={existing?.secret_masked || field.placeholder || ''}
                            onChange={(event) => handleCredentialDraftChange('company', provider, field.key, event.target.value)}
                            disabled={saving || validating}
                            autoComplete="off"
                            spellCheck={false}
                          />
                        </div>
                      ))}
                      <div className="settings-field">
                        <label htmlFor={`company-${provider}-description`}>Descricao interna</label>
                        <input
                          id={`company-${provider}-description`}
                          type="text"
                          className="settings-input"
                          value={draft.description || ''}
                          onChange={(event) =>
                            handleCredentialDraftChange('company', provider, 'description', event.target.value)
                          }
                          disabled={saving || validating}
                        />
                      </div>
                      <div className="settings-template-actions">
                        <button type="button" className="settings-mode-btn" onClick={() => handleValidateCredential('company', provider)} disabled={saving || validating}>
                          {validating ? 'Validando...' : 'Validar'}
                        </button>
                        <button type="submit" className="settings-primary-btn" disabled={saving || validating}>
                          {saving ? 'Salvando...' : 'Salvar'}
                        </button>
                        <button type="button" className="settings-mode-reset-btn" onClick={() => handleDeleteCredential('company', provider)} disabled={saving || validating || !existing}>
                          Remover
                        </button>
                      </div>
                    </form>
                  );
                })}
              </section>
            ) : null}

            <section className="settings-section-card">
              <h3>Minhas Credenciais Pessoais</h3>
              <p className="settings-help-text">
                Use override pessoal quando quiser faturar suas chamadas externamente na sua propria conta.
              </p>
              {PROVIDER_DEFINITIONS.map((providerDef) => {
                const provider = providerDef.provider;
                const existing = userCredentialsByProvider[provider];
                const draft = credentialDrafts.user[provider] || emptyCredentialDraft();
                const effectiveSource = effectiveSourcesByProvider[provider];
                const saving = savingCredentialKey === `user:${provider}`;
                const validating = validatingCredentialKey === `user:${provider}`;
                return (
                  <form
                    key={`user-${provider}`}
                    className="settings-section-card"
                    onSubmit={(event) => {
                      event.preventDefault();
                      handleSaveCredential('user', provider);
                    }}
                  >
                    <input
                      type="text"
                      name={`user-${provider}-credential-context`}
                      autoComplete="username"
                      value={`user:${provider}`}
                      readOnly
                      hidden
                      tabIndex={-1}
                    />
                    <h4>{providerDef.label}</h4>
                    <p className="settings-help-text">{providerDef.description}</p>
                    <p className="settings-help-text">
                      Origem efetiva em uso: <strong>{effectiveSource?.source_label || formatEffectiveSourceLabel(effectiveSource?.source)}</strong>
                    </p>
                    {providerDef.fields.map((field) => (
                      <div key={field.key} className="settings-field">
                        <label htmlFor={`user-${provider}-${field.key}`}>{field.label}</label>
                        <input
                          id={`user-${provider}-${field.key}`}
                          name={`user-${provider}-${field.key}`}
                          type="text"
                          className="settings-input settings-secret-input"
                          value={draft[field.key] || ''}
                          placeholder={existing?.secret_masked || field.placeholder || ''}
                          onChange={(event) => handleCredentialDraftChange('user', provider, field.key, event.target.value)}
                          disabled={saving || validating}
                          autoComplete="off"
                          spellCheck={false}
                        />
                      </div>
                    ))}
                    <div className="settings-field">
                      <label htmlFor={`user-${provider}-description`}>Descricao interna</label>
                      <input
                        id={`user-${provider}-description`}
                        type="text"
                        className="settings-input"
                        value={draft.description || ''}
                        onChange={(event) =>
                          handleCredentialDraftChange('user', provider, 'description', event.target.value)
                        }
                        disabled={saving || validating}
                      />
                    </div>
                    <div className="settings-template-actions">
                      <button type="button" className="settings-mode-btn" onClick={() => handleValidateCredential('user', provider)} disabled={saving || validating}>
                        {validating ? 'Validando...' : 'Validar'}
                      </button>
                      <button type="submit" className="settings-primary-btn" disabled={saving || validating}>
                        {saving ? 'Salvando...' : 'Salvar'}
                      </button>
                      <button type="button" className="settings-mode-reset-btn" onClick={() => handleDeleteCredential('user', provider)} disabled={saving || validating || !existing}>
                        Remover
                      </button>
                    </div>
                  </form>
                );
              })}
            </section>
          </div>
        )}
      </section>

      <ChangePasswordModal isOpen={isChangePasswordModalOpen} onClose={() => setIsChangePasswordModalOpen(false)} userId={user?.id} />
    </div>
  );
}

export default ConfiguracoesPage;
