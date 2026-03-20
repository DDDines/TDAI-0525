/**
 * Configuracoes page.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import authService from '../services/authService';
import basicTemplateService from '../services/basicTemplateService';
import credentialsService from '../services/credentialsService';
import aiPolicyService from '../services/aiPolicyService';
import importRulesService from '../services/importRulesService';
import { showErrorToast, showSuccessToast } from '../utils/notifications';
import { extractErrorMessage } from '../utils/errorDetails';
import ChangePasswordModal from '../components/user/ChangePasswordModal';
import { useAuth } from '../contexts/AuthContext';
import { useAppExperience } from '../contexts/AppExperienceContext';
import LoadingOverlay from '../components/common/LoadingOverlay.jsx';
import './ConfiguracoesPage.css';

const FALLBACK_BASIC_TEMPLATE_STATE = {
  titleTemplate: '{titulo_base}',
  descriptionTemplate: '{nome_base}',
};

const PROVIDER_DEFINITIONS = [
  {
    provider: 'openai',
    label: 'OpenAI',
    description: 'API key para geração e operações LLM remotas.',
    fields: [{ key: 'secret_value', label: 'API key', placeholder: 'sk-...' }],
  },
  {
    provider: 'google_gemini',
    label: 'Google Gemini',
    description: 'API key para Gemini e sugestões assistidas.',
    fields: [{ key: 'secret_value', label: 'API key', placeholder: 'AIza...' }],
  },
  {
    provider: 'google_cse',
    label: 'Google CSE',
    description: 'Credenciais para busca web do cliente com faturamento próprio.',
    fields: [
      { key: 'secret_value', label: 'API key', placeholder: 'AIza...' },
      { key: 'search_engine_id', label: 'Search Engine ID', placeholder: '5684ee...' },
    ],
  },
  {
    provider: 'lm_studio',
    label: 'LM Studio (Local)',
    description: 'Configuração de referência do servidor LM Studio. Ativo apenas quando AI_PROVIDER=lm_studio está definido no servidor. A URL base e o modelo aqui registados ficam documentados para o administrador.',
    fields: [
      { key: 'secret_value', label: 'URL base', placeholder: 'http://127.0.0.1:1234/v1' },
      { key: 'lm_studio_model', label: 'Modelo', placeholder: 'mistral-7b-instruct' },
    ],
  },
];

function emptyCredentialDraft() {
  return {
    secret_value: '',
    search_engine_id: '',
    lm_studio_model: '',
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
        ? { search_engine_id: draft.search_engine_id || '' }
        : provider === 'lm_studio'
        ? { model: draft.lm_studio_model || '' }
        : undefined,
  };
}

function formatEffectiveSourceLabel(source) {
  const normalized = String(source || '').trim().toLowerCase();
  const labels = {
    company: 'Empresa',
    none: 'Não configurado',
    system: 'Sistema',
    user: 'Pessoal',
  };
  return labels[normalized] || 'Desconhecido';
}

function normalizeTemplateScope(scope) {
  return String(scope || '').trim().toLowerCase() === 'company' ? 'company' : 'user';
}

function buildTemplatesFromScope(overview, scope = 'user') {
  const normalizedScope = normalizeTemplateScope(scope);
  const fallback =
    overview?.systemDefaults
    || basicTemplateService.DEFAULT_BASIC_GENERATION_TEMPLATES
    || FALLBACK_BASIC_TEMPLATE_STATE;
  const sourceConfig = normalizedScope === 'company' ? overview?.companyConfig : overview?.userConfig;

  return {
    titleTemplate: sourceConfig?.titleTemplate || fallback.titleTemplate,
    descriptionTemplate: sourceConfig?.descriptionTemplate || fallback.descriptionTemplate,
  };
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
  const [basicTemplates, setBasicTemplates] = useState(
    basicTemplateService.DEFAULT_BASIC_GENERATION_TEMPLATES || FALLBACK_BASIC_TEMPLATE_STATE
  );
  const [basicTemplateOverview, setBasicTemplateOverview] = useState(null);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [templatesLoadError, setTemplatesLoadError] = useState('');
  const [templateScope, setTemplateScope] = useState('user');
  const [savingTemplates, setSavingTemplates] = useState(false);
  const [credentialsOverview, setCredentialsOverview] = useState(null);
  const [credentialDrafts, setCredentialDrafts] = useState(buildInitialDrafts);
  const [loadingCredentials, setLoadingCredentials] = useState(false);
  const [credentialsLoadError, setCredentialsLoadError] = useState('');
  const [savingCredentialKey, setSavingCredentialKey] = useState('');

  const [validatingCredentialKey, setValidatingCredentialKey] = useState('');
  const [importRules, setImportRules] = useState([]);
  const [loadingImportRules, setLoadingImportRules] = useState(false);
  const [deletingRuleId, setDeletingRuleId] = useState(null);
  const [aiPolicyOverview, setAiPolicyOverview] = useState(null);
  const [loadingAiPolicy, setLoadingAiPolicy] = useState(false);
  const [savingAiPolicy, setSavingAiPolicy] = useState(false);
  const [aiPolicyDraft, setAiPolicyDraft] = useState(null);

  const loadImportRules = useCallback(async () => {
    setLoadingImportRules(true);
    try {
      const rules = await importRulesService.listarRegras();
      setImportRules(Array.isArray(rules) ? rules : []);
    } catch {
      // silently degrade
    } finally {
      setLoadingImportRules(false);
    }
  }, []);

  const loadAiPolicy = useCallback(async () => {
    setLoadingAiPolicy(true);
    try {
      const overview = await aiPolicyService.getOverview();
      setAiPolicyOverview(overview);
      const userCfg = overview?.user_config || overview?.effective_config || {};
      setAiPolicyDraft({
        generation_default_mode: userCfg.generation_default_mode || 'basic',
        enrichment_default_mode: userCfg.enrichment_default_mode || 'basic',
        allow_openai: userCfg.allow_openai !== false,
        allow_gemini: userCfg.allow_gemini !== false,
        allow_attribute_ai: userCfg.allow_attribute_ai !== false,
        allow_web_llm: userCfg.allow_web_llm !== false,
        allow_provider_fallback: userCfg.allow_provider_fallback !== false,
        max_recovery_attempts: userCfg.max_recovery_attempts ?? 1,
        default_provider_preference: userCfg.default_provider_preference || '',
      });
    } catch {
      // silently degrade
    } finally {
      setLoadingAiPolicy(false);
    }
  }, []);

  const handleDeleteImportRule = async (ruleId) => {
    if (deletingRuleId) return;
    setDeletingRuleId(ruleId);
    try {
      await importRulesService.deletarRegra(ruleId);
      setImportRules((prev) => prev.filter((r) => r.id !== ruleId));
      showSuccessToast('Regra removida com sucesso.');
    } catch (error) {
      showErrorToast(extractErrorMessage(error, 'Falha ao remover regra.'));
    } finally {
      setDeletingRuleId(null);
    }
  };

  const loadCredentialsOverview = useCallback(async () => {
    setLoadingCredentials(true);
    setCredentialsLoadError('');
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
              lm_studio_model: item?.config_json?.model || '',
              description: item?.description || '',
              is_active: item?.is_active !== false,
            };
          });
        });
        return { ...prev, ...nextDrafts };
      });
    } catch (error) {
      const errorMessage = extractErrorMessage(error, 'Falha ao carregar credenciais.');
      setCredentialsLoadError(errorMessage);
      showErrorToast(errorMessage);
    } finally {
      setLoadingCredentials(false);
    }
  }, []);

  const loadBasicTemplateOverview = useCallback(async () => {
    setLoadingTemplates(true);
    setTemplatesLoadError('');
    try {
      const overview = await basicTemplateService.getBasicGenerationTemplateOverview({
        preferFresh: true,
      });
      setBasicTemplateOverview(overview);
    } catch (error) {
      const errorMessage = extractErrorMessage(error, 'Falha ao carregar templates do modo básico.');
      setTemplatesLoadError(errorMessage);
      showErrorToast(errorMessage);
    } finally {
      setLoadingTemplates(false);
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
        showErrorToast(extractErrorMessage(error, 'Falha ao carregar dados do usuário.'));
      } finally {
        setLoadingProfile(false);
      }
    };

    void fetchCurrentUser();
    void loadCredentialsOverview();
    void loadBasicTemplateOverview();
    void loadImportRules();
    void loadAiPolicy();
  }, [loadBasicTemplateOverview, loadCredentialsOverview, loadImportRules, loadAiPolicy]);

  useEffect(() => {
    if (!basicTemplateOverview) {
      return;
    }
    setBasicTemplates(buildTemplatesFromScope(basicTemplateOverview, templateScope));
  }, [basicTemplateOverview, templateScope]);

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
      const errorMsg = extractErrorMessage(error, 'Falha ao atualizar perfil.');
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
      const savedTemplates = await basicTemplateService.saveBasicGenerationTemplates(
        {
          titleTemplate: basicTemplates.titleTemplate,
          descriptionTemplate: basicTemplates.descriptionTemplate,
        },
        {
          scope: templateScope,
        }
      );
      setBasicTemplateOverview(savedTemplates.overview);
      setBasicTemplates({
        titleTemplate: savedTemplates.titleTemplate,
        descriptionTemplate: savedTemplates.descriptionTemplate,
      });
      showSuccessToast('Templates do modo básico salvos com sucesso.');
    } catch (error) {
      showErrorToast(extractErrorMessage(error, 'Falha ao salvar templates do modo básico.'));
    } finally {
      setSavingTemplates(false);
    }
  };

  const handleResetBasicTemplates = () => {
    void handleResetBasicTemplatesAction();
  };

  const handleResetBasicTemplatesAction = async () => {
    setSavingTemplates(true);
    try {
      const resetTemplates = await basicTemplateService.resetBasicGenerationTemplates({
        scope: templateScope,
      });
      setBasicTemplateOverview(resetTemplates.overview);
      setBasicTemplates({
        titleTemplate: resetTemplates.titleTemplate,
        descriptionTemplate: resetTemplates.descriptionTemplate,
      });
      showSuccessToast('Templates do modo basico restaurados para o padrao.');
    } catch (error) {
      showErrorToast(extractErrorMessage(error, 'Falha ao restaurar templates do modo basico.'));
    } finally {
      setSavingTemplates(false);
    }
  };

  const handleSelectExperienceMode = (mode) => {
    setAdminPreviewMode(mode);
    showSuccessToast(
      `Modo de visualização alterado para ${mode === 'complete' ? 'Completo' : 'Básico'}.`
    );
  };

  const handleResetExperienceMode = () => {
    clearAdminPreviewMode();
    showSuccessToast('Visualização voltou ao modo padrão da plataforma.');
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
      showErrorToast(extractErrorMessage(error, 'Falha ao salvar credencial.'));
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
      showErrorToast(extractErrorMessage(error, `Falha ao validar ${providerLabel}.`));
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
      showErrorToast(extractErrorMessage(error, 'Falha ao remover credencial.'));
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

  const effectiveTemplateSourceLabel = basicTemplateOverview?.effectiveConfig?.sourceLabel || 'Sistema';
  const hasCompanyTemplateConfig = Boolean(basicTemplateOverview?.companyConfig);
  const hasUserTemplateConfig = Boolean(basicTemplateOverview?.userConfig);
  const templateScopeLabel = templateScope === 'company' ? 'Empresa' : 'Pessoal';

  const formatMembershipDate = (value) => {
    if (!value) return '-';
    const parsedDate = new Date(value);
    if (Number.isNaN(parsedDate.getTime())) return '-';
    return parsedDate.toLocaleDateString('pt-BR');
  };

  const userRoleDisplay = user?.is_superuser ? 'Administrador' : 'Usuário';
  const userPlanDisplay = user?.plano?.nome || 'Sem plano';
  const userCreatedAtDisplay = formatMembershipDate(user?.created_at);
  const profileAvatarFallback = (profileData.nome_completo || profileData.email || 'U')
    .slice(0, 1)
    .toUpperCase();

  const handleAiPolicyDraftChange = (field, value) => {
    setAiPolicyDraft((prev) => ({ ...prev, [field]: value }));
  };

  const handleSaveAiPolicy = async (event) => {
    event.preventDefault();
    if (!aiPolicyDraft) return;
    setSavingAiPolicy(true);
    try {
      await aiPolicyService.upsertPolicy({
        scope_type: 'user',
        generation_default_mode: aiPolicyDraft.generation_default_mode,
        enrichment_default_mode: aiPolicyDraft.enrichment_default_mode,
        allow_openai: aiPolicyDraft.allow_openai,
        allow_gemini: aiPolicyDraft.allow_gemini,
        allow_attribute_ai: aiPolicyDraft.allow_attribute_ai,
        allow_web_llm: aiPolicyDraft.allow_web_llm,
        allow_provider_fallback: aiPolicyDraft.allow_provider_fallback,
        max_recovery_attempts: Number(aiPolicyDraft.max_recovery_attempts),
        default_provider_preference: aiPolicyDraft.default_provider_preference || null,
      });
      showSuccessToast('Política de IA salva com sucesso.');
      await loadAiPolicy();
    } catch (error) {
      showErrorToast(extractErrorMessage(error, 'Falha ao salvar política de IA.'));
    } finally {
      setSavingAiPolicy(false);
    }
  };

  const handleResetAiPolicy = async () => {
    setSavingAiPolicy(true);
    try {
      await aiPolicyService.deletePolicy('user');
      showSuccessToast('Política de IA pessoal removida. O sistema usa a política padrão.');
      await loadAiPolicy();
    } catch (error) {
      showErrorToast(extractErrorMessage(error, 'Falha ao remover política de IA.'));
    } finally {
      setSavingAiPolicy(false);
    }
  };

  if ((!initialUserDataLoaded && loadingProfile) || loadingTemplates) {
    return <LoadingOverlay isOpen={true} message="Carregando configurações..." />;
  }

  return (
    <div className="settings-page-shell">
      <section className="settings-section-card">
        <h2>Perfil do Usuário</h2>
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
              <label htmlFor="avatar_url">Imagem do usuário (URL)</label>
              <input type="url" id="avatar_url" name="avatar_url" value={profileData.avatar_url} onChange={handleProfileChange} className="settings-input" placeholder="https://..." autoComplete="off" disabled={loadingProfile} />
            </div>
            <div className="settings-field">
              <label htmlFor="idioma_preferido">Idioma preferido</label>
              <select id="idioma_preferido" name="idioma_preferido" value={profileData.idioma_preferido} onChange={handleProfileChange} className="settings-input" disabled={loadingProfile}>
                <option value="pt_BR">Português (pt-BR)</option>
                <option value="en">Inglês (en)</option>
              </select>
            </div>
            <button type="submit" className="settings-primary-btn" disabled={loadingProfile}>
              {loadingProfile ? 'Salvando perfil...' : 'Salvar alterações do perfil'}
            </button>
          </form>

          <aside className="settings-profile-panel" aria-label="Informacoes pessoais">
            <div className="settings-profile-avatar-wrap">
              <div className="settings-profile-avatar" aria-hidden="true">
                {profileData.avatar_url ? <img src={profileData.avatar_url} alt="" referrerPolicy="no-referrer" /> : <span>{profileAvatarFallback}</span>}
              </div>
              <div className="settings-profile-heading">
                <h3>{profileData.nome_completo || 'Usuário sem nome'}</h3>
                <p>{profileData.nome_empresa || 'Empresa não informada'}</p>
              </div>
            </div>
            <div className="settings-profile-divider" />
            <div className="settings-profile-details">
              <div className="settings-profile-detail-row"><span className="settings-profile-detail-label">Email</span><span className="settings-profile-detail-value">{profileData.email || '-'}</span></div>
              <div className="settings-profile-detail-row"><span className="settings-profile-detail-label">Perfil</span><span className="settings-profile-detail-value">{userRoleDisplay}</span></div>
              <div className="settings-profile-detail-row"><span className="settings-profile-detail-label">Plano</span><span className="settings-profile-detail-value">{userPlanDisplay}</span></div>
              <div className="settings-profile-detail-row"><span className="settings-profile-detail-label">Modo do produto</span><span className="settings-profile-detail-value">{isCompleteMode ? 'Completo' : 'Básico'}</span></div>
              <div className="settings-profile-detail-row"><span className="settings-profile-detail-label">Membro desde</span><span className="settings-profile-detail-value">{userCreatedAtDisplay}</span></div>
            </div>
          </aside>
        </div>
      </section>

      <div className="settings-secondary-grid">
        <section className="settings-section-card settings-compact-card settings-security-card">
          <div className="settings-card-header">
            <h2>Segurança</h2>
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
            <h2>Experiência do Produto</h2>
            <p className="settings-help-text">
              Veja qual modo está guiando esta sessão e como a plataforma se comporta para o seu perfil.
            </p>
          </div>
          <div className="settings-experience-summary">
            <div className="settings-experience-row">
              <span className="settings-field-label">Modo ativo para esta sessão:</span>
              <span className={`settings-mode-badge ${isCompleteMode ? 'complete' : 'basic'}`}>
                {isCompleteMode ? 'Completo (com IA)' : 'Básico (sem IA)'}
              </span>
            </div>
            <div className="settings-experience-row">
              <span className="settings-field-label">Modo padrão da plataforma:</span>
              <strong className="settings-experience-value">
                {defaultMode === 'complete' ? 'Completo' : 'Básico'}
              </strong>
            </div>
          </div>
          {isAdmin && canAdminPreview ? (
            <div className="settings-experience-controls">
              <button type="button" className={`settings-mode-btn ${effectiveMode === 'basic' ? 'active' : ''}`} onClick={() => handleSelectExperienceMode('basic')}>
                Visualizar Básico
              </button>
              <button type="button" className={`settings-mode-btn ${effectiveMode === 'complete' ? 'active' : ''}`} onClick={() => handleSelectExperienceMode('complete')}>
                Visualizar Completo
              </button>
              {adminPreviewMode ? (
                <button type="button" className="settings-mode-reset-btn" onClick={handleResetExperienceMode}>
                  Voltar ao padrão
                </button>
              ) : null}
            </div>
          ) : (
            <p className="settings-help-text settings-experience-footnote">Seu modo real vem do plano ativo e do seu perfil.</p>
          )}
        </section>

        <section className="settings-section-card settings-templates-card">
          <div className="settings-card-header">
            <h2>Templates do Modo Básico</h2>
            <p className="settings-help-text">
              Ajuste o formato padrão de título e descrição para o fluxo sem IA.
            </p>
          </div>
          <div className="settings-experience-summary">
            <div className="settings-experience-row">
              <span className="settings-field-label">Origem efetiva em uso:</span>
              <strong className="settings-experience-value">{effectiveTemplateSourceLabel}</strong>
            </div>
            <div className="settings-experience-row">
              <span className="settings-field-label">Escopo em edição:</span>
              <strong className="settings-experience-value">{templateScopeLabel}</strong>
            </div>
          </div>
          {isAdmin ? (
            <div className="settings-experience-controls settings-template-scope-controls">
              <button
                type="button"
                className={`settings-mode-btn ${templateScope === 'user' ? 'active' : ''}`}
                onClick={() => setTemplateScope('user')}
              >
                Editar Pessoal
              </button>
              <button
                type="button"
                className={`settings-mode-btn ${templateScope === 'company' ? 'active' : ''}`}
                onClick={() => setTemplateScope('company')}
              >
                Editar Empresa
              </button>
            </div>
          ) : null}
          {templatesLoadError ? (
            <div className="settings-inline-error" role="alert">
              <p>{templatesLoadError}</p>
              <button
                type="button"
                className="settings-mode-btn"
                onClick={() => void loadBasicTemplateOverview()}
              >
                Tentar novamente
              </button>
            </div>
          ) : null}
          <form onSubmit={handleSaveBasicTemplates}>
            {templateScope === 'company' ? (
              <p className="settings-help-text">
                Empresa atual: <strong>{basicTemplateOverview?.companyIdentifier || 'não definida'}</strong>.
              </p>
            ) : (
              <p className="settings-help-text">
                {hasUserTemplateConfig
                  ? 'Você já possui um override pessoal salvo para o modo básico.'
                  : 'Sem override pessoal salvo. O sistema usará a próxima camada da precedência.'}
              </p>
            )}
            <div className="settings-field">
              <label htmlFor="titleTemplate">Template de Títulos</label>
              <textarea id="titleTemplate" name="titleTemplate" className="settings-input settings-textarea" rows={3} value={basicTemplates?.titleTemplate || ''} onChange={handleBasicTemplateChange} disabled={savingTemplates} />
            </div>
            <div className="settings-field">
              <label htmlFor="descriptionTemplate">Template de Descrição</label>
              <textarea id="descriptionTemplate" name="descriptionTemplate" className="settings-input settings-textarea" rows={8} value={basicTemplates?.descriptionTemplate || ''} onChange={handleBasicTemplateChange} disabled={savingTemplates} />
            </div>
            <small className="settings-help-text">
              Placeholders: titulo_base, nome_base, technical_summary, application, reference, material, content, specs, bullets.
            </small>
            <div className="settings-template-actions">
              <button type="submit" className="settings-primary-btn" disabled={savingTemplates}>
                {savingTemplates ? 'Salvando templates...' : 'Salvar templates'}
              </button>
              <button
                type="button"
                className="settings-mode-reset-btn"
                onClick={handleResetBasicTemplates}
                disabled={
                  savingTemplates ||
                  (templateScope === 'company' ? !hasCompanyTemplateConfig : !hasUserTemplateConfig)
                }
              >
                Restaurar padrão
              </button>
            </div>
          </form>
        </section>
      </div>

      <section className="settings-section-card">
        <h2>Credenciais e Integrações</h2>
        <p className="settings-help-text">
          As credenciais do cliente seguem esta precedência: <strong>Pessoal &gt; Empresa &gt; Sistema</strong>.
        </p>
        {loadingCredentials ? (
          <div className="settings-inline-loading" role="status" aria-live="polite">
            <span className="settings-inline-loading-spinner" aria-hidden="true" />
            <span>Carregando credenciais...</span>
          </div>
        ) : (
          <>
            {credentialsLoadError ? (
              <div className="settings-inline-error" role="alert">
                <p>{credentialsLoadError}</p>
                <button
                  type="button"
                  className="settings-mode-btn"
                  onClick={() => void loadCredentialsOverview()}
                >
                  Tentar novamente
                </button>
              </div>
            ) : null}
            <div className="settings-secondary-grid">
            {isAdmin ? (
              <section className="settings-section-card">
                <h3>Credenciais da Empresa</h3>
                <p className="settings-help-text">
                  Empresa atual: <strong>{credentialsOverview?.company_identifier || 'não definida'}</strong>.
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
                        <label htmlFor={`company-${provider}-description`}>Descrição interna</label>
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
                        <button type="button" className="settings-mode-reset-btn settings-danger-btn" onClick={() => handleDeleteCredential('company', provider)} disabled={saving || validating || !existing}>
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
                Use override pessoal quando quiser faturar suas chamadas externamente na sua própria conta.
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
                      <button type="button" className="settings-mode-reset-btn settings-danger-btn" onClick={() => handleDeleteCredential('user', provider)} disabled={saving || validating || !existing}>
                        Remover
                      </button>
                    </div>
                  </form>
                );
              })}
            </section>
            </div>
          </>
        )}
      </section>

      <section className="settings-section-card">
        <h2>Regras de Validação de Importação</h2>
        <p className="settings-help-text">
          Regras aprendidas durante revisões de importação. O sistema as aplica automaticamente nos próximos imports do mesmo fornecedor.
        </p>
        {loadingImportRules ? (
          <div className="settings-inline-loading" role="status" aria-live="polite">
            <span className="settings-inline-loading-spinner" aria-hidden="true" />
            <span>Carregando regras...</span>
          </div>
        ) : importRules.length === 0 ? (
          <p className="settings-help-text">Nenhuma regra salva ainda. Elas são criadas automaticamente ao revisar importações.</p>
        ) : (
          <ul className="settings-rules-list">
            {importRules.map((rule) => (
              <li key={rule.id} className="settings-rule-item">
                <div className="settings-rule-info">
                  <span className="settings-rule-type">{rule.rule_type}</span>
                  <span className="settings-rule-action">{rule.action}</span>
                  {rule.min_quality_score != null && (
                    <span className="settings-rule-score">score ≥ {(rule.min_quality_score * 100).toFixed(0)}%</span>
                  )}
                  <span className="settings-rule-applied">Aplicada {rule.times_applied}×</span>
                </div>
                <button
                  type="button"
                  className="settings-mode-reset-btn settings-danger-btn settings-rule-delete-btn"
                  disabled={deletingRuleId === rule.id}
                  onClick={() => handleDeleteImportRule(rule.id)}
                >
                  {deletingRuleId === rule.id ? 'Removendo...' : 'Remover'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="settings-section-card">
        <h2>Política de IA</h2>
        <p className="settings-help-text">
          Controle quais provedores e modos de IA estão ativos para o seu perfil.
          Origem efetiva: <strong>{aiPolicyOverview?.effective_config?.source_label || 'Sistema'}</strong>
        </p>
        {loadingAiPolicy ? (
          <div className="settings-inline-loading" role="status" aria-live="polite">
            <span className="settings-inline-loading-spinner" aria-hidden="true" />
            <span>Carregando política de IA...</span>
          </div>
        ) : aiPolicyDraft ? (
          <form onSubmit={handleSaveAiPolicy}>
            <div className="settings-secondary-grid">
              <div className="settings-field">
                <label htmlFor="ai-gen-mode">Modo de geração padrão</label>
                <select
                  id="ai-gen-mode"
                  className="settings-input"
                  value={aiPolicyDraft.generation_default_mode}
                  onChange={(e) => handleAiPolicyDraftChange('generation_default_mode', e.target.value)}
                  disabled={savingAiPolicy}
                >
                  <option value="basic">Básico (sem IA externa)</option>
                  <option value="ia">IA (OpenAI / Gemini)</option>
                </select>
              </div>
              <div className="settings-field">
                <label htmlFor="ai-enrich-mode">Modo de enriquecimento padrão</label>
                <select
                  id="ai-enrich-mode"
                  className="settings-input"
                  value={aiPolicyDraft.enrichment_default_mode}
                  onChange={(e) => handleAiPolicyDraftChange('enrichment_default_mode', e.target.value)}
                  disabled={savingAiPolicy}
                >
                  <option value="basic">Básico (sem IA)</option>
                  <option value="ia">IA</option>
                </select>
              </div>
              <div className="settings-field">
                <label htmlFor="ai-provider-pref">Provedor preferido</label>
                <select
                  id="ai-provider-pref"
                  className="settings-input"
                  value={aiPolicyDraft.default_provider_preference || ''}
                  onChange={(e) => handleAiPolicyDraftChange('default_provider_preference', e.target.value)}
                  disabled={savingAiPolicy}
                >
                  <option value="">Automático</option>
                  <option value="openai">OpenAI</option>
                  <option value="google_gemini">Google Gemini</option>
                </select>
              </div>
              <div className="settings-field">
                <label htmlFor="ai-max-recovery">Tentativas de recuperação (max)</label>
                <input
                  id="ai-max-recovery"
                  type="number"
                  min={0}
                  max={10}
                  className="settings-input"
                  value={aiPolicyDraft.max_recovery_attempts}
                  onChange={(e) => handleAiPolicyDraftChange('max_recovery_attempts', e.target.value)}
                  disabled={savingAiPolicy}
                />
              </div>
            </div>
            <div className="settings-experience-controls" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
              {[
                { key: 'allow_openai', label: 'OpenAI habilitado' },
                { key: 'allow_gemini', label: 'Gemini habilitado' },
                { key: 'allow_attribute_ai', label: 'IA para atributos' },
                { key: 'allow_web_llm', label: 'LLM para enriquecimento web' },
                { key: 'allow_provider_fallback', label: 'Fallback de provedor' },
              ].map(({ key, label }) => (
                <label key={key} className="settings-toggle-label">
                  <input
                    type="checkbox"
                    checked={Boolean(aiPolicyDraft[key])}
                    onChange={(e) => handleAiPolicyDraftChange(key, e.target.checked)}
                    disabled={savingAiPolicy}
                  />
                  {' '}{label}
                </label>
              ))}
            </div>
            <div className="settings-template-actions" style={{ marginTop: '1rem' }}>
              <button type="submit" className="settings-primary-btn" disabled={savingAiPolicy}>
                {savingAiPolicy ? 'Salvando...' : 'Salvar política'}
              </button>
              {aiPolicyOverview?.user_config ? (
                <button
                  type="button"
                  className="settings-mode-reset-btn"
                  onClick={handleResetAiPolicy}
                  disabled={savingAiPolicy}
                >
                  Remover override pessoal
                </button>
              ) : null}
            </div>
          </form>
        ) : null}
      </section>

      <ChangePasswordModal isOpen={isChangePasswordModalOpen} onClose={() => setIsChangePasswordModalOpen(false)} userId={user?.id} />
    </div>
  );
}

export default ConfiguracoesPage;
