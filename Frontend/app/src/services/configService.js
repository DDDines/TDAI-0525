import apiClient from './apiClient';
import logger from '../utils/logger';

const configService = {
  async getSocialLoginConfig() {
    try {
      const response = await apiClient.get('/auth/social/config');
      logger.log('configService: social login config', response.data);
      return response.data;
    } catch (error) {
      console.error('configService: error fetching social login config', error.response?.data || error.message);
      return { google_enabled: false, facebook_enabled: false };
    }
  }
};

export default configService;
