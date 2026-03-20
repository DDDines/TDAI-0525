import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import ConfiguracoesPage from '../ConfiguracoesPage.jsx';
import authService from '../../services/authService';
import basicTemplateService from '../../services/basicTemplateService';
import credentialsService from '../../services/credentialsService';
import { useAuth } from '../../contexts/AuthContext';
import { useAppExperience } from '../../contexts/AppExperienceContext';
import { showErrorToast, showSuccessToast } from '../../utils/notifications';

jest.mock('../../services/authService', () => ({
  __esModule: true,
  default: {
    getCurrentUser: jest.fn(),
    updateCurrentUser: jest.fn(),
  },
}));

jest.mock('../../services/basicTemplateService', () => ({
  __esModule: true,
  default: {
    DEFAULT_BASIC_GENERATION_TEMPLATES: {
      titleTemplate: '{titulo_base}',
      descriptionTemplate: '{nome_base}\n\n{technical_summary}',
    },
    getBasicGenerationTemplateOverview: jest.fn(),
    saveBasicGenerationTemplates: jest.fn(),
    resetBasicGenerationTemplates: jest.fn(),
  },
}));

jest.mock('../../services/credentialsService', () => ({
  __esModule: true,
  default: {
    getOverview: jest.fn(),
    upsertCredential: jest.fn(),
    deleteCredential: jest.fn(),
    validateCredential: jest.fn(),
  },
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../../contexts/AppExperienceContext', () => ({
  useAppExperience: jest.fn(),
}));

jest.mock('../../utils/notifications', () => ({
  showSuccessToast: jest.fn(),
  showErrorToast: jest.fn(),
}));

jest.mock('../../components/user/ChangePasswordModal', () => ({
  __esModule: true,
  default: ({ isOpen, onClose }) =>
    isOpen ? (
      <div data-testid="change-password-modal">
        <button type="button" onClick={() => onClose?.()}>
          close-change-password
        </button>
      </div>
    ) : null,
}));

jest.mock('../../components/common/LoadingOverlay.jsx', () => ({
  __esModule: true,
  default: ({ isOpen, message }) => (isOpen ? <div>{message}</div> : null),
}));

function buildCredentialsOverview() {
  return {
    company_identifier: 'catalogai',
    company_credentials: [
      {
        id: 1,
        scope_type: 'company',
        provider: 'google_cse',
        secret_masked: 'AIza****1234',
        config_json: { search_engine_id: 'cse-company-1' },
        description: 'Busca da empresa',
        is_active: true,
        source_label: 'Empresa',
      },
    ],
    user_credentials: [
      {
        id: 2,
        scope_type: 'user',
        provider: 'openai',
        secret_masked: 'sk-t****user',
        config_json: null,
        description: 'Override pessoal',
        is_active: true,
        source_label: 'Pessoal',
      },
    ],
    effective_sources: [
      { provider: 'openai', source: 'user', source_label: 'Pessoal', configured: true },
      { provider: 'google_gemini', source: 'system', source_label: 'Sistema', configured: true },
      { provider: 'google_cse', source: 'company', source_label: 'Empresa', configured: true },
    ],
  };
}

function buildTemplateOverview(overrides = {}) {
  const systemDefaults =
    overrides.systemDefaults || basicTemplateService.DEFAULT_BASIC_GENERATION_TEMPLATES;
  const companyConfig = overrides.companyConfig ?? {
    scope: 'company',
    titleTemplate: '{titulo_base} Empresa',
    descriptionTemplate: 'Descricao da empresa',
  };
  const userConfig = overrides.userConfig ?? {
    scope: 'user',
    titleTemplate: '{nome_base} {marca}',
    descriptionTemplate: '{descricao_web}',
  };
  const effectiveConfig =
    overrides.effectiveConfig || {
      source: 'user',
      sourceLabel: 'Pessoal',
      isCustom: true,
      titleTemplate: userConfig.titleTemplate,
      descriptionTemplate: userConfig.descriptionTemplate,
    };

  return {
    companyIdentifier: overrides.companyIdentifier || 'catalogai',
    systemDefaults,
    companyConfig,
    userConfig,
    effectiveConfig,
  };
}

describe('ConfiguracoesPage', () => {
  const setUser = jest.fn();
  const setAdminPreviewMode = jest.fn();
  const clearAdminPreviewMode = jest.fn();
  let currentTemplateOverview;

  beforeEach(() => {
    jest.clearAllMocks();

    currentTemplateOverview = buildTemplateOverview();

    basicTemplateService.getBasicGenerationTemplateOverview.mockImplementation(async () => ({
      ...currentTemplateOverview,
    }));
    basicTemplateService.saveBasicGenerationTemplates.mockImplementation(
      async (templates, { scope } = {}) => {
        const nextScope = scope === 'company' ? 'company' : 'user';
        currentTemplateOverview = {
          ...currentTemplateOverview,
          [`${nextScope}Config`]: {
            scope: nextScope,
            titleTemplate: templates.titleTemplate,
            descriptionTemplate: templates.descriptionTemplate,
          },
          effectiveConfig:
            nextScope === 'user'
              ? {
                  source: 'user',
                  sourceLabel: 'Pessoal',
                  isCustom: true,
                  titleTemplate: templates.titleTemplate,
                  descriptionTemplate: templates.descriptionTemplate,
                }
              : currentTemplateOverview.effectiveConfig,
        };

        return {
          titleTemplate: templates.titleTemplate,
          descriptionTemplate: templates.descriptionTemplate,
          overview: { ...currentTemplateOverview },
          scope: nextScope,
        };
      }
    );
    basicTemplateService.resetBasicGenerationTemplates.mockImplementation(
      async ({ scope } = {}) => {
        const nextScope = scope === 'company' ? 'company' : 'user';
        currentTemplateOverview = {
          ...currentTemplateOverview,
          [`${nextScope}Config`]: null,
          effectiveConfig:
            nextScope === 'user'
              ? {
                  source: 'system',
                  sourceLabel: 'Sistema',
                  isCustom: false,
                  titleTemplate: currentTemplateOverview.systemDefaults.titleTemplate,
                  descriptionTemplate: currentTemplateOverview.systemDefaults.descriptionTemplate,
                }
              : currentTemplateOverview.effectiveConfig,
        };

        return {
          titleTemplate: currentTemplateOverview.systemDefaults.titleTemplate,
          descriptionTemplate: currentTemplateOverview.systemDefaults.descriptionTemplate,
          overview: { ...currentTemplateOverview },
          scope: nextScope,
        };
      }
    );

    useAuth.mockReturnValue({
      user: {
        id: 8,
        is_superuser: true,
        plano: { nome: 'Pro' },
        created_at: '2026-03-07T00:00:00.000Z',
      },
      setUser,
    });
    useAppExperience.mockReturnValue({
      effectiveMode: 'complete',
      defaultMode: 'complete',
      isAdmin: true,
      canAdminPreview: true,
      adminPreviewMode: 'basic',
      setAdminPreviewMode,
      clearAdminPreviewMode,
    });

    authService.getCurrentUser.mockResolvedValue({
      id: 8,
      nome_completo: 'Julio Cesar',
      nome_empresa: 'CatalogAI',
      avatar_url: '',
      email: 'julio@example.com',
      idioma_preferido: 'pt_BR',
    });
    authService.updateCurrentUser.mockResolvedValue({
      id: 8,
      nome_completo: 'Julio Atualizado',
      nome_empresa: 'Nova Empresa',
      avatar_url: 'https://img.example/avatar.png',
      idioma_preferido: 'en',
    });

    credentialsService.getOverview.mockResolvedValue(buildCredentialsOverview());
    credentialsService.validateCredential.mockResolvedValue({ valid: true, errors: [] });
    credentialsService.upsertCredential.mockResolvedValue({});
    credentialsService.deleteCredential.mockResolvedValue({});
  });

  test('loads the current user and saves profile changes', async () => {
    render(<ConfiguracoesPage />);

    expect(await screen.findByDisplayValue('julio@example.com')).toBeInTheDocument();
    expect(await screen.findByText('Credenciais da Empresa')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Nome'), {
      target: { value: 'Julio Atualizado' },
    });
    fireEvent.change(screen.getByLabelText('Empresa'), {
      target: { value: 'Nova Empresa' },
    });
    fireEvent.change(screen.getByLabelText(/Imagem do usu/i), {
      target: { value: 'https://img.example/avatar.png' },
    });
    fireEvent.change(screen.getByLabelText(/Idioma preferido/i), {
      target: { value: 'en' },
    });

    fireEvent.click(screen.getByRole('button', { name: /Salvar .*perfil/i }));

    await waitFor(() => {
      expect(authService.updateCurrentUser).toHaveBeenCalledWith({
        nome_completo: 'Julio Atualizado',
        nome_empresa: 'Nova Empresa',
        avatar_url: 'https://img.example/avatar.png',
        idioma_preferido: 'en',
      });
    });

    expect(setUser).toHaveBeenCalledWith({
      id: 8,
      nome_completo: 'Julio Atualizado',
      nome_empresa: 'Nova Empresa',
      avatar_url: 'https://img.example/avatar.png',
      idioma_preferido: 'en',
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Perfil atualizado com sucesso.');
  });

  test('saves user templates, resets defaults and allows admin preview changes', async () => {
    render(<ConfiguracoesPage />);

    expect(await screen.findByDisplayValue('{nome_base} {marca}')).toBeInTheDocument();
    const templatesCard = screen.getByRole('heading', { name: /Templates do Modo/i }).closest('section');
    expect(within(templatesCard).getByText(/Origem efetiva em uso:/i)).toBeInTheDocument();
    expect(within(templatesCard).getByText(/Escopo em edi/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Template de T/i), {
      target: { value: '{nome_base} {sku}' },
    });
    fireEvent.change(screen.getByLabelText(/Template de Descri/i), {
      target: { value: '{intro}\n{specs}' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Salvar templates/i }));

    await waitFor(() => {
      expect(basicTemplateService.saveBasicGenerationTemplates).toHaveBeenCalledWith(
        {
          titleTemplate: '{nome_base} {sku}',
          descriptionTemplate: '{intro}\n{specs}',
        },
        {
          scope: 'user',
        }
      );
    });
    expect(showSuccessToast).toHaveBeenCalledWith(
      expect.stringContaining('Templates do modo')
    );

    fireEvent.click(screen.getByRole('button', { name: /Restaurar padr/i }));

    await waitFor(() => {
      expect(basicTemplateService.resetBasicGenerationTemplates).toHaveBeenCalledWith({
        scope: 'user',
      });
    });

    fireEvent.click(screen.getByRole('button', { name: /Visualizar B/i }));
    expect(setAdminPreviewMode).toHaveBeenCalledWith('basic');

    fireEvent.click(screen.getByRole('button', { name: /Visualizar Completo/i }));
    expect(setAdminPreviewMode).toHaveBeenCalledWith('complete');

    fireEvent.click(screen.getByRole('button', { name: /Voltar ao padr/i }));
    expect(clearAdminPreviewMode).toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: /Alterar Senha/i }));
    expect(screen.getByTestId('change-password-modal')).toBeInTheDocument();
    fireEvent.click(screen.getByText('close-change-password'));
    expect(screen.queryByTestId('change-password-modal')).not.toBeInTheDocument();
  });

  test('supports switching the template editor scope for admins', async () => {
    render(<ConfiguracoesPage />);

    expect(await screen.findByDisplayValue('{nome_base} {marca}')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Editar Empresa/i }));

    expect(await screen.findByDisplayValue('{titulo_base} Empresa')).toBeInTheDocument();
    const templatesCard = screen.getByRole('heading', { name: /Templates do Modo/i }).closest('section');
    expect(within(templatesCard).getByText(/Empresa atual:/i)).toHaveTextContent('catalogai');
  });

  test('renders company and personal credentials with precedence information', async () => {
    render(<ConfiguracoesPage />);

    expect(await screen.findByText('Credenciais da Empresa')).toBeInTheDocument();
    expect(screen.getByText(/Empresa atual:/i)).toHaveTextContent('catalogai');
    expect(screen.getByText('Minhas Credenciais Pessoais')).toBeInTheDocument();
    expect(screen.getAllByText('OpenAI').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Origem efetiva em uso:/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Pessoal').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Empresa').length).toBeGreaterThan(0);
  });

  test('validates and saves a company credential, then reloads the overview', async () => {
    render(<ConfiguracoesPage />);

    const companyHeading = await screen.findByText('Credenciais da Empresa');
    const companySection = companyHeading.closest('section');
    expect(await within(companySection).findByText('Google CSE')).toBeInTheDocument();
    const googleCseCard = within(companySection).getByText('Google CSE').closest('form');

    fireEvent.change(within(googleCseCard).getByLabelText('API key'), {
      target: { value: 'AIza-company-new' },
    });
    fireEvent.change(within(googleCseCard).getByLabelText('Search Engine ID'), {
      target: { value: 'cse-company-new' },
    });
    fireEvent.change(within(googleCseCard).getByLabelText(/Descri/i), {
      target: { value: 'Novo mecanismo' },
    });

    fireEvent.click(within(googleCseCard).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => {
      expect(credentialsService.validateCredential).toHaveBeenCalledWith({
        scope_type: 'company',
        provider: 'google_cse',
        secret_value: 'AIza-company-new',
        description: 'Novo mecanismo',
        is_active: true,
        config_json: { search_engine_id: 'cse-company-new' },
      });
    });

    expect(credentialsService.upsertCredential).toHaveBeenCalledWith({
      scope_type: 'company',
      provider: 'google_cse',
      secret_value: 'AIza-company-new',
      description: 'Novo mecanismo',
      is_active: true,
      config_json: { search_engine_id: 'cse-company-new' },
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Credencial salva com sucesso.');
    expect(credentialsService.getOverview).toHaveBeenCalledTimes(2);
  });

  test('removes a personal override credential', async () => {
    render(<ConfiguracoesPage />);

    const userSection = await screen.findByText('Minhas Credenciais Pessoais');
    const userOpenAICard = within(userSection.closest('section')).getByText('OpenAI').closest('form');

    fireEvent.click(within(userOpenAICard).getByRole('button', { name: 'Remover' }));

    await waitFor(() => {
      expect(credentialsService.deleteCredential).toHaveBeenCalledWith('user', 'openai');
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Credencial removida com sucesso.');
  });

  test('validates a stored credential without forcing the user to save it first', async () => {
    render(<ConfiguracoesPage />);

    const userSection = await screen.findByText('Minhas Credenciais Pessoais');
    const userOpenAICard = within(userSection.closest('section')).getByText('OpenAI').closest('form');

    fireEvent.click(within(userOpenAICard).getByRole('button', { name: 'Validar' }));

    await waitFor(() => {
      expect(credentialsService.validateCredential).toHaveBeenCalledWith({
        scope_type: 'user',
        provider: 'openai',
        secret_value: undefined,
        description: 'Override pessoal',
        is_active: true,
        config_json: undefined,
      });
    });
    expect(showSuccessToast).toHaveBeenCalledWith('OpenAI validado com sucesso.');
  });

  test('shows the non-admin product experience copy and hides company credentials', async () => {
    useAuth.mockReturnValue({
      user: {
        id: 8,
        is_superuser: false,
        plano: { nome: 'Gratuito' },
        created_at: '2026-03-07T00:00:00.000Z',
      },
      setUser,
    });
    useAppExperience.mockReturnValue({
      effectiveMode: 'basic',
      defaultMode: 'basic',
      isAdmin: false,
      canAdminPreview: false,
      adminPreviewMode: null,
      setAdminPreviewMode,
      clearAdminPreviewMode,
    });

    render(<ConfiguracoesPage />);

    expect(await screen.findByDisplayValue('julio@example.com')).toBeInTheDocument();
    const experienceCard = screen.getByRole('heading', { name: /Experi.ncia do Produto/i }).closest('section');
    expect(within(experienceCard).getByText(/sem IA/i)).toBeInTheDocument();
    expect(screen.getByText(/Seu modo real vem do plano ativo e do seu perfil/i)).toBeInTheDocument();
    expect(screen.queryByText('Credenciais da Empresa')).not.toBeInTheDocument();
    expect(screen.getByText('Minhas Credenciais Pessoais')).toBeInTheDocument();
  });

  test('uses the page loading overlay before the profile data finishes loading', async () => {
    let resolveCurrentUser;
    authService.getCurrentUser.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveCurrentUser = resolve;
        })
    );

    render(<ConfiguracoesPage />);

    expect(screen.getByText(/Carregando configura/i)).toBeInTheDocument();

    resolveCurrentUser({
      id: 8,
      nome_completo: 'Julio Cesar',
      nome_empresa: 'CatalogAI',
      avatar_url: '',
      email: 'julio@example.com',
      idioma_preferido: 'pt_BR',
    });

    expect(await screen.findByDisplayValue('julio@example.com')).toBeInTheDocument();
  });

  test('shows loading and error fallbacks for templates and credentials', async () => {
    let resolveSave;
    basicTemplateService.saveBasicGenerationTemplates.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveSave = resolve;
        })
    );
    credentialsService.getOverview.mockRejectedValueOnce(new Error('credenciais indisponiveis'));

    render(<ConfiguracoesPage />);

    expect(await screen.findByDisplayValue('{nome_base} {marca}')).toBeInTheDocument();
    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('credenciais indisponiveis');
    });

    fireEvent.click(screen.getByRole('button', { name: /Salvar templates/i }));
    expect(screen.getByRole('button', { name: /Salvando templates/i })).toBeDisabled();

    resolveSave({
      titleTemplate: '{nome_base} {marca}',
      descriptionTemplate: '{descricao_web}',
      overview: currentTemplateOverview,
      scope: 'user',
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Salvar templates/i })).toBeEnabled();
    });
  });

  test('shows the template load error and lets the user retry', async () => {
    basicTemplateService.getBasicGenerationTemplateOverview
      .mockRejectedValueOnce(new Error('templates offline'))
      .mockResolvedValueOnce(currentTemplateOverview);

    render(<ConfiguracoesPage />);

    expect(await screen.findByText('templates offline')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Tentar novamente/i }));

    expect(await screen.findByDisplayValue('{nome_base} {marca}')).toBeInTheDocument();
  });
});
