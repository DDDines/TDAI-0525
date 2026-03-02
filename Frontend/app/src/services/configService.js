/**
 * Module config service.
 *
 * Defines responsibilities and integration points for services.
 */

import apiClient from './apiClient';
import logger from '../utils/logger';

const DEFAULT_AUTH_PUBLIC_CONFIG = {
  google_enabled: false,
  facebook_enabled: false,
  product_experience_default: 'basic',
  allow_admin_experience_preview: true,
};

const configService = {
  async getSocialLoginConfig() {
    try {
      const response = await apiClient.get('/auth/social/config');
      logger.log('configService: social login config', response.data);
      return { ...DEFAULT_AUTH_PUBLIC_CONFIG, ...(response.data || {}) };
    } catch (error) {
      console.error('configService: error fetching social login config', error.response?.data || error.message);
      return DEFAULT_AUTH_PUBLIC_CONFIG;
    }
  },
  async getAppExperienceConfig() {
    const config = await this.getSocialLoginConfig();
    return {
      product_experience_default: config.product_experience_default,
      allow_admin_experience_preview: config.allow_admin_experience_preview,
    };
  },
};

export default configService;
