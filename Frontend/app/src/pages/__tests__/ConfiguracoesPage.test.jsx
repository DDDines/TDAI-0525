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
    getBasicGenerationTemplates: jest.fn(),
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

describe('ConfiguracoesPage', () => {
  const setUser = jest.fn();
  const setAdminPreviewMode = jest.fn();
  const clearAdminPreviewMode = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();

    basicTemplateService.getBasicGenerationTemplates.mockReturnValue({
      titleTemplate: '{nome_base} {marca}',
      descriptionTemplate: '{descricao_web}',
    });
    basicTemplateService.saveBasicGenerationTemplates.mockImplementation((templates) => templates);
    basicTemplateService.resetBasicGenerationTemplates.mockReturnValue({
      titleTemplate: '{nome_base}',
      descriptionTemplate: '{intro}',
    });

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
    fireEvent.change(screen.getByLabelText('Imagem do usuario (URL)'), {
      target: { value: 'https://img.example/avatar.png' },
    });
    fireEvent.change(screen.getByLabelText('Idioma preferido'), {
      target: { value: 'en' },
    });

    fireEvent.click(screen.getByText('Salvar alteracoes do perfil'));

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

  test('saves templates, resets defaults and allows admin preview changes', async () => {
    render(<ConfiguracoesPage />);

    expect(await screen.findByDisplayValue('{nome_base} {marca}')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Template de Titulos'), {
      target: { value: '{nome_base} {sku}' },
    });
    fireEvent.change(screen.getByLabelText('Template de Descricao'), {
      target: { value: '{intro}\n{specs}' },
    });
    fireEvent.click(screen.getByText('Salvar templates'));

    await waitFor(() => {
      expect(basicTemplateService.saveBasicGenerationTemplates).toHaveBeenCalledWith({
        titleTemplate: '{nome_base} {sku}',
        descriptionTemplate: '{intro}\n{specs}',
      });
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Templates do modo basico salvos com sucesso.');

    fireEvent.click(screen.getByText('Restaurar padrao'));
    expect(basicTemplateService.resetBasicGenerationTemplates).toHaveBeenCalled();
    expect(showSuccessToast).toHaveBeenCalledWith(
      'Templates do modo basico restaurados para o padrao.'
    );

    fireEvent.click(screen.getByText('Visualizar Basico'));
    expect(setAdminPreviewMode).toHaveBeenCalledWith('basic');

    fireEvent.click(screen.getByText('Visualizar Completo'));
    expect(setAdminPreviewMode).toHaveBeenCalledWith('complete');

    fireEvent.click(screen.getByText('Voltar ao padrao'));
    expect(clearAdminPreviewMode).toHaveBeenCalled();

    fireEvent.click(screen.getByText('Alterar Senha'));
    expect(screen.getByTestId('change-password-modal')).toBeInTheDocument();
    fireEvent.click(screen.getByText('close-change-password'));
    expect(screen.queryByTestId('change-password-modal')).not.toBeInTheDocument();
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
    fireEvent.change(within(googleCseCard).getByLabelText('Descricao interna'), {
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
    expect(screen.getByText('Basico (sem IA)')).toBeInTheDocument();
    expect(screen.getByText('Seu modo real vem do plano ativo e do seu perfil.')).toBeInTheDocument();
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

    expect(screen.getByText('Carregando configuracoes...')).toBeInTheDocument();

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

    fireEvent.click(screen.getByText('Salvar templates'));
    expect(screen.getByRole('button', { name: /Salvando templates/i })).toBeDisabled();

    resolveSave({
      titleTemplate: '{nome_base} {marca}',
      descriptionTemplate: '{descricao_web}',
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Salvar templates/i })).toBeEnabled();
    });
  });
});
