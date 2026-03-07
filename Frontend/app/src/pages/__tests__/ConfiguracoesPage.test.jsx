import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ConfiguracoesPage from '../ConfiguracoesPage.jsx';
import authService from '../../services/authService';
import basicTemplateService from '../../services/basicTemplateService';
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

jest.mock('../../components/common/LoadingPopup.jsx', () => ({
  __esModule: true,
  default: ({ isOpen, message }) => (isOpen ? <div>{message}</div> : null),
}));

describe('ConfiguracoesPage', () => {
  const setUser = jest.fn();
  const setAdminPreviewMode = jest.fn();
  const clearAdminPreviewMode = jest.fn();
  let consoleErrorSpy;
  let resolveCurrentUser;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
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
      chave_openai_pessoal: 'sk-test',
    });
    authService.updateCurrentUser.mockResolvedValue({
      id: 8,
      nome_completo: 'Julio Atualizado',
      nome_empresa: 'Nova Empresa',
      avatar_url: 'https://img.example/avatar.png',
      idioma_preferido: 'en',
      chave_openai_pessoal: 'sk-live',
    });
    resolveCurrentUser = null;
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  test('loads the current user and saves profile changes', async () => {
    render(<ConfiguracoesPage />);

    expect(await screen.findByDisplayValue('julio@example.com')).toBeInTheDocument();

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
    fireEvent.change(screen.getByLabelText('Chave OpenAI pessoal (opcional)'), {
      target: { value: 'sk-live' },
    });

    fireEvent.click(screen.getByText('Salvar alteracoes do perfil'));

    await waitFor(() => {
      expect(authService.updateCurrentUser).toHaveBeenCalledWith({
        nome_completo: 'Julio Atualizado',
        nome_empresa: 'Nova Empresa',
        avatar_url: 'https://img.example/avatar.png',
        idioma_preferido: 'en',
        chave_openai_pessoal: 'sk-live',
      });
    });

    expect(setUser).toHaveBeenCalledWith({
      id: 8,
      nome_completo: 'Julio Atualizado',
      nome_empresa: 'Nova Empresa',
      avatar_url: 'https://img.example/avatar.png',
      idioma_preferido: 'en',
      chave_openai_pessoal: 'sk-live',
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Perfil atualizado com sucesso!');
    expect(screen.getByText('Nova Empresa')).toBeInTheDocument();
  });

  test('saves and resets basic mode templates and allows admin mode preview changes', async () => {
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

  test('shows an error toast when loading the current user fails', async () => {
    authService.getCurrentUser.mockRejectedValueOnce(new Error('perfil indisponivel'));

    render(<ConfiguracoesPage />);

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('perfil indisponivel');
    });
  });

  test('shows the loading state first and keeps defaults when current user payload is empty', async () => {
    authService.getCurrentUser.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveCurrentUser = resolve;
        })
    );
    useAuth.mockReturnValue({
      user: {
        id: 8,
        is_superuser: false,
        plano: null,
        created_at: null,
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

    expect(screen.getByText('Carregando configuracoes...')).toBeInTheDocument();
    resolveCurrentUser(null);

    expect(
      await screen.findByText('Apenas administradores podem alternar o modo de visualizacao.')
    ).toBeInTheDocument();
    expect(screen.getByText('Basico (sem IA)')).toBeInTheDocument();
    expect(screen.getByText('Sem plano')).toBeInTheDocument();
    expect(screen.getByText('Empresa nao informada')).toBeInTheDocument();
    expect(screen.getByText('Usuario sem nome')).toBeInTheDocument();
    expect(screen.getByText('U')).toBeInTheDocument();
    expect(screen.getAllByText('-').length).toBeGreaterThan(0);
    expect(screen.queryByText('Visualizar Completo')).not.toBeInTheDocument();
    expect(screen.queryByText('Voltar ao padrao')).not.toBeInTheDocument();
  });

  test('formats profile update errors and template save errors', async () => {
    authService.updateCurrentUser.mockRejectedValueOnce({
      detail: [{ msg: 'nome invalido' }, { msg: 'idioma invalido' }],
    });
    basicTemplateService.saveBasicGenerationTemplates.mockImplementationOnce(() => {
      throw new Error('falha ao salvar template');
    });

    render(<ConfiguracoesPage />);

    expect(await screen.findByDisplayValue('julio@example.com')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Salvar alteracoes do perfil'));
    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('nome invalido; idioma invalido');
    });

    fireEvent.click(screen.getByText('Salvar templates'));
    expect(showErrorToast).toHaveBeenCalledWith('falha ao salvar template');
  });

  test('supports profile fallback fields, null updates and invalid membership dates', async () => {
    authService.getCurrentUser.mockResolvedValueOnce({
      id: 8,
      nome: 'Nome alternativo',
      nome_empresa: '',
      avatar_url: '',
      email: 'fallback@example.com',
      idioma_preferido: '',
      chave_openai_pessoal: '',
    });
    authService.updateCurrentUser.mockResolvedValueOnce(null);
    useAuth.mockReturnValue({
      user: {
        id: 8,
        is_superuser: false,
        plano: null,
        created_at: 'invalido',
      },
      setUser,
    });

    render(<ConfiguracoesPage />);

    expect(await screen.findByDisplayValue('fallback@example.com')).toBeInTheDocument();
    expect(screen.getByText('Nome alternativo')).toBeInTheDocument();
    expect(screen.getByText('Usuario')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Salvar alteracoes do perfil'));

    await waitFor(() => {
      expect(authService.updateCurrentUser).toHaveBeenCalled();
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Perfil atualizado com sucesso!');
    expect(setUser).not.toHaveBeenCalled();
  });
});
