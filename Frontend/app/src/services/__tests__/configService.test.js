import configService from '../configService';
import apiClient from '../apiClient';

jest.mock('../apiClient', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
  },
}));

jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
  },
}));

describe('configService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('getSocialLoginConfig merges backend flags with safe defaults', async () => {
    apiClient.get.mockResolvedValueOnce({
      data: {
        google_enabled: true,
        product_experience_default: 'complete',
      },
    });

    await expect(configService.getSocialLoginConfig()).resolves.toEqual({
      google_enabled: true,
      facebook_enabled: false,
      product_experience_default: 'complete',
      allow_admin_experience_preview: true,
    });
    expect(apiClient.get).toHaveBeenCalledWith('/auth/social/config');
  });

  test('getSocialLoginConfig falls back to default config on failure', async () => {
    apiClient.get.mockRejectedValueOnce(new Error('offline'));

    await expect(configService.getSocialLoginConfig()).resolves.toEqual({
      google_enabled: false,
      facebook_enabled: false,
      product_experience_default: 'basic',
      allow_admin_experience_preview: true,
    });
  });

  test('getAppExperienceConfig exposes only the experience-related fields', async () => {
    apiClient.get.mockResolvedValueOnce({
      data: {
        product_experience_default: 'complete',
        allow_admin_experience_preview: false,
      },
    });

    await expect(configService.getAppExperienceConfig()).resolves.toEqual({
      product_experience_default: 'complete',
      allow_admin_experience_preview: false,
    });
  });
});
